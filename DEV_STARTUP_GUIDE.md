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

### 5. Running the Agent Container (Podman)

The High-Level Brain (LangChain + Vision) can run inside a Debian container to simulate the physical eMMC storage and OS of the Qualcomm Dragonwing MPU on the UNO Q.

> **Note on macOS GPU Paravirtualization:** We require `--device /dev/dri` to ensure the simulated LLM operations run with Metal GPU acceleration (using Vulkan/virtio-gpu translation) rather than flat CPU. This yields roughly 70-80% of native Metal performance, perfectly simulating the Qualcomm Adreno compute limits.
>
> **Enabling `/dev/dri` on macOS:** Standard Apple Hypervisor VMs do not expose the GPU. You MUST recreate your Podman machine using the `libkrun` provider (requires Podman 5.2+). The command line flag was replaced by an environment variable in Podman 5.x, and it requires the `krunkit` package from a specific Homebrew tap:
> ```bash
> brew tap slp/krun       # Add the required repository
> brew install krunkit    # Required for the virtio-gpu macOS translation backend
> 
> export CONTAINERS_MACHINE_PROVIDER=libkrun  # Tell podman to use libkrun for all following commands
> 
> podman machine rm       # Warning: this deletes your existing podman images/containers!
> podman machine init --disk-size 50
> podman machine start
> ```

Use the `Makefile` to build and test the agent:

```bash
cd UNO_Q_Autonomy
make build-agent
make run-agent
```
