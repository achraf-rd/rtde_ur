#!/usr/bin/env python
"""
RTDE Connection Clearer
========================
This utility script helps clear stuck RTDE connections that cause
"An input parameter is already in use" errors.

Run this script when you get the error, then try your main script again.
"""

import sys
sys.path.append("..")

import time
import rtde.rtde as rtde

ROBOT_HOST = "localhost"  # Change to your robot's IP address
ROBOT_PORT = 30004

print("="*70)
print("RTDE CONNECTION CLEARER")
print("="*70)
print(f"\nAttempting to clear RTDE connection on {ROBOT_HOST}:{ROBOT_PORT}")
print("This will help resolve 'input parameter already in use' errors\n")

try:
    print("Step 1: Connecting to robot...")
    con = rtde.RTDE(ROBOT_HOST, ROBOT_PORT)
    con.connect()
    print("✓ Connected")
    
    print("\nStep 2: Getting controller version...")
    version = con.get_controller_version()
    print(f"✓ Controller version: {version}")
    
    print("\nStep 3: Pausing any active RTDE session...")
    con.send_pause()
    print("✓ RTDE paused")
    
    print("\nStep 4: Disconnecting...")
    con.disconnect()
    print("✓ Disconnected")
    
    print("\nStep 5: Waiting for registers to clear (5 seconds)...")
    time.sleep(5)
    
    print("\n" + "="*70)
    print("✓ RTDE CONNECTION CLEARED SUCCESSFULLY")
    print("="*70)
    print("\nYou can now run your RTDE script again.")
    print("If you still get errors, try:")
    print("  1. Restarting the robot controller")
    print("  2. Waiting 10-30 seconds before retrying")
    print("  3. Checking for other RTDE clients connected to the robot")
    
except ConnectionRefusedError:
    print("\n❌ ERROR: Connection refused")
    print("   - Check if robot is turned on")
    print("   - Verify the IP address is correct")
    print("   - Ensure RTDE is enabled in robot settings")
    
except TimeoutError:
    print("\n❌ ERROR: Connection timeout")
    print("   - Check network connection to robot")
    print("   - Verify the IP address is correct")
    print("   - Check firewall settings")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\nTry restarting the robot controller and wait 30 seconds")
    
print("\n")
