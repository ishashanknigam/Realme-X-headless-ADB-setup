# Realme X RMX1901 — Headless ADB Recovery

A complete backup and recovery procedure for running a **Realme X (RMX1901)** as a headless Android device when the display/touchscreen is not usable.

The goal is to boot normal Android and automatically expose:

- MTP
- ADB
- Remote control through `adb shell`
- Remote screen control through `scrcpy`

---

# 1. Device Information

| Item | Value |
|---|---|
| Device | Realme X |
| Model | RMX1901 |
| SoC | Qualcomm SDM710 / Snapdragon 710 |
| Android | 10 |
| ColorOS | 7.2 |
| Build | RMX1901_11_C.11 |
| Bootloader | Unlocked |
| Verified Boot | `orange` |
| Magisk | 24.2 |
| Purpose | Headless ADB / scrcpy |

The display and touchscreen are not usable.

The phone is controlled from a Linux PC through USB ADB.

---

# 2. Verified Working State

The following state has been successfully tested after a normal Android reboot.

## ADB

```text
adb devices

8546e62c    device
```

## Root

```text
adb shell su -c id
```

Expected:

```text
uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
```

## Current runtime USB configuration

Verified after normal reboot:

```text
persist.sys.usb.config=mtp,adb
persist.vendor.usb.config=<empty>
sys.usb.config=mtp,adb
adb_enabled=1
```

ADB works even though the phone has no usable touchscreen.

USB device:

```text
22d9:2765 OPPO Electronics Corp. Oppo N1
```

---

# 3. Repository Structure

```text
realme-x-headless-adb/
│
├── backup/
│   ├── adb_keys
│   ├── persistent_properties
│   └── settings_global.xml
│
├── info/
│   ├── device-state.txt
│   └── working-config.txt
│
├── scripts/
│   ├── patch_usb_vendor.py
│   └── usb-adb.sh
│
├── README.md
└── SHA256SUMS
```

---

# 4. What Each Backup File Does

## `backup/persistent_properties`

Backup of:

```text
/data/property/persistent_properties
```

This is Android's persistent-property database.

It contains the USB-related persistent configuration used to enable ADB.

The saved backup contains:

```text
persist.sys.usb.config=mtp,adb
persist.vendor.usb.config=mtp,adb
```

Important:

The saved file is a **snapshot**. It is not necessarily identical to the values returned by `getprop` while Android is currently running.

---

## `backup/settings_global.xml`

Backup of:

```text
/data/system/users/0/settings_global.xml
```

The important setting is:

```xml
name="adb_enabled" value="1"
```

This tells Android that ADB is enabled.

---

## `backup/adb_keys`

Backup of:

```text
/data/misc/adb/adb_keys
```

This contains the **ADB host public key** authorized by the phone.

This allows the PC to connect without requiring authorization through the broken touchscreen.

### Security warning

Never put the PC's private ADB key in this repository.

Do NOT upload:

```text
~/.android/adbkey
```

Only the phone-side `adb_keys` public-key file is backed up here.

---

# 5. Important: Magisk Service Script

The repository also contains:

```text
scripts/usb-adb.sh
```

which is installed on the phone as:

```text
/data/adb/service.d/usb-adb.sh
```

Current script:

```sh
#!/system/bin/sh

sleep 5

resetprop persist.sys.usb.config mtp,adb
resetprop persist.vendor.usb.config mtp,adb

setprop sys.usb.config mtp,adb

settings put global adb_enabled 1
```

## Current status

Magisk 24.2 successfully discovers the script during boot:

```text
* late_start service mode running
* Running service.d scripts
service.d: exec [usb-adb.sh]
```

However, the same boot log reported:

```text
execve /sbin/.magisk/busybox/busybox failed with 2: No such file or directory
```

Therefore:

**Do not rely on `usb-adb.sh` as the primary recovery mechanism.**

The actual ADB configuration has independently been verified to survive a normal reboot.

The script is retained in this repository as an additional recovery/experimental component.

---

# 6. Before Doing Anything

Do NOT factory-reset or format `/data` unless necessary.

If Android is currently working:

```bash
adb devices
```

should show:

```text
8546e62c    device
```

Check:

```bash
adb shell '
echo "persist.sys.usb.config=$(getprop persist.sys.usb.config)"
echo "persist.vendor.usb.config=$(getprop persist.vendor.usb.config)"
echo "sys.usb.config=$(getprop sys.usb.config)"
echo "adb_enabled=$(settings get global adb_enabled)"
'
```

Expected:

```text
persist.sys.usb.config=mtp,adb
persist.vendor.usb.config=
sys.usb.config=mtp,adb
adb_enabled=1
```

If this works, no recovery is required.

---

# 7. If ADB Is Still Working but You Only Want a Backup

