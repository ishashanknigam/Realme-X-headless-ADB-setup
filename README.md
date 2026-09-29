# Realme X RMX1901 — Headless ADB Recovery

Recovery notes for using a **Realme X RMX1901** with a dead display/touchscreen as a headless Android ADB device.

## Known-good configuration

Target firmware:

- Device: Realme X RMX1901
- Android: 10
- ColorOS: 7.2
- Build: `RMX1901_11_C.11`
- Bootloader: unlocked
- TWRP: `3.6.2_12.1_nicky_RC3`
- Magisk: 24.2

The tested working USB state is:

```text
persist.sys.allcommode=true
persist.sys.usb.config=mtp,adb
sys.usb.config=mtp,adb
sys.usb.state=mtp,adb
adb_enabled=1
```

The phone was also tested across a physical USB disconnect/reconnect and remained visible to ADB as:

```text
8546e62c    device
```

The Linux USB device was:

```text
22d9:2765 OPPO Electronics Corp. Oppo N1
```

## Why `persist.sys.allcommode=true` matters

This ROM's decompiled `UsbDeviceManager` uses a boot-mode-specific persistent USB function when `ro.bootmode=reboot` unless `persist.sys.allcommode=true`. With `allcommode=true`, the code uses `persist.sys.usb.config` instead of `persist.sys.usb.reboot.func`.

The OPPO helper also checks `persist.sys.allcommode` in its ADB-disable decision. On the tested phone, changing `allcommode` to `true` prevented the late boot transition to MIDI and allowed `mtp,adb` to remain active.

## Important safety rules

- Do not wipe `/data` unless you intentionally want a factory reset.
- Keep an untouched copy of the original persistent-properties file.
- Never upload `~/.android/adbkey` (the private key) to GitHub.
- `backup/adb_keys` is the public/authorized key file used by the phone and is safe only for a private recovery repository.
- Do not flash the empty standalone `odm` partition just because `/dev/block/sda12` appears unused.
- EDL/Sahara worked on this device, but the tested public Firehose loader failed signature verification, so EDL is not part of this recovery procedure.

## 1. Enter TWRP

Hardware sequence already verified on this device:

1. `Vol Down + Power` → fastboot.
2. In fastboot, press `Vol Down` once.
3. Press `Power` → TWRP.

Confirm TWRP ADB:

```fish
adb devices
```

Expected:

```text
8546e62c    recovery
```

Confirm root:

```fish
adb shell id
```

Expected to include:

```text
uid=0(root)
```

Make sure `/data` is mounted in TWRP.

## 2. Prepare a fresh recovery workspace

On the Arch/Kitty host:

```fish
cd ~/Documents/realme-x-headless-adb
mkdir -p recovery-work
```

Pull fresh copies from the phone **before modifying them**:

```fish
adb pull /data/property/persistent_properties \
    recovery-work/persistent_properties-current.bin
```

```fish
adb pull /data/system/users/0/settings_global.xml \
    recovery-work/settings_global-current.xml
```

Keep these fresh files separate from the repository's original backups.

## 3. Patch the persistent USB properties

Copy the fresh property store to a working file:

```fish
cp recovery-work/persistent_properties-current.bin \
    recovery-work/persistent_properties-working.bin
```

Run the canonical patcher:

```fish
python3 scripts/patch_headless.py \
    recovery-work/persistent_properties-working.bin \
    recovery-work/persistent_properties-headless.bin
```

The patcher sets:

```text
persist.sys.usb.config=mtp,adb
persist.vendor.usb.config=mtp,adb
persist.sys.allcommode=true
```

It updates existing entries and creates `persist.vendor.usb.config` if the fresh store does not already contain it.

Verify the binary contains the target values:

```fish
grep -aobE \
    'persist.sys.allcommode|persist.sys.usb.config|persist.vendor.usb.config|mtp,adb|midi' \
    recovery-work/persistent_properties-headless.bin
```

Do not assume `strings` alone proves a name/value pair; use the patcher output and the binary as a whole.

## 4. Install the patched persistent-properties file

Push it:

```fish
adb push recovery-work/persistent_properties-headless.bin \
    /data/local/tmp/persistent_properties.new
```

Because TWRP ADB is root, no `su` command is needed:

```fish
adb shell 'cat /data/local/tmp/persistent_properties.new > /data/property/persistent_properties'
```

Restore the expected metadata explicitly:

