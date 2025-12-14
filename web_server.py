"""
-------------------------------------------------------------------------
File:       web_server.py
Version:    1.2.0 (Version Display Fixed)
Author:     Karl @ TechnoShed
Date:       December 2025
Repo:       https://github.com/TechnoShed-dev/ble_prober

Description:
    This module implements the Async Web Server using Microdot.
    It serves the dashboard UI, handles API endpoints, and now reads 
    the system version from main.py to display on the dashboard.
-------------------------------------------------------------------------
"""

from microdot import Microdot, send_file
import scanner
import json
import asyncio
import machine

app = Microdot()
radio_lock = asyncio.Lock()

# --- HELPER: Read Version from main.py ---
def get_system_version():
    """Reads the Version line from the main.py header."""
    try:
        with open('main.py', 'r') as f:
            for i in range(20): # Check top 20 lines
                line = f.readline()
                if "Version:" in line:
                    # Format: "Version:    1.0.7" -> "1.0.7"
                    parts = line.split(':')
                    if len(parts) > 1:
                        return parts[1].strip()
    except:
        pass
    return "Unknown"

# --- ROUTES ---

@app.route('/')
async def index(request):
    return send_file('index.html')

@app.route('/version')
async def version_api(request):
    """API endpoint for frontend to fetch version number"""
    ver = get_system_version()
    return json.dumps({"version": ver}), 200, {'Content-Type': 'application/json'}

@app.route('/scan')
async def start_scan(request):
    print("[WEB] Scan Requested")
    if radio_lock.locked():
        return "Radio is busy, please wait...", 503
        
    async with radio_lock:
        try:
            await scanner.run_scan()
            return "Scan Complete", 200
        except Exception as e:
            print(f"[WEB] Scan Error: {e}")
            return f"Scan Error: {e}", 500

@app.route('/results')
async def get_results(request):
    clean_results = []
    for dev in scanner.found_devices:
        clean_results.append({
            "name": dev['name'],
            "mac": dev['mac'],
            "rssi": dev['rssi']
        })
    return json.dumps(clean_results), 200, {'Content-Type': 'application/json'}

@app.route('/probe/<path:bdaddr>')
async def probe_target(request, bdaddr):
    print(f"[WEB] Probe Requested for: {bdaddr}")
    if radio_lock.locked():
        return json.dumps({"error": "Radio is busy"}), 503

    async with radio_lock:
        try:
            services = await scanner.probe_device(bdaddr)
            return json.dumps(services), 200, {'Content-Type': 'application/json'}
        except Exception as e:
            print(f"[WEB] Probe Error: {e}")
            return json.dumps({"error": str(e)}), 500, {'Content-Type': 'application/json'}

@app.route('/download_log')
async def download_log(request):
    try:
        response = send_file('probe_log.txt')
        response.headers['Content-Disposition'] = 'attachment; filename="probe_log.txt"'
        return response
    except:
        return "Log file not found yet. Run a probe first!", 404

@app.route('/set_time', methods=['POST'])
async def set_time(request):
    try:
        data = request.json
        rtc = machine.RTC()
        # (year, month, day, weekday, hour, minute, second, subsecond)
        rtc.datetime((data['year'], data['month'], data['day'], 0, data['hour'], data['minute'], data['second'], 0))
        print(f"[SYSTEM] Time synced from browser: {data['hour']}:{data['minute']}")
        return "Time Set", 200
    except Exception as e:
        print(f"[SYSTEM] Time sync failed: {e}")
        return "Failed", 400

# --- STARTUP ---

import network
import config 

def start_server():
    # Setup Access Point using settings from config.py
    ap = network.WLAN(network.AP_IF)
    ap.config(essid=config.AP_SSID, password=config.AP_PASS)
    ap.active(True)
    
    # Wait for AP to come up
    while not ap.active():
        pass
        
    print(f"[WEB] AP Started: {config.AP_SSID}")
    print(f"[WEB] Connect and go to: http://{ap.ifconfig()[0]}")
    
    app.run(port=80, debug=True)