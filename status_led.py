"""
-------------------------------------------------------------------------
File:       status_led.py
Version:    1.0.0
Author:     Karl @ TechnoShed
Description:
    Async LED Status Indicator for Pico W.
    Controls the onboard LED to give visual feedback on system state.
-------------------------------------------------------------------------
"""

import machine
import asyncio

# Define States
IDLE = "IDLE"           # Slow Blink
SCANNING = "SCANNING"   # Fast Blink
CONNECTING = "CONNECTING" # Medium Blink
ERROR = "ERROR"         # Solid On

# Global State Variable
current_state = IDLE

# Setup the LED (Pico W uses string "LED", regular Pico uses Pin 25)
try:
    led = machine.Pin("LED", machine.Pin.OUT)
except:
    # Fallback for older non-W Picos just in case
    led = machine.Pin(25, machine.Pin.OUT)

def set_state(new_state):
    global current_state
    current_state = new_state

async def run_led_loop():
    """Main async loop to control LED based on state."""
    print("[SYSTEM] LED Status Loop Started")
    
    while True:
        if current_state == IDLE:
            # Gentle Heartbeat (1s on, 1s off)
            led.toggle()
            await asyncio.sleep(1.0)
            
        elif current_state == SCANNING:
            # Rapid Activity (100ms)
            led.toggle()
            await asyncio.sleep(0.1)
            
        elif current_state == CONNECTING:
            # "Thinking" pace (300ms)
            led.toggle()
            await asyncio.sleep(0.3)
            
        elif current_state == ERROR:
            # Solid On (Warning)
            led.value(1)
            await asyncio.sleep(0.5) # Check again in 0.5s