"""
-------------------------------------------------------------------------
File:       display_task.py
Version:    1.0.0
Author:     Karl @ TechnoShed
Description:
    Async Task to handle LCD updates and BME280 readings.
    - Top Line: System Status (Scanning, Idle, etc.)
    - Bottom Line: Time (HH:MM) + Temperature
-------------------------------------------------------------------------
"""

import asyncio
import utime
import BME280
from I2C_LCD import I2CLcd
from machine import I2C, Pin

# --- GLOBAL VARIABLES ---
current_status = "Booting..."
last_status = ""
lcd = None
bme = None

# --- INITIALIZATION ---
def init_hardware():
    global lcd, bme
    try:
        # Screen I2C (as per your main.py snippet)
        i2c_screen = I2C(1, sda=Pin(14), scl=Pin(15), freq=400000)
        lcd = I2CLcd(i2c_screen, 63, 2, 16) # Verify 0x27 or 63 (0x3F) based on your hardware!
        # Note: Your snippet said 63, which is 0x3F. If 0x27 doesn't work, swap to 0x3F.
        
        # Sensor I2C (as per your main.py snippet)
        i2c_sensor = I2C(0, scl=Pin(17), sda=Pin(16), freq=10000)
        bme = BME280.BME280(i2c=i2c_sensor)
        
        lcd.clear()
        lcd.putstr("TechnoShed BLE")
        utime.sleep(1)
        lcd.clear()
        print("[DISPLAY] Hardware Initialized")
    except Exception as e:
        print(f"[DISPLAY] Init Error: {e}")

# --- PUBLIC HELPER ---
def set_status(new_status):
    global current_status
    # Truncate to 16 chars to fit screen
    current_status = new_status[:16]

# --- MAIN LOOP ---
async def run_display_loop():
    global last_status
    
    print("[DISPLAY] Loop Started")
    
    while True:
        if not lcd or not bme:
            await asyncio.sleep(5)
            continue
            
        try:
            # 1. UPDATE TOP LINE (Status) - Only if changed
            if current_status != last_status:
                lcd.move_to(0, 0)
                # Pad with spaces to clear old text
                lcd.putstr(f"{current_status:<16}") 
                last_status = current_status
            
            # 2. READ SENSOR
            # BME280 library is blocking, but fast enough (ms). 
            # If strictly non-blocking is needed, we'd need a different driver, 
            # but for 1s updates, this is fine.
            temp_str = bme.temperature  # e.g., "23.45C"
            # Strip the 'C' and extra decimals if needed to save space
            temp_clean = temp_str.replace("C", "") 
            
            # 3. GET TIME
            t = utime.localtime()
            time_str = "{:02d}:{:02d}".format(t[3], t[4])
            
            # 4. UPDATE BOTTOM LINE
            # Format: "12:30 23.45C    "
            line2 = f"{time_str} {temp_str}"
            lcd.move_to(0, 1)
            lcd.putstr(f"{line2:<16}") # Pad to clear rest of line
            
        except Exception as e:
            print(f"[DISPLAY] Loop Error: {e}")
            
        # Update every 1 second
        await asyncio.sleep(1)