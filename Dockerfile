FROM ubuntu:24.04

# Avoid interactive tzdata prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies required for building llama.cpp (Vulkan) and python packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    nano \
    python3-opencv \
    zstd \
    git \
    build-essential \
    cmake \
    libvulkan-dev \
    vulkan-tools \
    glslc \
    && rm -rf /var/lib/apt/lists/*

# Avoid "externally-managed-environment" PEP 668 errors by running pip inside a venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Clone and build llama.cpp with Vulkan support for the GPU paravirtualization
RUN git clone https://github.com/ggerganov/llama.cpp.git && \
    cd llama.cpp && \
    cmake -B build -DGGML_VULKAN=1 -DGGML_NATIVE=OFF && \
    cmake --build build --config Release -j $(nproc)

# Copy requirements and install
COPY agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agent code
COPY agent/ /app/agent/

# Make the entrypoint executable
RUN chmod +x /app/agent/entrypoint.sh

# Start from the entrypoint script
ENTRYPOINT ["/app/agent/entrypoint.sh"]
