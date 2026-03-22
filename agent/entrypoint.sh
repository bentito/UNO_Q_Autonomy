#!/bin/bash
set -e

MODEL_DIR="/root/.ollama/models"
mkdir -p $MODEL_DIR

echo "Checking for Qwen2.5-VL-3B GGUF models..."
if [ ! -f "$MODEL_DIR/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf" ]; then
    echo "Downloading Qwen2.5-VL 3B GGUF model (This might take a few minutes)..."
    /opt/venv/bin/python3 -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='unsloth/Qwen2.5-VL-3B-Instruct-GGUF', filename='Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf', local_dir='${MODEL_DIR}'); hf_hub_download(repo_id='unsloth/Qwen2.5-VL-3B-Instruct-GGUF', filename='mmproj-F16.gguf', local_dir='${MODEL_DIR}')"
fi

echo "Starting llama.cpp server in the background..."
/app/llama.cpp/build/bin/llama-server \
    -m $MODEL_DIR/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf \
    --mmproj $MODEL_DIR/mmproj-F16.gguf \
    --port 11434 \
    --host 0.0.0.0 \
    -ngl 99 \
    --jinja &
LLAMA_PID=$!

echo "Waiting for llama-server to be reachable..."
while ! curl -s http://localhost:11434/v1/models > /dev/null; do
    sleep 1
done

echo "llama-server is up. Starting the LangChain ReAct loop..."
/opt/venv/bin/python3 /app/agent/agent.py

# Wait to keep container running if agent unexpectedly exits but the server is still up
wait $LLAMA_PID
