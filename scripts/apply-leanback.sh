#!/usr/bin/env bash
# Adiciona android.software.leanback via overlay do adb remount.
# Requer: build userdebug, adb root. Reinicia o aparelho 2x.
# Reverter: ./revert-leanback.sh
set -euo pipefail
cd "$(dirname "$0")/.."
IP="${HY300_IP:-}"   # opcional: IP para reconectar via Wi-Fi (ex.: 20.0.0.190)
reconnect() { sleep 45; [[ -n "$IP" ]] && adb connect "$IP:5555" >/dev/null || true; adb wait-for-device; adb root >/dev/null; sleep 3; [[ -n "$IP" ]] && adb connect "$IP:5555" >/dev/null || true; adb wait-for-device; }
adb root >/dev/null; sleep 3; adb wait-for-device
adb disable-verity || true
adb reboot; reconnect
adb remount
adb push android/permissions/android.software.leanback.xml /system/etc/permissions/
adb shell chmod 644 /system/etc/permissions/android.software.leanback.xml
adb reboot; reconnect
adb shell pm list features | grep leanback
# A Play Store precisa reler o perfil do aparelho
adb shell pm clear com.android.vending
adb shell am force-stop com.google.android.gms
