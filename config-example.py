# config.py - TechnoShed BLE Prober Settings - EXAMPLE FILE

# Wi-Fi Access Point Settings (The network you join)
AP_SSID = "PICO_PROBER"
AP_PASS = "technoshed" # Must be at least 8 chars

# Scanning Settings
SCAN_DURATION_MS = 10000  # How long a single scan run lasts
RSSI_THRESHOLD = -90     # Ignore anything weaker than this
FILTER_NAMED_ONLY = True # True = Only show devices with a Local Name

# File Storage
LOG_FILE = "probe_log.txt"

#Known Networks for SYNC
KNOWN_NETWORKS = [
    {"ssid": "WiFi-SSID", "pass": "WiFiPASS"},			# Home Network
    {"ssid": "WiFi2", "pass": "WIFI2-PASS"},			# 2nd Network
    {"ssid": "LastWiFi", "pass": "LastWiFi-PASS"},		# 3rd Network
]
