#!/usr/bin/env bash
set -euo pipefail
adb root >/dev/null; sleep 3; adb wait-for-device
adb remount
adb shell rm -f /system/etc/permissions/android.software.leanback.xml
adb shell pm clear com.android.vending
echo "Reinicie. Para reativar a verificação dm-verity: adb enable-verity && adb reboot"
