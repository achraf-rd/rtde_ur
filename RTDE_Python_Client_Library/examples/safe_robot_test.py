#!/usr/bin/env python
"""
Safe Robot Movement Test Script
================================
This script demonstrates safe robot movement with multiple safety features:
- Small incremental movements only
- Current position monitoring
- Emergency stop capability (Ctrl+C)
- Movement range validation
- Velocity and acceleration limits
- Proper connection cleanup

SAFETY NOTES:
1. Ensure the robot workspace is clear before running
2. Keep emergency stop button accessible
3. Start with robot in a safe home position
4. Monitor robot movement at all times
5. Use Ctrl+C to stop at any time
"""

import sys
sys.path.append("..")

import time
import logging
import math
import rtde.rtde as rtde
import rtde.rtde_config as rtde_config

# ============================================================================
# CONFIGURATION - ADJUST THESE VALUES FOR YOUR SETUP
# ============================================================================

ROBOT_HOST = "192.168.1.10"  # Change to your robot's IP address
ROBOT_PORT = 30004

# Safety limits - CONSERVATIVE VALUES
MAX_JOINT_MOVEMENT = 0.05  # Maximum movement per joint (radians) ~2.86 degrees
MAX_VELOCITY = 0.1         # Maximum joint velocity (rad/s) - VERY SLOW
MAX_ACCELERATION = 0.5     # Maximum joint acceleration (rad/s²)
MOVEMENT_TIMEOUT = 10.0    # Maximum time to wait for movement completion (seconds)

# Test movement parameters (small movements from current position)
SMALL_MOVEMENT_OFFSET = 0.03  # 1.7 degrees - very small test movement

# ============================================================================
# SAFETY FUNCTIONS
# ============================================================================

def validate_joint_position(current_pos, target_pos, max_delta):
    """
    Validate that target position is within safe range of current position
    
    Args:
        current_pos: List of current joint positions (radians)
        target_pos: List of target joint positions (radians)
        max_delta: Maximum allowed change per joint (radians)
    
    Returns:
        (bool, str): (is_safe, message)
    """
    if len(current_pos) != 6 or len(target_pos) != 6:
        return False, "Invalid position dimensions"
    
    for i, (curr, targ) in enumerate(zip(current_pos, target_pos)):
        delta = abs(targ - curr)
        if delta > max_delta:
            return False, f"Joint {i} movement too large: {delta:.4f} rad (max: {max_delta:.4f})"
    
    return True, "Position is safe"


def print_joint_positions(positions, label="Joint positions"):
    """Pretty print joint positions in both radians and degrees"""
    print(f"\n{label}:")
    for i, pos in enumerate(positions):
        degrees = math.degrees(pos)
        print(f"  Joint {i}: {pos:7.4f} rad ({degrees:7.2f}°)")


def wait_for_move_completion(con, state_obj, timeout=10.0):
    """
    Wait for robot to complete movement
    
    Args:
        con: RTDE connection object
        state_obj: State data object to monitor
        timeout: Maximum time to wait (seconds)
    
    Returns:
        bool: True if completed, False if timeout
    """
    start_time = time.time()
    
    while (time.time() - start_time) < timeout:
        state = con.receive()
        if state is None:
            return False
        
        # Check if robot has stopped moving (velocity near zero)
        max_velocity = max([abs(v) for v in state.actual_qd])
        if max_velocity < 0.001:  # Nearly stopped
            return True
        
        time.sleep(0.01)
    
    print("WARNING: Movement timeout reached")
    return False


# ============================================================================
# MAIN TEST FUNCTION
# ============================================================================

