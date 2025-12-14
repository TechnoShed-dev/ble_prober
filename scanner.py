"""
-------------------------------------------------------------------------
File:       scanner.py
Version:    1.0.7 (Long-Run Stability)
Author:     Karl @ TechnoShed
Date:       December 2025
Repo:       https://github.com/TechnoShed-dev/ble_prober

Description:
    This module handles the BLE Central role for the Pico Prober.
    
    v1.0.7 Update:
    - Added garbage collection (gc.collect) to prevent memory leaks over time.
    - Added explicit radio stop commands to prevent resource exhaustion.
    - Improved cleanup logic to ensure the radio doesn't hang after 
      multiple consecutive probes.

Dependencies:
    - aioble, bluetooth, asyncio
    - config, status_led, gc
-------------------------------------------------------------------------
"""

import aioble
import bluetooth
import asyncio
import time
import gc       # <--- Added Garbage Collection
import config
import status_led

# --- CONSTANTS & LOOKUPS ---

UUID_NAMES = {
    "0x1800": "Generic Access",
    "0x1801": "Generic Attribute",
    "0x180a": "Device Information",
    "0x180f": "Battery Service",
    "0x180d": "Heart Rate",
    "0x1815": "Automation IO",
    "0x1809": "Health Thermometer",
    "0xffe0": "HM-10 Serial (Proprietary)",
    "0xfebe": "Bose Proprietary"
}

found_devices = []

async def run_scan():
    # 1. CLEANUP MEMORY BEFORE STARTING
    gc.collect()
    
    status_led.set_state(status_led.SCANNING)
    duration_ms = config.SCAN_DURATION_MS
    print(f"[BLE] Starting Scan for {duration_ms}ms (Threshold: {config.RSSI_THRESHOLD}dBm)...")
    
    found_devices.clear()
    
    try:
        async with aioble.scan(duration_ms, interval_us=30000, window_us=30000, active=True) as scanner:
            async for result in scanner:
                if result.rssi < config.RSSI_THRESHOLD: continue

                if result.connectable:
                    raw_name = result.name()
                    device_name = raw_name if raw_name else "Unknown"
                    mac_addr = str(result.device.addr_hex())
                    
                    if config.FILTER_NAMED_ONLY and device_name == "Unknown": pass 
                    
                    existing_dev = None
                    for dev in found_devices:
                        if dev['mac'] == mac_addr:
                            existing_dev = dev
                            break
                    
                    if existing_dev:
                        if existing_dev['name'] == "Unknown" and device_name != "Unknown":
                            existing_dev['name'] = device_name
                        existing_dev['rssi'] = result.rssi
                        existing_dev['device_obj'] = result.device
                    else:
                        if config.FILTER_NAMED_ONLY and device_name == "Unknown": continue
                        print(f"[BLE] Found: {device_name} ({mac_addr}) RSSI: {result.rssi}")
                        found_devices.append({
                            "name": device_name,
                            "mac": mac_addr,
                            "rssi": result.rssi,
                            "device_obj": result.device
                        })
    except Exception as e:
        print(f"[BLE] Scan Error: {e}")
    finally:
        print(f"[BLE] Scan finished. Found {len(found_devices)} targets.")
        status_led.set_state(status_led.IDLE)
        gc.collect() # Cleanup after scan

def _resolve_uuid(uuid_obj):
    if uuid_obj is None: return "Unknown (None)"
    s_uuid = str(uuid_obj)
    if s_uuid in UUID_NAMES: return f"{s_uuid} ({UUID_NAMES[s_uuid]})"
    return s_uuid

def log_to_file(device_name, bdaddr, services):
    try:
        t = time.localtime()
        time_str = "{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(t[1], t[2], t[3], t[4], t[5])
        filename = config.LOG_FILE
        
        with open(filename, "a") as f:
            f.write("--------------------------------------------------\n")
            f.write(f"PROBE REPORT: {time_str}\n")
            f.write(f"Device:  {device_name}\n")
            f.write(f"Address: {bdaddr}\n")
            f.write("Services Found:\n")
            for s_uuid, data in services.items():
                f.write(f"  + Service: {data['name']}\n")
                for char in data['chars']:
                    f.write(f"      - Char: {char['uuid']} {char['props']}\n")
            f.write("\n")
        print(f"[SYSTEM] Log saved to {filename}")
    except Exception as e:
        print(f"[SYSTEM] Logging failed: {e}")

