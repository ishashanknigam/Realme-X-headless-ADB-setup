#!/system/bin/sh
# Magisk boot script to disable ADB RSA fingerprint security prompt
# This allows any device to connect via ADB without clicking "Allow" on the screen.

resetprop ro.adb.secure 0
