import time
import os
import sys
from pymavlink import mavutil
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from tools import analyze_image, plot_navigation, get_telemetry, init_mavlink

TEST_MODE = os.environ.get("TEST_MODE") == "1"

def wait_heartbeat(master):
    if TEST_MODE: return
    print("Waiting for heartbeat...")
    msg = master.recv_match(type='HEARTBEAT', blocking=True)
    master.target_system = msg.get_srcSystem()
    master.target_component = 1
    print(f"Heartbeat from system {master.target_system} component {master.target_component}")

def set_guided_mode(master):
    if TEST_MODE: return
    print("Waiting for EKF to settle and vehicle to accept GUIDED mode...")
    while True:
        while master.recv_match(blocking=False):
            pass
        master.set_mode('GUIDED')
        msg = master.recv_match(type='HEARTBEAT', blocking=True, timeout=2.0)
        if msg:
            mode = mavutil.mode_string_v10(msg)
            if mode == 'GUIDED':
                print("Successfully entered GUIDED mode!")
                break

def arm_vehicle(master):
    if TEST_MODE: return
    print("Attempting to arm vehicle...")
    while True:
        while master.recv_match(blocking=False):
            pass
        master.mav.command_long_send(
            master.target_system, master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 1, 0, 0, 0, 0, 0, 0
        )
        start_time = time.time()
        armed = False
        while time.time() - start_time < 5.0:
            msg = master.recv_match(type='HEARTBEAT', blocking=True, timeout=0.5)
            if msg and (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED):
                armed = True
                break
        if armed:
            print("Vehicle is officially ARMED!")
            time.sleep(2)
            break
        time.sleep(1)

def takeoff(master, altitude):
    if TEST_MODE: return
    print(f"Taking off to {altitude}m...")
    while master.recv_match(blocking=False):
            pass
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0, 0, 0, 0, 0, 0, 0, altitude
    )
    msg = master.recv_match(type='COMMAND_ACK', blocking=True, timeout=3.0)
    if msg and msg.command == mavutil.mavlink.MAV_CMD_NAV_TAKEOFF and msg.result == 0:
        print("  [ACK] Takeoff command accepted!")