```fish
adb shell 'chown root:root /data/property/persistent_properties; chmod 600 /data/property/persistent_properties; chcon u:object_r:property_data_file:s0 /data/property/persistent_properties'
```

Verify:

```fish
adb shell 'ls -lZ /data/property/persistent_properties'
```

Expected:

```text
-rw------- 1 root root ... u:object_r:property_data_file:s0
```

## 5. Enable ADB in settings

Make a safety copy:

```fish
cp recovery-work/settings_global-current.xml \
    recovery-work/settings_global-before-adb.patch.xml
```

Edit:

```fish
nano recovery-work/settings_global-current.xml
```

Change **only** the `adb_enabled` value:

```xml
name="adb_enabled" value="0"
```

to:

```xml
name="adb_enabled" value="1"
```

Verify:

```fish
grep -n 'name="adb_enabled"' recovery-work/settings_global-current.xml
```

Push:

```fish
adb push recovery-work/settings_global-current.xml \
    /data/local/tmp/settings_global.xml
```

Install and restore metadata:

```fish
adb shell 'cat /data/local/tmp/settings_global.xml > /data/system/users/0/settings_global.xml; chown system:system /data/system/users/0/settings_global.xml; chmod 600 /data/system/users/0/settings_global.xml; chcon u:object_r:system_data_file:s0 /data/system/users/0/settings_global.xml'
```

## 6. Restore the authorized ADB public key

Create the directory if needed:

```fish
adb shell 'mkdir -p /data/misc/adb; chown system:shell /data/misc/adb; chmod 750 /data/misc/adb'
```

Push the saved public key:

```fish
adb push backup/adb_keys /data/local/tmp/adb_keys
```

Install it:

```fish
adb shell 'cat /data/local/tmp/adb_keys > /data/misc/adb/adb_keys; chown system:shell /data/misc/adb/adb_keys; chmod 640 /data/misc/adb/adb_keys; chcon u:object_r:adb_keys_file:s0 /data/misc/adb/adb_keys; rm -f /data/local/tmp/adb_keys'
```

Verify:

```fish
adb shell 'ls -lZ /data/misc/adb/adb_keys'
```

## 7. Verify before rebooting

Check the property file metadata:

```fish
adb shell 'ls -lZ /data/property/persistent_properties'
```

Check the persistent values currently visible in the TWRP property service:

```fish
adb shell 'getprop persist.sys.allcommode; getprop persist.sys.usb.config; getprop persist.vendor.usb.config'
```

The recovery environment may report different temporary `sys.usb.*` values because TWRP itself is running in `recovery` mode. The persistent file is the important part for the normal `reboot` test.

## 8. Reboot and verify normal Android

```fish
adb reboot
```

Wait for Android to boot, then:

```fish
adb devices
```

Expected:

```text
List of devices attached
8546e62c    device
```

Verify the key runtime values:

```fish
adb shell 'echo "bootmode=$(getprop ro.bootmode)"; echo "allcommode=$(getprop persist.sys.allcommode)"; echo "persist.usb=$(getprop persist.sys.usb.config)"; echo "vendor.usb=$(getprop persist.vendor.usb.config)"; echo "sys.usb.config=$(getprop sys.usb.config)"; echo "sys.usb.state=$(getprop sys.usb.state)"; echo "adb=$(settings get global adb_enabled)"'
```

Expected working state includes:

```text
bootmode=reboot
allcommode=true
persist.usb=mtp,adb
sys.usb.config=mtp,adb
sys.usb.state=mtp,adb
adb=1
```

Check the Linux USB identity from the host:

```fish
lsusb | grep -iE '22d9|18d1|2765|4ee8'
```

Expected working device:

```text
22d9:2765
```

## 9. Verify physical USB reconnect

After the reboot test succeeds:

1. Disconnect the USB cable.
2. Wait 5–10 seconds.
3. Reconnect it.

Then:

```fish
lsusb | grep -iE '22d9|18d1|2765|4ee8'
```

```fish
adb devices
```

Expected again:

```text
22d9:2765
```

and:

```text
8546e62c    device
```

This physical reconnect test was successful on the known-good configuration.

## 10. Known-good backup

Once the phone is confirmed working, save the exact live persistent-properties file:

```fish
cd ~/Documents/realme-x-headless-adb

adb exec-out 'cat /data/property/persistent_properties' \
    > backup/persistent_properties-working
```

Do **not** overwrite `backup/persistent_properties`; keep that as the original clean backup.

