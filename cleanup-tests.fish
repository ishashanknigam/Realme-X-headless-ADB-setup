#!/usr/bin/env fish
cd ~/Documents/realme-x-headless-adb

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

rm -f scripts/patch_reboot_func.py scripts/patch_allcommode.py
rm -rf info/boot-capture

echo 'Cleanup complete. Kept primary backups and repository files.'
