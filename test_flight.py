#!/usr/bin/env python3
# AP_FLAKE8_CLEAN

"""
Minimal autonomous flight script for ArduPilot SITL.
Connects via MAVLink, arms, takes off to 100m, and moves forward 100m.
"""

import argparse
import sys
import time

from pymavlink import mavutil


def wait_heartbeat(master):
    """Wait for a heartbeat to ensure the connection is active."""
    print("Waiting for heartbeat...")
    msg = master.recv_match(type='HEARTBEAT', blocking=True)
    # Force target system/component mapping to match the drone
    master.target_system = msg.get_srcSystem()
    master.target_component = 1 # Force component 1 (Flight Controller)
    print(f"Heartbeat from system (system {master.target_system} component {master.target_component})")


def set_guided_mode(master):
    """Continuously request GUIDED mode and read telemetry until confirmed."""
    print("Waiting for EKF to settle and vehicle to accept GUIDED mode...")
    while True:
        # Clear buffer
        while master.recv_match(blocking=False):
            pass
            
        master.set_mode('GUIDED')
        msg = master.recv_match(type='HEARTBEAT', blocking=True, timeout=2.0)
        if msg:
            mode = mavutil.mode_string_v10(msg)
            if mode == 'GUIDED':
                print("Successfully entered GUIDED mode!")
                break
            else:
                print(f"  Current mode is {mode} (waiting for GUIDED lock...)")


def arm_vehicle(master):
    """Arm the vehicle, retrying until successful (handles EKF settling delay)."""
    print("Attempting to arm vehicle...")
    while True:
        while master.recv_match(blocking=False):
            pass

        master.mav.command_long_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1, 0, 0, 0, 0, 0, 0
        )
        
        start_time = time.time()
        armed = False
        while time.time() - start_time < 5.0:
            msg = master.recv_match(type=['STATUSTEXT', 'HEARTBEAT'], blocking=True, timeout=0.5)
            if not msg:
                continue
            if msg.get_type() == 'STATUSTEXT':
                print(f"  [Drone] {msg.text}")
            elif msg.get_type() == 'HEARTBEAT':
                if msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED:
                    armed = True
                    break
        
        if armed:
            print("Vehicle is officially ARMED!")
            # Brief pause to let rotors spin up
            time.sleep(2)
            break
        else:
            print("  Still waiting/retrying to arm... (Usually due to EKF settling)")
            time.sleep(1)


def takeoff(master, altitude):
    """Command the vehicle to take off to a specific altitude."""
    print(f"Taking off to {altitude}m...")
    while master.recv_match(blocking=False):
        pass

    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,
        0, 0, 0, 0, 0, 0, altitude
    )
    
    # Wait for ACK
    msg = master.recv_match(type='COMMAND_ACK', blocking=True, timeout=3.0)
    if msg and msg.command == mavutil.mavlink.MAV_CMD_NAV_TAKEOFF:
        if msg.result == 0:
            print("  [ACK] Takeoff command accepted!")
        else:
            print(f"  [ACK] Takeoff REJECTED (error code {msg.result}). Retrying...")
    else:
        print("  [ACK] No acknowledgment received for takeoff.")


def move_forward(master, distance):
    """Move forward by a specified distance in meters using LOCAL_NED coordinates."""
    # Coordinate frame 9 is MAV_FRAME_BODY_OFFSET_NED 
    print(f"Commanding vehicle to move forward {distance}m...")
    master.mav.set_position_target_local_ned_send(
        0,  
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_FRAME_BODY_OFFSET_NED,
        0b0000111111111000,
        distance,
        0,
        0,
        0, 0, 0,
        0, 0, 0,
        0, 0
    )


def main():
    parser = argparse.ArgumentParser(description="Run autonomous flight test.")
    parser.add_argument("--connect", default="tcp:127.0.0.1:5760", help="MAVLink connection string")
    args = parser.parse_args()

    print(f"Connecting to {args.connect}...")
    try:
        master = mavutil.mavlink_connection(args.connect)
    except Exception as e:
        print(f"Failed to connect to {args.connect}: {e}")
        sys.exit(1)

    wait_heartbeat(master)
    
    # Arm first. This implicitly waits for the EKF to settle because ArduPilot
    # will refuse to arm until it is. It will stay in STABILIZE mode until done.
    arm_vehicle(master)
    
    # Now that it's armed and EKF is 100% engaged, shift into GUIDED mode.
    # This prevents the mode from spontaneously reverting during boot-up.
    set_guided_mode(master)
    
    takeoff(master, 100)
    
    print("Waiting 25s for takeoff to reach 100m... (assuming ~4m/s climb rate)")
    time.sleep(25)

    move_forward(master, 100)
    print("Navigation command sent. The drone will now fly forward.")


if __name__ == '__main__':
    main()
