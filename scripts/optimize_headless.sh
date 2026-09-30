#!/bin/bash

DEVICE="-s 8546e62c"

echo "Applying headless server optimizations..."

# 1. Kill all UI animations to save GPU/CPU cycles
echo "Disabling window animations..."
adb $DEVICE shell "su -c 'settings put global window_animation_scale 0.0'"
adb $DEVICE shell "su -c 'settings put global transition_animation_scale 0.0'"
adb $DEVICE shell "su -c 'settings put global animator_duration_scale 0.0'"

# 2. Disable system updates and OTA services
echo "Disabling OTA auto-updates..."
adb $DEVICE shell "su -c 'settings put global ota_disable_automatic_update 1'"
adb $DEVICE shell "su -c 'pm disable com.oppo.ota'" 2>/dev/null
adb $DEVICE shell "su -c 'pm disable com.nearme.romupdate'" 2>/dev/null

# 3. Network and Power management
echo "Configuring network and power for 24/7 uptime..."
# Keep Wi-Fi on during sleep (2 = always)
adb $DEVICE shell "su -c 'settings put global wifi_sleep_policy 2'"
# Prevent device from sleeping while plugged in (7 = AC | USB | Wireless)
adb $DEVICE shell "su -c 'settings put global stay_on_while_plugged_in 7'"

# 4. Hardware Power Optimizations (Screen, Bluetooth, Location)
echo "Applying hardware power optimizations..."
# Minimize screen timeout (15 seconds) and brightness to 0
adb $DEVICE shell "su -c 'settings put system screen_off_timeout 15000'"
adb $DEVICE shell "su -c 'settings put system screen_brightness 0'"
adb $DEVICE shell "su -c 'settings put system screen_brightness_mode 0'"
# Turn off Bluetooth
adb $DEVICE shell "su -c 'settings put global bluetooth_on 0'"
# Turn off Location Services
adb $DEVICE shell "su -c 'settings put secure location_mode 0'"
# Disable background scanning for Wi-Fi and Bluetooth
adb $DEVICE shell "su -c 'settings put global wifi_scan_always_enabled 0'"
adb $DEVICE shell "su -c 'settings put global ble_scan_always_enabled 0'"

echo "Headless optimizations applied successfully!"