async def probe_device(bdaddr):
    # MEMORY CLEANUP
    gc.collect()
    status_led.set_state(status_led.CONNECTING)
    
    # Radio Cooldown
    await asyncio.sleep(0.5)
    
    print(f"[BLE] Connecting to {bdaddr}...")
    
    device_name = "Unknown Device"
    target_device = None
    
    for dev in found_devices:
        if dev['mac'] == bdaddr:
            target_device = dev['device_obj']
            device_name = dev['name']
            break
            
    if not target_device:
        print("[BLE] Warn: Device not in list, trying blind connect...")
        try:
            target_device = aioble.Device(bluetooth.ADDR_PUBLIC, bluetooth.UUID(bdaddr))
        except:
            status_led.set_state(status_led.IDLE)
            raise ValueError("Invalid Address")

    services_dict = {}
    device_connection = None

    max_retries = 2
    for attempt in range(max_retries):
        try:
            device_connection = await target_device.connect(timeout_ms=10000)
            break 
        except OSError as e:
            if e.errno == 107 or e.errno == 22:
                print(f"[BLE] Radio busy (Error {e.errno}), retrying... ({attempt+1}/{max_retries})")
                await asyncio.sleep(1.0)
                continue
            elif attempt < max_retries - 1:
                print(f"[BLE] Connect failed ({e}), retrying...")
                await asyncio.sleep(1.0)
                continue
            else:
                status_led.set_state(status_led.ERROR)
                asyncio.create_task(reset_led_later(2))
                print(f"[BLE] Connection Failed: {e}")
                raise e
        except asyncio.TimeoutError:
            print("[BLE] Connection Timed Out.")
            if attempt < max_retries - 1:
                print("[BLE] Retrying connection...")
                await asyncio.sleep(1.0)
                continue
            status_led.set_state(status_led.ERROR)
            asyncio.create_task(reset_led_later(2))
            raise Exception("Connection Timeout")

    print(f"[BLE] Connected to {device_name}. Settling (1s)...")
    await asyncio.sleep(1.0)

    try:
        print("[BLE] Enumerating Services...")
        try:
            async for service in device_connection.services():
                try:
                    if not service or service.uuid is None: continue
                    s_uuid = str(service.uuid)
                    s_name = _resolve_uuid(service.uuid)
                    print(f"[BLE] Found Service: {s_name}")
                    services_dict[s_uuid] = {"name": s_name, "chars": []}
                    await asyncio.sleep(0.1) 
                    async for char in service.characteristics():
                        try:
                            if not char or char.uuid is None: continue
                            c_uuid = str(char.uuid)
                            props = []
                            if char.properties & bluetooth.FLAG_READ: props.append("R")
                            if char.properties & bluetooth.FLAG_WRITE: props.append("W")
                            if char.properties & bluetooth.FLAG_NOTIFY: props.append("N")
                            services_dict[s_uuid]["chars"].append({"uuid": c_uuid, "props": props})
                        except: continue
                except (TypeError, AttributeError, ValueError) as e:
                    print(f"[BLE] Skipped malformed service data: {e}")
                    continue
        except TypeError:
            print("[BLE] Device sent invalid Service Table.")
        except Exception as e:
            print(f"[BLE] Service Iterator Error: {e}")

        log_to_file(device_name, bdaddr, services_dict)

    except Exception as e:
        status_led.set_state(status_led.ERROR)
        asyncio.create_task(reset_led_later(2))
        print(f"[BLE] Critical Enumeration Error: {e}")
        raise e
    finally:
        if device_connection:
            try:
                await device_connection.disconnect()
                print("[BLE] Disconnected.")
            except: pass
        
        status_led.set_state(status_led.IDLE)
        gc.collect() # Final Cleanup
            
    return services_dict

async def reset_led_later(seconds):
    await asyncio.sleep(seconds)
    status_led.set_state(status_led.IDLE)