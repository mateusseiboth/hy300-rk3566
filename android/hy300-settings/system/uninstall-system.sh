#!/usr/bin/env bash
set -euo pipefail
adb root >/dev/null; sleep 3; adb wait-for-device
adb remount
adb shell rm -rf /system/priv-app/HY300Settings /system/etc/permissions/privapp-permissions-hy300-settings.xml
echo "ok — reinicie (adb reboot)"
