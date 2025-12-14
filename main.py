"""
-------------------------------------------------------------------------
File:       main.py
Version:    1.1.1 (Single Config)
Author:     Karl @ TechnoShed
Date:       December 2025
Repo:       https://github.com/TechnoShed-dev/ble_prober

Description:
    Application Entry Point.
    
    SEQUENCE:
    1. Smart Sync: Scans for known networks (from config.py).
    2. If found, connects and syncs time via NTP.
    3. Disconnects and switches to AP Mode.
    4. Starts the Web Server.

Dependencies:
    - web_server, config, ntptime, network
-------------------------------------------------------------------------
"""

import network
import utime
import ntptime
import machine
import asyncio
import web_server
import config  # <--- Changed from config_credentials
import status_led

# --- HELPER FUNCTIONS ---

def connect_for_sync(wlan):
    """Smart Connect (Blocking): Scans first, connects to highest priority visible network."""
    print("[SYSTEM] Starting Smart Scan...")
    
    target_net = None
    
    try:
        # 1. SCAN PHASE
        scan_results = wlan.scan()
        visible_ssids = [s[0].decode() for s in scan_results]
        print(f"[SYSTEM] Visible Networks: {visible_ssids}")
        
        # Priority Match: Iterate known list in config.py
        for net in config.KNOWN_NETWORKS:  # <--- Updated Reference
            if net['ssid'] in visible_ssids:
                target_net = net
                print(f"[SYSTEM] Match Found: {target_net['ssid']}")
                break 
    except Exception as e:
        print(f"[SYSTEM] Boot Scan Error: {e}")
        return False

    # 2. CONNECT PHASE
    if target_net:
        print(f"[SYSTEM] Connecting to {target_net['ssid']}...")
        wlan.config(pm=0xa11140) # Disable power saving for stability
        wlan.connect(target_net['ssid'], target_net['pass'])
        
        for i in range(15):
            if wlan.isconnected():
                print("[SYSTEM] Connected!")
                return True
            print(".", end="")
            utime.sleep(1)
        
        print("\n[SYSTEM] Connection Timed Out.")
            
    return False

def sync_time_ntp():
    """Sets RTC via NTP on startup."""
    print("[SYSTEM] Attempting Time Sync...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if connect_for_sync(wlan):
        try:
            print("[SYSTEM] Fetching NTP time...")
            ntptime.settime() 
            t = utime.localtime()
            if t[0] >= 2024:
                 print(f"[SYSTEM] RTC Set Successfully: {t[0]}-{t[1]}-{t[2]} {t[3]}:{t[4]}")
            else:
                 print("[SYSTEM] NTP Sync failed (Year invalid).")
        except Exception as e:
            print(f"[SYSTEM] NTP Error: {e}")
    else:
        print("[SYSTEM] No known networks found. Skipping Time Sync.")

    print("[SYSTEM] Closing Sync Connection...")
    wlan.disconnect()
    wlan.active(False)
    utime.sleep(1)

# --- MAIN EXECUTION ---

if __name__ == "__main__":
    try:
        # 1. Start the LED Loop immediately
        loop = asyncio.get_event_loop()
        loop.create_task(status_led.run_led_loop())

        # 2. Run the Smart Sync
        # Set LED to Connecting while syncing
        status_led.set_state(status_led.CONNECTING) 
        sync_time_ntp()
        
        print("-" * 40)
        
        # 3. Launch Web Server
        # Set LED to Idle when ready
        status_led.set_state(status_led.IDLE)
        web_server.start_server()
        
    except KeyboardInterrupt:
        print("[SYSTEM] Application Stopped by User.")
    except Exception as e:
        status_led.set_state(status_led.ERROR) # <--- Visual Error indication
        print(f"[SYSTEM] Critical Error: {e}")