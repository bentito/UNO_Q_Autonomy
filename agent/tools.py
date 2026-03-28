import time
import math
from langchain.tools import tool
from pymavlink import mavutil

drone_master = None

def init_mavlink(master):
    """Initializes the global drone master connection for tools to use."""
    global drone_master
    drone_master = master

@tool
def analyze_image(camera_id: str) -> str:
    """
    Analyzes the current image from the specified camera and returns a text description.
    Useful for finding targets (e.g. dog) or identifying obstacles when GPS is denied.
    """
    # Stub implementation
    result = f"Simulated analysis of camera {camera_id}: clear path ahead, target not found."
    print(f"\n\033[95m[VISION LOG] 📷 {result}\033[0m")
    return result

@tool
def get_telemetry() -> str:
    """
    Reads the latest telemetry from the drone, including altitude (m), heading (degrees), and relative position.
    MUST be called before plotting navigation to understand the drone's current state.
    """
    import os
    if os.environ.get("TEST_MODE") == "1":
        res = "Telemetry: Altitude=100.0m, Heading=0.0 degrees (0=North, 90=East)."
        print(f"\n\033[96m[TELEMETRY LOG] 📡 {res}\033[0m")
        return res

    if not drone_master:
        return "Error: Hardware connection not initialized."
    
    # Drain buffer and get the latest messages
    start_time = time.time()
    attitude_msg = None
    pos_msg = None
    
    while True:
        msg = drone_master.recv_match(type=['ATTITUDE', 'GLOBAL_POSITION_INT'], blocking=True, timeout=0.2)
        if not msg:
            break
        if msg.get_type() == 'ATTITUDE':
            attitude_msg = msg
        elif msg.get_type() == 'GLOBAL_POSITION_INT':
            pos_msg = msg
            
        if attitude_msg and pos_msg and (time.time() - start_time > 0.5):
            break
            
    if not attitude_msg or not pos_msg:
        return "Telemetry currently unavailable. Wait and try again."
        
    heading = math.degrees(attitude_msg.yaw)
    if heading < 0:
        heading += 360
        
    alt = pos_msg.relative_alt / 1000.0  # mm to meters
    
    res = f"Telemetry: Altitude={alt:.1f}m, Heading={heading:.1f} degrees (0=North, 90=East)."
    print(f"\n\033[96m[TELEMETRY LOG] 📡 {res}\033[0m")
    return res

@tool
def plot_navigation(target_x: float, target_y: float) -> str:
    """
    Commands the drone to move safely to relative x (forward), y (right) coordinates in meters.
    Example: target_x=5.0 moves 5 meters forward. target_y=-3.0 moves 3 meters left.
    """
    import os
    if os.environ.get("TEST_MODE") == "1":
        res = f"Navigation command issued: moving X:{target_x}m, Y:{target_y}m. Movement initiated."
        print(f"\n\033[92m[NAVIGATION LOG] 🚁 {res}\033[0m")
        return res

    if not drone_master:
        return "Error: Hardware connection not initialized."
        
    print(f"Executing MAVLink command: move_forward X:{target_x}m, Y:{target_y}m...")
    drone_master.mav.set_position_target_local_ned_send(
        0,  
        drone_master.target_system,
        drone_master.target_component,
        mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED,
        0b0000111111111000, # Type mask: only tracking positions (x,y,z)
        target_x,
        target_y,
        0, # Z (down) is 0 so altitude stays the same
        0, 0, 0,
        0, 0, 0,
        0, 0
    )
    
    res = f"Navigation command issued: moving X:{target_x}m, Y:{target_y}m. Movement initiated."
    print(f"\n\033[92m[NAVIGATION LOG] 🚁 {res}\033[0m")
    return res