Pull the current working files using root:

```bash
adb exec-out su -c 'cat /data/property/persistent_properties' \
    > backup/persistent_properties

adb exec-out su -c 'cat /data/system/users/0/settings_global.xml' \
    > backup/settings_global.xml

adb exec-out su -c 'cat /data/misc/adb/adb_keys' \
    > backup/adb_keys

adb exec-out su -c 'cat /data/adb/service.d/usb-adb.sh' \
    > scripts/usb-adb.sh
```

Check:

```bash
ls -lh backup/ scripts/
```

---

# 8. Recovery After `/data` Wipe

A factory reset or TWRP data format removes:

```text
/data/property/persistent_properties
/data/system/users/0/settings_global.xml
/data/misc/adb/adb_keys
/data/adb/
```

Therefore normal Android may boot with:

```text
persist.sys.usb.config=midi
adb_enabled=0
```

and ADB will no longer be available.

The recovery method is:

```text
TWRP
  ↓
restore USB configuration
  ↓
restore adb_enabled
  ↓
restore ADB public key
  ↓
reboot Android
  ↓
ADB available again
```

---

# 9. Enter TWRP

Because the display is not usable, use the known working button sequence.

## Enter fastboot

Power off the phone.

Use:

```text
Volume Down + Power
```

The phone should enter fastboot.

## From fastboot to TWRP

Use:

```text
Press Volume Down once
then Power
```

TWRP should boot.

---

# 10. Verify TWRP ADB

From the PC:

```bash
adb devices
```

Expected:

```text
8546e62c    recovery
```

Check root:

```bash
adb shell id
```

Expected:

```text
uid=0(root)
```

If `/data` is not mounted, mount it from TWRP before continuing.

---

# 11. Backup the Fresh `/data` Files Before Modifying Them

This is strongly recommended.

Create a recovery working directory:

```bash
mkdir -p ~/Documents/realme-x-headless-adb/recovery-work
cd ~/Documents/realme-x-headless-adb/recovery-work
```

Pull the current persistent-property file:

```bash
adb pull /data/property/persistent_properties \
    persistent_properties-current.bin
```

Pull the current settings file:

```bash
adb pull /data/system/users/0/settings_global.xml \
    settings_global-current.xml
```

If these files are fresh after a factory reset, keep them as untouched originals.

---

# 12. Restore / Patch USB Persistent Properties

## Recommended method

Use the included:

```text
scripts/patch_usb_vendor.py
```

The script was created specifically for the Realme X persistent-property file.

Copy the current file to the filename expected by the script:

```bash
cp persistent_properties-current.bin \
   persistent_properties-current.bin
```

Run:

```bash
python3 ../scripts/patch_usb_vendor.py
```

The patched output should be:

```text
persistent_properties-vendor-adb.bin
```

Verify the resulting file:

```bash
strings -n 1 persistent_properties-vendor-adb.bin |
grep -E -A2 -B2 'persist\.(vendor|sys)\.usb\.config'
```

The patched file should contain:

```text
persist.sys.usb.config
mtp,adb
```

and:

```text
persist.vendor.usb.config
mtp,adb
```

Do not modify the original backup.

---

# 13. Install the Patched Persistent Properties

Push the patched file to temporary storage:

```bash
adb push persistent_properties-vendor-adb.bin \
    /data/local/tmp/persistent_properties
```

Copy it as root:

```bash
adb shell "
su -c '
cp /data/local/tmp/persistent_properties \
   /data/property/persistent_properties

chown root:root \
   /data/property/persistent_properties

chmod 600 \
   /data/property/persistent_properties

chcon u:object_r:property_data_file:s0 \
   /data/property/persistent_properties

rm -f /data/local/tmp/persistent_properties
'
"
```

---

# 14. Enable `adb_enabled`

Do not blindly replace the entire `settings_global.xml` after a factory reset if a fresh file is available.

Instead:

1. Pull the fresh file.
2. Make a backup.
3. Change only `adb_enabled` from `0` to `1`.
4. Push it back.

Create a backup:

```bash
cp settings_global-current.xml \
   settings_global-before-adb.patch.xml
```

Edit:

```bash
nano settings_global-current.xml
```

Find:

```xml
name="adb_enabled" value="0"
```

Change only:

```xml
name="adb_enabled" value="1"
```

Verify:

```bash
grep -n 'name="adb_enabled"' \
    settings_global-current.xml
```

Expected:

```xml
name="adb_enabled" value="1"
```

Push:

```bash
adb push settings_global-current.xml \
    /data/local/tmp/settings_global.xml
```

Install:

