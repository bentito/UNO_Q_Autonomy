# Developer Startup Guide: UNO Q Autonomy

This project utilizes a macOS-based SITL (Software-In-The-Loop) environment to simulate the dual-processor architecture of the Arduino UNO Q 4GB.

### 1. Core System & Simulation
* **OS:** macOS (Apple Silicon supported).
* **Simulator:** [Webots](https://cyberbotics.com/) (installed to `/Applications/Webots.app`).
  * *macOS Note:* Gatekeeper must be manually bypassed on first launch (`Control + Click` -> Open).
* **Flight Stack:** [ArduPilot](https://github.com/ArduPilot/ardupilot) (Specifically `ArduCopter` 4.8.0-dev or later).
* **Build System:** The code uses ArduPilot's `waf` build system. Before running the simulation, you must configure and build the SITL binary from the ArduPilot root directory:
  ```bash
  ./waf configure --board sitl
  ./waf copter
  ```

### 2. Python Environment
A dedicated virtual environment (`venv`) is required to bridge Webots, ArduPilot, and the high-level autonomy scripts without system path conflicts.

* **Version:** Python 3.8+
* **Flight Dependencies:** `MAVProxy`, `pymavlink`
* **Autonomy Dependencies (Phase 2/3):** `opencv-python` (vision), `langchain` (ReAct loop)

To create and equip the environment from the ArduPilot root:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -U pymavlink MAVProxy opencv-python langchain
```

### 3. Path & Alias Configuration
To run the dual-terminal setup, the Webots CLI must be aliased within your active `venv`. Add this to your environment setup or `~/.zshrc`:

```bash
# Activate workspace venv
source ~/workspace/ardupilot/venv/bin/activate

# Expose Webots CLI to macOS terminal
alias webots='/Applications/Webots.app/Contents/MacOS/webots'
```

### 4. Running the Autonomous Smoke Test
We have wrapped the complex dual-processor simulation bootup into a single Makefile target for local development. Once your environment is set up and the flight stack is built, you can trigger the autonomous flight test:

```bash
cd UNO_Q_Autonomy
make test-flight
```
This automatically boots Webots in the background, spins up the `arducopter` SITL flight controller cleanly without an interactive MAVProxy console, and then executes our `test_flight.py` High-Level Brain algorithm. Hit `Ctrl-C` at any time to execute the cleanup trap and terminate the background simulator processes.
