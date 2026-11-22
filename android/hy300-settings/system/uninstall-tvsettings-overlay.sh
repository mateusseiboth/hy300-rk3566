#!/usr/bin/env bash
# Reverte install-tvsettings-overlay.sh (o TvSettings volta ao sabor "Classic"). Reinicie depois.
set -euo pipefail
adb root >/dev/null; sleep 3; adb wait-for-device
adb remount
adb shell rm -rf /product/overlay/HY300TvSettingsOverlay
echo "ok. Reinicie (adb reboot)."