```bash
adb shell "
su -c '
cp /data/local/tmp/settings_global.xml \
   /data/system/users/0/settings_global.xml

chown system:system \
   /data/system/users/0/settings_global.xml

chmod 600 \
   /data/system/users/0/settings_global.xml

chcon u:object_r:system_data_file:s0 \
   /data/system/users/0/settings_global.xml

rm -f /data/local/tmp/settings_global.xml
'
"
```

---

# 15. Restore the Authorized ADB Public Key

Create the ADB directory if necessary:

```bash
adb shell "
su -c '
mkdir -p /data/misc/adb

chown system:shell /data/misc/adb
chmod 750 /data/misc/adb
'
"
```

Push the backed-up public key:

```bash
adb push ../backup/adb_keys \
    /data/local/tmp/adb_keys
```

Install it:

```bash
adb shell "
su -c '
cp /data/local/tmp/adb_keys \
   /data/misc/adb/adb_keys

chown system:shell \
   /data/misc/adb/adb_keys

chmod 640 \
   /data/misc/adb/adb_keys

chcon u:object_r:adb_keys_file:s0 \
   /data/misc/adb/adb_keys

rm -f /data/local/tmp/adb_keys
'
"
```

---

# 16. Verify Everything Before Reboot

## Persistent USB properties

```bash
adb shell '
strings -n 1 /data/property/persistent_properties |
grep -E -A2 -B2 "persist\.(vendor|sys)\.usb\.config"
'
```

Look for:

```text
persist.sys.usb.config
mtp,adb
```

and:

```text
persist.vendor.usb.config
mtp,adb
```

## ADB setting

```bash
adb shell '
grep -n "name=\"adb_enabled\"" \
/data/system/users/0/settings_global.xml
'
```

Expected:

```text
name="adb_enabled" value="1"
```

## ADB public key

```bash
adb shell '
ls -lZ /data/misc/adb/adb_keys
'
```

Expected:

```text
-rw-r----- 1 system shell ... u:object_r:adb_keys_file:s0
```

## Persistent-property permissions

```bash
adb shell '
ls -lZ /data/property/persistent_properties
'
```

Expected:

```text
-rw------- 1 root root ... u:object_r:property_data_file:s0
```

## Settings permissions

```bash
adb shell '
ls -lZ /data/system/users/0/settings_global.xml
'
```

Expected:

```text
-rw------- 1 system system ... u:object_r:system_data_file:s0
```

---

# 17. Reboot Into Android

Only after all files have been verified:

```bash
adb reboot
```

Wait for Android to completely boot.

---

# 18. Verify ADB After Reboot

Run:

```bash
adb devices
```

Expected:

```text
List of devices attached
8546e62c    device
```

Then:

```bash
adb shell '
echo "persist.sys.usb.config=$(getprop persist.sys.usb.config)"
echo "persist.vendor.usb.config=$(getprop persist.vendor.usb.config)"
echo "sys.usb.config=$(getprop sys.usb.config)"
echo "adb_enabled=$(settings get global adb_enabled)"
'
```

Expected:

```text
persist.sys.usb.config=mtp,adb
persist.vendor.usb.config=
sys.usb.config=mtp,adb
adb_enabled=1
```

---

# 19. Verify Root

```bash
adb shell su -c id
```

Expected:

```text
uid=0(root) gid=0(root) groups=0(root) context=u:r:magisk:s0
```

---

# 20. Verify USB From Linux

```bash
lsusb
```

The working phone was detected as:

```text
22d9:2765 OPPO Electronics Corp. Oppo N1
```

---

# 21. Test scrcpy

Once ADB is working:

```bash
scrcpy
```

ADB shell:

```bash
adb shell
```

Install an APK:

```bash
adb install app.apk
```

Copy a file to the phone:

```bash
adb push file /sdcard/
```

Copy a file from the phone:

```bash
adb pull /sdcard/file
```

Reboot:

```bash
adb reboot
```

---

# 22. Full Snapshot Restore

The repository also contains complete snapshots:

```text
backup/persistent_properties
backup/settings_global.xml
backup/adb_keys
```

These should be treated as **device/build-specific snapshots**.

Use them only when recovering the same:

```text
RMX1901
Android 10
RMX1901_11_C.11
```

The recommended recovery method after a data wipe is the **surgical patching method above**, because it changes only the settings required for ADB instead of replacing the entire fresh Android settings database.

---

# 23. Optional: Restore the Magisk Service Script

The script is stored at:

```text
scripts/usb-adb.sh
```

To restore it:

```bash
adb push ../scripts/usb-adb.sh \
    /data/local/tmp/usb-adb.sh
```

Then:

```bash
adb shell "
su -c '
mkdir -p /data/adb/service.d

cp /data/local/tmp/usb-adb.sh \
   /data/adb/service.d/usb-adb.sh

chown 0:0 \
   /data/adb/service.d/usb-adb.sh

chmod 755 \
   /data/adb/service.d/usb-adb.sh

rm -f /data/local/tmp/usb-adb.sh
'
"
```

