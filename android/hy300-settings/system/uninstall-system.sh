#!/usr/bin/env bash
# Reverte install-system.sh: tira o priv-app, a privapp-permissions e o .rc dos LEDs do overlay.
# A cópia em /data (se houver) continua instalada como app comum. Reinicie depois.
set -euo pipefail
adb root >/dev/null; sleep 3; adb wait-for-device
adb remount
adb shell rm -rf /system/priv-app/HY300Settings /system/etc/permissions/privapp-permissions-hy300-settings.xml \
    /system/etc/init/hy300-settings.rc
echo "ok. Reinicie (adb reboot)."