def main():
    print("Initializing UNO Q Autonomy Agent...")
    print("Hardware Profile Target: Qualcomm Dragonwing MPU (Debian + llama.cpp)")
    
    # Initialize the LLM (connects to the local llama.cpp server instance)
    llm = ChatOpenAI(
        model="qwen2.5-vl", 
        base_url="http://localhost:11434/v1",
        api_key="sk-no-key-required",
        temperature=0.1
    )
    # Connect to SITL
    if not TEST_MODE:
        # Inside the container, host is usually host.containers.internal
        connection_string = os.environ.get("MAVLINK_CONN", "tcp:host.containers.internal:5760")
        print(f"Connecting to SITL at {connection_string}...")
        try:
            master = mavutil.mavlink_connection(connection_string)
        except Exception as e:
            print(f"Failed to connect: {e}")
            sys.exit(1)
    else:
        master = None
        print("Running in TEST_MODE: MAVLink connection bypassed.")

    wait_heartbeat(master)
    arm_vehicle(master)
    set_guided_mode(master)
    takeoff(master, 100) # Safe altitude for test
    
    if not TEST_MODE:
        print("Waiting 25s for takeoff to reach 100m...")
        time.sleep(25)
    
    init_mavlink(master)
    
    tools = [analyze_image, get_telemetry, plot_navigation]
    
    system_prompt = """You are an autonomous quadcopter AI navigating a GPS-denied environment.
Your primary objective is to find a dog using your camera. 
You control the drone via the provided tools.

### DRONE FLIGHT MANUAL & CONSTRAINTS:
1. **Always Check Telemetry First:** Before moving, you MUST call `get_telemetry` to understand your current altitude and heading.
2. **Coordinate System (NED):** When calling `plot_navigation(target_x, target_y)`:
   - `target_x` moves you FORWARD by that many meters. 
   - `target_y` moves you RIGHT by that many meters.
   - Negative values move BACKWARD or LEFT.
   - Example: `target_x=5, target_y=0` moves you 5 meters directly forward relative to your current heading.
3. **Flight Constraints:** Do NOT make large leaps. Move in small increments (e.g., 2 to 5 meters at a time) to avoid crashing or losing your target.
4. **Action Sequence:** 
   - Call `analyze_image` to check for obstacles or the target.
   - Call `get_telemetry` to check status.
   - Call `plot_navigation` to move safely based on the image analysis.
   
### CRITICAL INSTRUCTION ON TOOL USAGE:
You MUST invoke the functions via Native Tool Calling.
DO NOT write python code blocks like ` ```python analyze_image() ``` `.
Instead, use the OpenAI-style JSON tool calling format.
For example, if you want to check your altitude, your response should natively invoke the `get_telemetry` tool.
Take it one step at a time."""

    # Initialize the modern LangChain agent
    agent = create_agent(model=llm, tools=tools, system_prompt=system_prompt)
    
    print("Agent is initialized. Beginning control loop...")
    
    try:
        tick = 0
        while True:
            tick += 1
            print(f"\n--- New Agent Tick [{tick}] ---")
            
            # The overarching objective for the agent in this context
            objective = "Run your analysis and standard grid search loop. Find the target."
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Trigger the observe -> think -> act loop
                    print(f"\n\033[93m[AGENT INVOCATION]\033[0m Starting ReAct reasoning...")
                    
                    response = agent.invoke({"messages": [{"role": "user", "content": objective}]})
                    
                    found_action = False
                    ai_text = ""
                    for msg in response.get("messages", []):
                        if getattr(msg, "type", "") == "human":
                            continue
                            
                        # Agent message (could contain thoughts and tool calls)
                        if getattr(msg, "type", "") == "ai":
                            content = getattr(msg, "content", "")
                            if content and isinstance(content, str) and content.strip():
                                ai_text = content.strip()
                                print(f"\033[93m[AGENT REASONING]\033[0m {ai_text}")
                            elif content and isinstance(content, list):
                                content_str = " ".join(str(c.get("text", c)) if isinstance(c, dict) else str(c) for c in content)
                                if content_str.strip():
                                    ai_text = content_str.strip()
                                    print(f"\033[93m[AGENT REASONING]\033[0m {ai_text}")
                            
                            # Log the tool calls requested by the agent
                            tool_calls = getattr(msg, "tool_calls", [])
                            if tool_calls:
                                found_action = True
                                for tc in tool_calls:
                                    print(f"\033[94m[THOUGHT]\033[0m Agent requested tool: {tc.get('name', getattr(tc, 'name', ''))} with args {tc.get('args', getattr(tc, 'args', ''))}")
                                    
                        # Tool execution result
                        elif getattr(msg, "type", "") == "tool":
                            # The tools implicitly printed their own color logs, but we can print the raw response here too 
                            print(f"\033[90m[TOOL OUTPUT]\033[0m {getattr(msg, 'content', '')}")
                    
                    if not found_action:
                        # Fallback for 3B models: manually parse the text for Python-like tool invocations
                        import re
                        raw_text = ai_text
                        
                        tool_match = None
                        rt_lower = raw_text.lower()
                        if "analyz" in rt_lower:
                            tool_match = ("analyze_image", {"camera_id": "front"})
                        elif "telemetry" in rt_lower:
                            tool_match = ("get_telemetry", {})
                        else:
                            # Try to match plot_navigation(...) or similar
                            match = re.search(r'plot.*?(forward|navig|move).*?(-?\d+).*?(-?\d+)', rt_lower)
                            if match:
                                tool_match = ("plot_navigation", {"target_x": int(match.group(2)), "target_y": int(match.group(3))})
                            elif "plot" in rt_lower or "move" in rt_lower or "navig" in rt_lower:
                                # Safe default leap if it forgets args
                                tool_match = ("plot_navigation", {"target_x": 5, "target_y": 0})
                        
                        if tool_match:
                            found_action = True
                            tool_name, tool_args = tool_match
                            print(f"\033[94m[THOUGHT - TEXT FALLBACK]\033[0m Agent requested tool via text: {tool_name} with args {tool_args}")
                            
                            # Execute it manually since the LangChain agent didn't catch it
                            print(f"\033[90m[TOOL MANUAL EXECUTION]\033[0m Running {tool_name}...")
                            try:
                                if tool_name == "analyze_image":
                                    tools[0].invoke(tool_args)
                                elif tool_name == "get_telemetry":
                                    tools[1].invoke(tool_args)
                                elif tool_name == "plot_navigation":
                                    tools[2].invoke(tool_args)
                            except Exception as e:
                                print(f"Error executing manual fallback tool: {e}")
                                
                    if not found_action:
                        print("\033[91m[WARNING]\033[0m Agent did not attempt to use any tools in this tick.")
                        
                    break
                except Exception as e:
                    print(f"Error in agent processing (Attempt {attempt+1}/{max_retries}): {e}")
                    if attempt == max_retries - 1:
                        if TEST_MODE:
                            print("TEST_MODE: Agent tick failed. Exiting with error.")
                            sys.exit(1)
                        else:
                            break
                    time.sleep(5)
                
            if TEST_MODE:
                print("TEST_MODE: First tick completed successfully.")
                break
                
            # Simulate the internal serial / processing latency constraint of the actual hardware
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("Agent shutting down.")

if __name__ == "__main__":
    main()
