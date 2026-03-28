# Makefile for UNO_Q_Autonomy
# Automates the autonomous flight smoke test

ARDUPILOT_ROOT = ..
VENV = $(ARDUPILOT_ROOT)/venv

.PHONY: help test-flight clean-sim

help:
	@echo "UNO_Q_Autonomy Makefile"
	@echo "======================="
	@echo ""
	@echo "Available commands:"
	@echo "  make test-flight    - Runs the background SITL simulator and executes the autonomous Python flight script."
	@echo "  make agent-flight   - Runs the background SITL simulator and runs the podman autonomy agent to control flights via LLM."
	@echo "  make test-agent     - Runs the agent container in TEST_MODE to verify the LangGraph loop and LLM."
	@echo "  make clean-sim      - Force kills any lingering simulator processes."

clean-sim:
	@echo "Cleaning up simulator processes..."
	@pkill -f "sim_vehicle.py" || true
	@pkill -f "arducopter" || true
	@pkill -f "webots" || true

test-flight: clean-sim
	@bash -c ' \
		ORIG_DIR="$$PWD"; \
		trap "$(MAKE) -C \"$$ORIG_DIR\" clean-sim" EXIT; \
		if [ -d "$(VENV)" ]; then source $(VENV)/bin/activate; fi; \
		echo "Starting Autonomous SITL Smoke Test..."; \
		if ! pgrep -x "webots" >/dev/null; then \
			echo "Starting Webots backend (3D Graphics)..."; \
			nohup /Applications/Webots.app/Contents/MacOS/webots $(ARDUPILOT_ROOT)/libraries/SITL/examples/Webots_Python/worlds/iris.wbt >/dev/null 2>&1 & \
			echo "Waiting for Webots to initialize (5s)..."; \
			sleep 5; \
		fi; \
		echo "Starting sim_vehicle.py (Flight Controller) in background..."; \
		cd $(ARDUPILOT_ROOT) && ./Tools/autotest/sim_vehicle.py -v ArduCopter --model webots-python --add-param-file=UNO_Q_Autonomy/uno_q_dev.parm --no-mavproxy >/dev/null 2>&1 & \
		echo "Waiting for SITL TCP port 5760 to open (up to 15s)..."; \
		for i in $$(seq 1 15); do \
			if nc -z 127.0.0.1 5760 2>/dev/null; then \
				echo "SITL is ready!"; \
				break; \
			fi; \
			sleep 1; \
		done; \
		echo "--------------------------------------------------------"; \
		echo "Running autonomous flight Engine (High-Level Brain)..."; \
		cd $(ARDUPILOT_ROOT) && python3 UNO_Q_Autonomy/test_flight.py --connect tcp:127.0.0.1:5760; \
		echo "--------------------------------------------------------"; \
		echo "--------------------------------------------------------"; \
		echo "Flight complete! The drone will hold its final position."; \
		echo "Press Ctrl-C when you are ready to exit and clean up the simulator."; \
		while true; do sleep 1; done \
	'

agent-flight: clean-sim build-agent
	@bash -c ' \
		ORIG_DIR="$$PWD"; \
		trap "$(MAKE) -C \"$$ORIG_DIR\" clean-sim" EXIT; \
		if [ -d "$(VENV)" ]; then source $(VENV)/bin/activate; fi; \
		echo "Starting Autonomous SITL Smoke Test..."; \
		if ! pgrep -x "webots" >/dev/null; then \
			echo "Starting Webots backend (3D Graphics)..."; \
			nohup /Applications/Webots.app/Contents/MacOS/webots $(ARDUPILOT_ROOT)/libraries/SITL/examples/Webots_Python/worlds/iris.wbt >/dev/null 2>&1 & \
			echo "Waiting for Webots to initialize (5s)..."; \
			sleep 5; \
		fi; \
		echo "Starting sim_vehicle.py (Flight Controller) in background..."; \
		cd $(ARDUPILOT_ROOT) && ./Tools/autotest/sim_vehicle.py -v ArduCopter --model webots-python --add-param-file=UNO_Q_Autonomy/uno_q_dev.parm --no-mavproxy >/dev/null 2>&1 & \
		echo "Waiting for SITL TCP port 5760 to open (up to 15s)..."; \
		for i in $$(seq 1 15); do \
			if nc -z 127.0.0.1 5760 2>/dev/null; then \
				echo "SITL is ready!"; \
				break; \
			fi; \
			sleep 1; \
		done; \
		echo "--------------------------------------------------------"; \
		echo "Running UNO Q Autonomy Agent with macOS GPU paravirtualization (simulating Adreno performance)..."; \
		podman run -it --rm --replace --device /dev/dri -v uno_q_ollama_models:/root/.ollama -e MAVLINK_CONN="tcp:host.containers.internal:5760" --name uno-q-agent-run uno-q-agent; \
		echo "--------------------------------------------------------"; \
		echo "Agent container exited. The drone will hold its final position."; \
		echo "Press Ctrl-C when you are ready to exit and clean up the simulator."; \
		while true; do sleep 1; done \
	'

build-agent:
	@echo "Building UNO Q Autonomy Agent Container using Podman..."
	@cd $(ARDUPILOT_ROOT)/UNO_Q_Autonomy && podman build -t uno-q-agent -f Dockerfile .

run-agent:
	@echo "Running UNO Q Autonomy Agent with macOS GPU paravirtualization (simulating Adreno performance)..."
	@podman run -it --rm --replace --device /dev/dri -v uno_q_ollama_models:/root/.ollama --name uno-q-agent-run uno-q-agent

test-agent: build-agent
	@echo "Running UNO Q Autonomy Agent in TEST_MODE (simulated LLM loop validation)..."
	@podman run -it --rm --replace --device /dev/dri -v uno_q_ollama_models:/root/.ollama -e TEST_MODE=1 --name uno-q-agent-test uno-q-agent

test: test-agent
