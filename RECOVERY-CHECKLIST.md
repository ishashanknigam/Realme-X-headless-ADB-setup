# Realme X RMX1901 — Headless ADB Recovery Checklist

> Quick recovery checklist for a `/data` wipe / factory reset.
>
> Target device: **Realme X RMX1901 — Android 10 — Build RMX1901_11_C.11**
>
> This checklist assumes:
> - TWRP is already installed and boots.
> - TWRP ADB is root.
> - `/data` is mounted.
> - This repository is available on the PC.
>
> For explanations and the full recovery procedure, see `README.md`.

---

## 0. Set the repository path

Run on the PC:

```bash
cd ~/Documents/realme-x-headless-adb
```

Check the repository:

```bash
ls backup scripts
```

Expected:

```text
backup:
adb_keys
persistent_properties
settings_global.xml

scripts:
patch_usb_vendor.py
usb-adb.sh
```

---

## 1. Confirm TWRP ADB

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

If `/data` is not mounted, mount `/data` in TWRP before continuing.

---

## 2. Keep untouched copies of the fresh `/data` files

Create a temporary recovery directory:

```bash
mkdir -p recovery-work
```

Pull the fresh persistent-properties file:

```bash
adb pull /data/property/persistent_properties \
    recovery-work/persistent_properties-current.bin
```

Pull the fresh settings file:

```bash
adb pull /data/system/users/0/settings_global.xml \
    recovery-work/settings_global-current.xml
```

Do **not** overwrite these fresh files with the old backups.

---

## 3. Patch the persistent USB configuration

The patcher works on the fresh persistent-properties file.

From the repository root:

```bash
cp recovery-work/persistent_properties-current.bin \
    persistent_properties-current.bin
```

Run the repository patcher:

```bash
python3 scripts/patch_usb_vendor.py
```

Verify the patched file:

```bash
strings -n 1 persistent_properties-vendor-adb.bin |
grep -E -A2 -B2 'persist\.(vendor|sys)\.usb\.config'
```

Expected entries include:

```text
persist.sys.usb.config
mtp,adb
```

and:

```text
persist.vendor.usb.config
mtp,adb
```

---

## 4. Install the patched persistent-properties file

```bash
adb push persistent_properties-vendor-adb.bin \
    /data/local/tmp/persistent_properties
```

```bash
adb shell "su -c '
cp /data/local/tmp/persistent_properties \
   /data/property/persistent_properties

chown root:root \
   /data/property/persistent_properties

chmod 600 \
   /data/property/persistent_properties

chcon u:object_r:property_data_file:s0 \
   /data/property/persistent_properties

rm -f /data/local/tmp/persistent_properties
'"
```

---

## 5. Enable Android ADB in the fresh settings file

Create a backup of the fresh file:

```bash
cp recovery-work/settings_global-current.xml \
   recovery-work/settings_global-before-adb.patch.xml
```

Edit it:

```bash
nano recovery-work/settings_global-current.xml
```

Change only:

```xml
name="adb_enabled" value="0"
```

to:

```xml
name="adb_enabled" value="1"
```

Verify:

```bash
grep -n 'name="adb_enabled"' \
    recovery-work/settings_global-current.xml
```

Expected:

```text
name="adb_enabled" value="1"
```

Push it:

```bash
adb push recovery-work/settings_global-current.xml \
    /data/local/tmp/settings_global.xml
```

Install it:

```bash
adb shell "su -c '
cp /data/local/tmp/settings_global.xml \
   /data/system/users/0/settings_global.xml

chown system:system \
   /data/system/users/0/settings_global.xml

chmod 600 \
   /data/system/users/0/settings_global.xml

chcon u:object_r:system_data_file:s0 \
   /data/system/users/0/settings_global.xml

rm -f /data/local/tmp/settings_global.xml
'"
```

---

## 6. Restore the authorized ADB public key

Create the directory:

```bash
adb shell "su -c '
mkdir -p /data/misc/adb
chown system:shell /data/misc/adb
chmod 750 /data/misc/adb
'"
```

Push the saved public key:

