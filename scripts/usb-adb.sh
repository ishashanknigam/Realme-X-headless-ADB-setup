#!/system/bin/sh

sleep 5

echo "usb-adb service.d executed at $(date)" > /data/local/tmp/usb-adb-ran.txt

resetprop persist.sys.usb.config mtp,adb
resetprop persist.vendor.usb.config mtp,adb

setprop sys.usb.config mtp,adb

settings put global adb_enabled 1
