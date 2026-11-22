#!/usr/bin/env bash
# Desfaz o remove-mediacenter-toofifi.sh: apaga os whiteouts do overlay, e os APKs originais
# (que continuam na camada de baixo do /system e do /odm) voltam a aparecer no próximo boot.
set -euo pipefail
adb root >/dev/null; sleep 3; adb wait-for-device
adb shell 'rm -f /mnt/scratch/overlay/system/upper/priv-app/MediaCenter \
  /mnt/scratch/overlay/odm/upper/bundled_persist-app/TXCZTVApp_FTZX_*'
echo "ok, reinicie (adb reboot)"
