# UNO Q Autonomy: Agent Guidelines & Progress

**Primary Directive:** All automated code generation, tooling, and architectural decisions must strictly adhere to the overarching roadmap and hardware constraints defined in [`Project_Plan_Autonomous_GPS-Denied_LLM.md`](Project_Plan_Autonomous_GPS-Denied_LLM.md).

## 1. Current Development Progress

### Autonomous Flight Smoke Test (SITL)
We have successfully established a `pymavlink` bridge simulating the Qualcomm MPU (Brain) controlling the STM32 MCU (Flight Controller) via SITL.

* **Simulation Automation:** `make test-flight` in this directory handles tearing down and cleanly spooling up the Webots 3D environment, the `arducopter` executable, and the Python flight script.
* **EKF Takeoff Rejection Fix:** During development, we encountered MAVLink rejection (error code 4) when attempting to switch the drone to `GUIDED` mode and `TAKEOFF`. The script (`test_flight.py`) is now specifically designed to:
  1. Boot into `STABILIZE`.
  2. Send the `ARM` command (This forces ArduPilot to block until the EKF/MSL altitude establishes a valid lock).
  3. Once armed and props are spinning, switch to `GUIDED` mode.
  4. Send the `MAV_CMD_NAV_TAKEOFF` command safely.
* **Developer Onboarding:** A `DEV_STARTUP_GUIDE.md` was created to outline prerequisites, dependencies, and aliasing for the macOS Webots / SITL environment.

## 2. Immediate Trajectory & Next Steps

If you are picking up this project in a new conversation, your primary objective is to transition from a scripted takeoff to a completely dynamic, vision-driven ReAct agent loop.

### Phase 2: Integrating Vision & LangChain
1. **Camera Feed:** Modify the Webots simulation / SITL link (or Python script) to ingest the virtual FPV camera feed using `opencv-python`.
2. **ReAct Loop:** Bring in `langchain` and establish the core autonomous reasoning loop (Observe -> Think -> Act).
3. **Flight Primitives:** Expand `test_flight.py` to support directional movement (`move_forward`, `yaw`, `hold`) by wrapping `SET_POSITION_TARGET_LOCAL_NED` or `SET_ATTITUDE_TARGET` commands, exposing them as Tools for the LangChain agent.

## 3. Core Hardware Constraints (Reminder)
When designing the Phase 2 agent loop, remember:
- Cannot rely on GPS endpoints or internet for continuous navigation.
- Agent loop happens on the high-level MPU (in Python). Low level obstacle avoidance happens on MCU (C++).
- Failsafes must execute immediately. Over-reliance on LLM reasoning for split-second crash avoidance will fail the physical hardware limits.