Verify the known-good file:

```fish
grep -aobE \
    'persist.sys.allcommode|persist.sys.usb.config|persist.vendor.usb.config|persist.sys.usb.reboot.func|mtp,adb|midi' \
    backup/persistent_properties-working
```

For this known-good configuration, the relevant values should include:

```text
persist.sys.allcommode=true
persist.sys.usb.config=mtp,adb
persist.vendor.usb.config=mtp,adb
```

`persist.sys.usb.reboot.func=midi` may still exist. That is expected; `allcommode=true` makes the reboot path use `persist.sys.usb.config` instead.

## 11. Update SHA256SUMS

After creating the known-good backup:

```fish
sha256sum \
    backup/persistent_properties-working \
    >> SHA256SUMS
```

For the repository scripts, also regenerate their hashes if you changed them:

```fish
sha256sum \
    scripts/patch_headless.py \
    scripts/usb-adb.sh \
    > /tmp/realme-x-headless-adb-script-checksums
```

Merge/update those entries in `SHA256SUMS` rather than keeping stale hashes.

## 12. Optional Magisk service script

`/data/adb/service.d/usb-adb.sh` was observed by Magisk 24.2, but the same setup also produced a Magisk BusyBox execution error. Therefore the repository does **not** depend on that script for the primary recovery path.

The persistent `allcommode=true` + `persist.sys.usb.config=mtp,adb` configuration is the tested solution.

## 13. Cleaning up old experiment files

After the final known-good backup is verified, remove only the temporary USB-property experiment files and boot logs. Keep the original and known-good backups.

```fish
rm -f \
    info/persistent_properties-before-reboot-func-test \
    info/persistent_properties-after-reboot-func-test \
    info/persistent_properties-current \
    info/persistent_properties-before-reboot-func-patch \
    info/persistent_properties-reboot-func-mtp-adb \
    info/persistent_properties-after-reboot-func-patch \
    info/persistent_properties-after-failed-boot \
    info/persistent_properties-before-allcommode-test \
    info/persistent_properties-allcommode-test-installed
```

Remove old test-only patchers after the canonical patcher is installed:

```fish
rm -f \
    scripts/patch_reboot_func.py \
    scripts/patch_allcommode.py
```

The old `boot-capture` logs were diagnostic evidence and are no longer required for recovery:

```fish
rm -rf info/boot-capture
```

Do not delete the primary backups:

```text
backup/adb_keys
backup/persistent_properties
backup/persistent_properties-working
backup/settings_global.xml
```

## 14. Emergency recovery

If Android starts but ADB disappears:

1. Do not format `/data` again.
2. Re-enter TWRP.
3. Confirm `adb devices` shows `8546e62c    recovery`.
4. Re-read `/data/property/persistent_properties` and compare it with `backup/persistent_properties-working`.
5. Reinstall the known-good persistent-properties file if necessary.

```fish
adb push backup/persistent_properties-working \
    /data/local/tmp/persistent_properties-working

adb shell 'cat /data/local/tmp/persistent_properties-working > /data/property/persistent_properties'

adb shell 'chown root:root /data/property/persistent_properties; chmod 600 /data/property/persistent_properties; chcon u:object_r:property_data_file:s0 /data/property/persistent_properties'
```

If `/data` is not mounted in TWRP, mount it first.

## 15. GitHub privacy

Keep this repository **private**.

Safe to keep:

```text
backup/adb_keys
backup/persistent_properties
backup/persistent_properties-working
backup/settings_global.xml
```

Never commit:

```text
~/.android/adbkey
~/.android/adbkey*private*
```

The host ADB private key must remain on the host only.

## 16. Permanent Wireless ADB

After USB ADB is working, enable persistent TCP ADB:

```fish
adb shell su -c 'setprop persist.adb.tcp.port 5555'
adb shell su -c 'setprop service.adb.tcp.port 5555'
adb shell su -c 'stop adbd; start adbd'
```

Reconnect using the phone's Wi-Fi IP:

```fish
adb connect PHONE_IP:5555
```

Verify:
```fish
adb -s PHONE_IP:5555 shell 'getprop persist.adb.tcp.port'
adb -s PHONE_IP:5555 shell 'toybox netstat -lnt | grep 5555'
```

Expected:
```text
5555
tcp6 ... :::5555 ... LISTEN
```

The configuration was tested successfully across a complete Android reboot. The phone's DHCP address may change, so use the current Wi-Fi IP when connecting.