# Project Plan: Autonomous GPS-Denied Navigation & Interaction

This document outlines the development roadmap for an autonomous, GPS-denied drone system. The architecture is designed on a macOS SITL/Webots superset and targeted for deployment on the **Arduino UNO Q 4GB** (utilizing its dual-brain Qualcomm Dragonwing QRB2210 MPU and STM32U585 MCU architecture).

## 1. System Architecture

The software stack is divided to match the target hardware's dual-processor design, ensuring a seamless transition from Mac simulation to the UNO Q.

* **High-Level Brain (Target: UNO Q MPU - Debian Linux):**
    * **Deployment:** Executed as an OCI container (via Podman) to ensure environment consistency from macOS development straight to the physical eMMC storage on the MPU.
    * **Autonomy Engine:** Python-based LangChain ReAct loop orchestrating mission objectives.
    * **Vision Pipeline:** OpenCV edge tracing and lightweight inferencing (e.g., YOLOv8-nano or TensorFlow Lite) tuned for the Qualcomm Adreno GPU.
    * **Comms:** `pymavlink` or MAVSDK to bridge high-level decisions to flight commands.
* **Low-Level Flight (Target: ArduPilot / UNO Q MCU):**
    * **Deployment:** Compiled as a monolithic bare-metal firmware image (`.apj`/`.bin`) running on the ChibiOS RTOS. No containerization is used, as this is deployed directly to the STM32 microcontroller.
    * **Flight Controller:** Handles PID loops, motor mixing, and immediate obstacle avoidance.
    * **Sensors:** Optical flow and LiDAR (for GPS-denied velocity/altitude hold), processed locally.

* **Development / macOS SITL Environment:**
    * **Simulation Container:** Software-In-The-Loop (SITL) and the ArduCopter build environment can optionally be containerized (Ubuntu-based) on the macOS host to maintain a clean, isolated workflow mimicking the firmware's target Linux CI environments.

## 2. Phase 1: Simulation Customization (The "Superset" Model)

Before writing autonomy code, the macOS simulation must accurately restrict itself to mimic the UNO Q's physical limitations.

* **[ ] Video Feed Extraction:** Write a Python script to pull the raw FPV camera array directly from the Webots API (bypassing MAVProxy) to act as the "local camera" feed.
* **[ ] Model Latency (MPU constraint):** Introduce a strict `time.sleep()` or async delay loop in the Mac's vision pipeline to cap frame processing at 15-30 FPS, simulating the Dragonwing processor's throughput.
* **[ ] Model Bandwidth (Telemetry constraint):** Cap the MAVLink message rate between the Python control script and ArduPilot to simulate the internal serial/RPC limits between the UNO Q's MPU and MCU.

## 3. Phase 2: Vision & State Estimation (GPS-Denied)

Since GPS is unavailable, the drone must rely on visual odometry and edge detection to understand its position and find the target (dog).

* **[ ] Edge Tracing:** Implement Fast OpenCV edge detection (Canny/Sobel) to identify walls and corridors for indoor grid-search navigation.
* **[ ] Target Inferencing:** Train/deploy a lightweight object detection model specifically for "Dog".
* **[ ] Telemetry Fusion:** Combine optical flow sensor data (from ArduPilot SITL) with the vision model to maintain a localized map grid of where the drone has already searched.

## 4. Phase 3: The ReAct Autonomy Loop

Implement the LangChain framework to convert natural language objectives ("find a dog, give treat, return on low battery") into executable drone behaviors.

* **[ ] Tool Creation:** Define strict Python functions for the LLM to call:
    * `initiate_grid_search(area_bounds)`
    * `scan_for_target(target_class="dog")`
    * `trigger_payload(payload="treat_dispenser")`
    * `get_battery_state()`
    * `execute_return_to_home()`
* **[ ] The Decision Loop:** Implement a LangChain Agent (using a lightweight local LLM or an API via WiFi) that continuously evaluates the camera state and battery state against the primary objective.
* **[ ] Failsafe Interruption:** Build a hardware-interrupt simulation where if battery drops below 15%, the LangChain loop is overridden, and `execute_return_to_home()` is forced.

## 5. Phase 4: Hardware Porting (Arduino UNO Q 4GB)

Transition the verified Python/SITL code from the Mac to the physical board.

* **[ ] Debian Environment Setup:** Flash the UNO Q with the latest Debian image. Configure Python `venv`, OpenCV, and Edge Impulse/TFLite runtimes on the 32GB eMMC.
* **[ ] App Lab / RPC Integration:** Use Arduino App Lab to map the high-level Python commands (from the Qualcomm MPU) over the built-in RPC to the STM32 MCU.
* **[ ] Peripheral Mapping:** Wire the physical camera to the MPU (via USB-C dongle or MIPI) and the flight controller telemetry to the MCU's high-speed headers.
* **[ ] Field Testing:** Run the ReAct loop in a controlled physical environment.