```bash
adb push backup/adb_keys \
    /data/local/tmp/adb_keys
```

Install it:

```bash
adb shell "su -c '
cp /data/local/tmp/adb_keys \
   /data/misc/adb/adb_keys

chown system:shell \
   /data/misc/adb/adb_keys

chmod 640 \
   /data/misc/adb/adb_keys

chcon u:object_r:adb_keys_file:s0 \
   /data/misc/adb/adb_keys

rm -f /data/local/tmp/adb_keys
'"
```

---

## 7. Verify before reboot

### Persistent USB configuration

```bash
adb shell '
strings -n 1 /data/property/persistent_properties |
grep -E -A2 -B2 "persist\.(vendor|sys)\.usb\.config"
'
```

### ADB enabled

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

### ADB key

```bash
adb shell 'ls -lZ /data/misc/adb/adb_keys'
```

Expected:

```text
-rw-r----- 1 system shell ... u:object_r:adb_keys_file:s0
```

### Persistent-properties permissions/context

```bash
adb shell 'ls -lZ /data/property/persistent_properties'
```

Expected:

```text
-rw------- 1 root root ... u:object_r:property_data_file:s0
```

### Settings permissions/context

```bash
adb shell 'ls -lZ /data/system/users/0/settings_global.xml'
```

Expected:

```text
-rw------- 1 system system ... u:object_r:system_data_file:s0
```

---

## 8. Optional — restore the Magisk boot script

This is optional.

The current Magisk 24.2 setup discovered `usb-adb.sh` during boot, but its log also showed a BusyBox execution failure. Therefore the script is **not the primary recovery mechanism**.

Only restore it after Magisk itself is working:

```bash
adb push scripts/usb-adb.sh \
    /data/local/tmp/usb-adb.sh
```

```bash
adb shell "su -c '
mkdir -p /data/adb/service.d

cp /data/local/tmp/usb-adb.sh \
   /data/adb/service.d/usb-adb.sh

chown 0:0 \
   /data/adb/service.d/usb-adb.sh

chmod 755 \
   /data/adb/service.d/usb-adb.sh

rm -f /data/local/tmp/usb-adb.sh
'"
```

Verify:

```bash
adb shell "su -c '
ls -lZ /data/adb/service.d/usb-adb.sh
'"
```

---

## 9. Reboot Android

Only reboot after the verification steps above pass:

```bash
adb reboot
```

Wait for Android to finish booting.

---

## 10. Verify ADB

```bash
adb devices
```

Expected:

```text
List of devices attached
8546e62c    device
```

Check USB/ADB configuration:

```bash
adb shell '
echo "persist.sys.usb.config=$(getprop persist.sys.usb.config)"
echo "persist.vendor.usb.config=$(getprop persist.vendor.usb.config)"
echo "sys.usb.config=$(getprop sys.usb.config)"
echo "adb_enabled=$(settings get global adb_enabled)"
'
```

Expected runtime state:

```text
persist.sys.usb.config=mtp,adb
persist.vendor.usb.config=
sys.usb.config=mtp,adb
adb_enabled=1
```

Check root if Magisk was restored:

```bash
adb shell su -c id
```

Expected:

```text
uid=0(root)
```

---

# Emergency Notes

### If `adb devices` is empty after reboot

Do not wipe `/data` again.

Return to TWRP and repeat the recovery steps.

### If `/data` is not accessible in TWRP

Mount `/data` from the TWRP UI, then verify:

```bash
adb shell 'ls -ld /data /data/property /data/system'
```

### If the ADB key is rejected

Restore:

```text
backup/adb_keys
```

with the ownership, permissions and SELinux context shown above.

### If Magisk is missing

The repository does **not** contain the complete Magisk installation. Reinstall a compatible Magisk version separately, then restore the optional `service.d` script.

---

# Final Success Criteria

Recovery is complete when all of these are true:

```text
adb devices
    └── 8546e62c    device

persist.sys.usb.config
    └── mtp,adb

sys.usb.config
    └── mtp,adb

adb_enabled
    └── 1
```

And, when Magisk is installed:

```text
adb shell su -c id
    └── uid=0(root)
```