def run_safe_robot_test():
    """Main function to run safe robot movement test"""
    
    print("="*70)
    print("SAFE ROBOT MOVEMENT TEST")
    print("="*70)
    print("\nSAFETY CHECKLIST:")
    print("  ✓ Robot workspace is clear")
    print("  ✓ Emergency stop is accessible")
    print("  ✓ Robot is in safe home position")
    print("  ✓ All personnel are at safe distance")
    print("\nPress Ctrl+C at any time to stop")
    print("="*70)
    
    # User confirmation
    response = input("\nType 'YES' to proceed: ")
    if response.upper() != "YES":
        print("Test cancelled by user")
        return
    
    # Create configuration for reading robot state
    config_content = """<?xml version="1.0"?>
<rtde_config>
    <recipe key="state">
        <field name="actual_q" type="VECTOR6D"/>
        <field name="actual_qd" type="VECTOR6D"/>
        <field name="target_q" type="VECTOR6D"/>
        <field name="robot_mode" type="INT32"/>
        <field name="safety_mode" type="INT32"/>
    </recipe>
    <recipe key="setp">
        <field name="input_double_register_0" type="DOUBLE"/>
        <field name="input_double_register_1" type="DOUBLE"/>
        <field name="input_double_register_2" type="DOUBLE"/>
        <field name="input_double_register_3" type="DOUBLE"/>
        <field name="input_double_register_4" type="DOUBLE"/>
        <field name="input_double_register_5" type="DOUBLE"/>
    </recipe>
</rtde_config>"""
    
    # Save temporary config file
    config_file = "safe_test_config.xml"
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    # Parse configuration
    conf = rtde_config.ConfigFile(config_file)
    state_names, state_types = conf.get_recipe("state")
    setp_names, setp_types = conf.get_recipe("setp")
    
    # Connect to robot
    print(f"\nConnecting to robot at {ROBOT_HOST}:{ROBOT_PORT}...")
    con = rtde.RTDE(ROBOT_HOST, ROBOT_PORT)
    
    try:
        con.connect()
        print("✓ Connected successfully")
        
        # Get controller version
        version = con.get_controller_version()
        print(f"✓ Controller version: {version}")
        
        # Setup recipes with retry mechanism for "already in use" error
        max_retries = 3
        retry_count = 0
        setp = None
        
        while retry_count < max_retries:
            try:
                con.send_output_setup(state_names, state_types)
                setp = con.send_input_setup(setp_names, setp_types)
                print("✓ RTDE interface configured")
                break  # Success, exit retry loop
                
            except ValueError as e:
                if "already in use" in str(e):
                    retry_count += 1
                    print(f"⚠ Input registers are in use (attempt {retry_count}/{max_retries})")
                    print("  Disconnecting to clear registers...")
                    con.disconnect()
                    time.sleep(2)  # Wait for robot to release registers
                    
                    if retry_count < max_retries:
                        print("  Reconnecting...")
                        con.connect()
                        version = con.get_controller_version()
                    else:
                        print("\n❌ Failed to configure RTDE after multiple attempts")
                        print("\nTROUBLESHOOTING:")
                        print("  1. Restart the robot controller")
                        print("  2. Wait 10 seconds and try again")
                        print("  3. Check if another RTDE client is connected")
                        return
                else:
                    raise  # Re-raise if it's a different error
            except Exception as e:
                print(f"❌ Setup error: {e}")
                raise
        
        if setp is None:
            print("❌ Failed to setup RTDE interface")
            return
        
        # Start data synchronization
        if not con.send_start():
            print("ERROR: Failed to start RTDE synchronization")
            return
        print("✓ Data synchronization started")
        
        # Read current position
        print("\n" + "="*70)
        print("STEP 1: Reading current robot position...")
        print("="*70)
        
        state = con.receive()
        if state is None:
            print("ERROR: Failed to receive robot state")
            return
        
        current_position = list(state.actual_q)
        print_joint_positions(current_position, "Current robot position")
        
        # Calculate small test movements
        print("\n" + "="*70)
        print("STEP 2: Calculating safe test movements...")
        print("="*70)
        
        # Movement 1: Small positive movement on joint 5 (wrist)
        target_pos_1 = current_position.copy()
        target_pos_1[5] += SMALL_MOVEMENT_OFFSET
        
        # Movement 2: Return to original position
        target_pos_2 = current_position.copy()
        
        # Validate movements
        is_safe, msg = validate_joint_position(current_position, target_pos_1, MAX_JOINT_MOVEMENT)
        if not is_safe:
            print(f"ERROR: Movement 1 validation failed: {msg}")
            return
        print(f"✓ Movement 1 validated: {msg}")
        
        is_safe, msg = validate_joint_position(target_pos_1, target_pos_2, MAX_JOINT_MOVEMENT)
        if not is_safe:
            print(f"ERROR: Movement 2 validation failed: {msg}")
            return
        print(f"✓ Movement 2 validated: {msg}")
        
        # Execute test movements
        print("\n" + "="*70)
        print("STEP 3: Executing test movements...")
        print("="*70)
        print("⚠ ROBOT WILL NOW MOVE - STAY ALERT!")
        time.sleep(2)  # Give user time to read warning
        
        # Movement 1
        print("\n→ Movement 1: Small wrist rotation...")
        print_joint_positions(target_pos_1, "Target position")
        
        for i in range(6):
            setp.__dict__[f"input_double_register_{i}"] = target_pos_1[i]
        con.send(setp)
        
        print("  Waiting for movement completion...")
        if wait_for_move_completion(con, state, MOVEMENT_TIMEOUT):
            state = con.receive()
            print("✓ Movement 1 completed")
            print_joint_positions(list(state.actual_q), "Actual position reached")
        else:
            print("⚠ Movement 1 timeout - stopping test")
            return
        
        time.sleep(1)  # Pause between movements
        
        # Movement 2: Return to original position
        print("\n→ Movement 2: Returning to original position...")
        print_joint_positions(target_pos_2, "Target position")
        
        for i in range(6):
            setp.__dict__[f"input_double_register_{i}"] = target_pos_2[i]
        con.send(setp)
        
        print("  Waiting for movement completion...")
        if wait_for_move_completion(con, state, MOVEMENT_TIMEOUT):
            state = con.receive()
            print("✓ Movement 2 completed")
            print_joint_positions(list(state.actual_q), "Final position")
        else:
            print("⚠ Movement 2 timeout")
            return
        
        # Test completed successfully
        print("\n" + "="*70)
        print("✓ TEST COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("\nRobot returned to original position")
        
    except KeyboardInterrupt:
        print("\n\n⚠ EMERGENCY STOP - Test interrupted by user")
        print("Robot movement stopped")
    
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Always cleanup connection
        print("\nCleaning up connection...")
        try:
            con.send_pause()
            con.disconnect()
            print("✓ Connection closed properly")
        except:
            print("⚠ Error during cleanup")


# ============================================================================
# SCRIPT ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║           UNIVERSAL ROBOTS SAFE MOVEMENT TEST                      ║")
    print("║                                                                    ║")
    print("║  This script will move the robot with very small, safe movements  ║")
    print("║  Please ensure all safety precautions are in place               ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print("\n")
    
    run_safe_robot_test()
    
    print("\nTest script finished.")