Verify:

```bash
adb shell "
su -c '
ls -lZ /data/adb/service.d/usb-adb.sh
'
"
```

Expected:

```text
-rwxr-xr-x 1 root root ... usb-adb.sh
```

## Important

The current Magisk 24.2 installation reported:

```text
service.d: exec [usb-adb.sh]
execve /sbin/.magisk/busybox/busybox failed with 2
```

Therefore this script should be considered **optional** until the Magisk BusyBox issue is resolved.

---

# 24. Verify Repository Integrity

From the repository root:

```bash
cd ~/Documents/realme-x-headless-adb
```

Run:

```bash
sha256sum -c SHA256SUMS
```

Expected:

```text
backup/adb_keys: OK
backup/persistent_properties: OK
backup/settings_global.xml: OK
scripts/patch_usb_vendor.py: OK
scripts/usb-adb.sh: OK
```

---

# 25. Check for Private Keys Before Git Push

Run:

```bash
find . -type f \( \
    -name 'adbkey' -o \
    -name 'adbkey.*' -o \
    -name '*.pem' -o \
    -name '*.p12' -o \
    -name '*.pfx' -o \
    -name '*.key' -o \
    -name 'id_rsa' -o \
    -name 'id_ed25519' \
\) -print
```

Expected:

```text
(no output)
```

Never commit:

```text
~/.android/adbkey
```

---

# 26. Git Setup

From the repository root:

```bash
cd ~/Documents/realme-x-headless-adb
```

Initialize:

```bash
git init
```

Add files:

```bash
git add .
```

Review:

```bash
git status
```

Create the first commit:

```bash
git commit -m "Backup working Realme X headless ADB setup"
```

Set the branch:

```bash
git branch -M main
```

Add the private GitHub repository:

```bash
git remote add origin <YOUR_PRIVATE_GITHUB_REPOSITORY>
```

Push:

```bash
git push -u origin main
```

---

# 27. Recovery Decision Tree

## ADB works

Run:

```bash
adb devices
```

If:

```text
8546e62c    device
```

No recovery is required.

---

## Android boots but ADB does not work

Boot TWRP and restore:

```text
persistent_properties
adb_enabled
adb_keys
```

Then reboot Android.

---

## `/data` was formatted

Boot TWRP.

Use the **fresh-file patching procedure**:

```text
1. Pull fresh persistent_properties
2. Patch USB configuration
3. Set adb_enabled=1
4. Restore adb_keys
5. Verify permissions/context
6. Reboot
7. Verify adb
```

---

## Magisk root is missing

The files in this repository do not contain the complete Magisk installation.

A compatible Magisk package must be kept separately.

After restoring/reinstalling Magisk, the optional:

```text
/data/adb/service.d/usb-adb.sh
```

script can be restored.

---

# 28. Important Warnings

## Do not factory-reset `/data`

A data wipe removes the configuration required for headless ADB.

---

## Do not blindly flash random firmware

This backup is specific to:

```text
Realme X RMX1901
Android 10
Build RMX1901_11_C.11
```

Verify firmware compatibility before restoring system/data configuration files.

---

## Do not restore the entire settings database unnecessarily

Prefer changing only:

```text
adb_enabled=1
```

on a fresh `settings_global.xml`.

---

## Do not commit private ADB keys

Never upload:

```text
~/.android/adbkey
```

to GitHub.

---

## Keep an offline copy

Keep at least one copy outside GitHub:

```text
USB drive
External HDD
Another PC
```

---

# 29. Known Working Recovery Files

| File | Purpose |
|---|---|
| `backup/persistent_properties` | Persistent Android USB configuration snapshot |
| `backup/settings_global.xml` | Known-good settings snapshot |
| `backup/adb_keys` | Authorized ADB public key |
| `scripts/patch_usb_vendor.py` | Patches persistent USB properties |
| `scripts/usb-adb.sh` | Optional Magisk boot-time ADB script |
| `info/device-state.txt` | Device state captured during working setup |
| `info/working-config.txt` | Human-readable working configuration |
| `SHA256SUMS` | File integrity verification |

---

# 30. Final Known-Good State

The configuration was successfully verified after a normal reboot:

```text
Device: Realme X RMX1901
Android: 10
Build: RMX1901_11_C.11

Bootloader:
Unlocked

AVB:
orange

ADB:
Working

Root:
Working

USB:
MTP + ADB

persist.sys.usb.config:
mtp,adb

persist.vendor.usb.config:
<empty at runtime>

sys.usb.config:
mtp,adb

adb_enabled:
1

Magisk:
24.2
```

The phone can therefore be operated as a headless Android device through USB ADB without requiring a functional touchscreen.
