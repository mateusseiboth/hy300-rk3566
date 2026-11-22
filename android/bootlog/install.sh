#!/usr/bin/env bash
# Instala a animação de boot com log ao vivo via overlay do adb remount.
# Pré-requisito: adb disable-verity já aplicado (ver scripts/apply-leanback.sh).
set -euo pipefail
cd "$(dirname "$0")"
[[ -f out/bootlog.dex ]] || ./build.sh
adb root >/dev/null; sleep 3; adb wait-for-device
adb remount
adb shell mkdir -p /system/media/bootlog
adb push out/bootlog.dex files/logo.png files/bootlog.sh /system/media/bootlog/
adb shell chmod 644 /system/media/bootlog/bootlog.dex /system/media/bootlog/logo.png
adb shell chmod 755 /system/media/bootlog/bootlog.sh
# guarda o rc original uma vez
adb shell '[ -f /system/etc/init/bootanim.rc.orig ] || cp /system/etc/init/bootanim.rc /system/etc/init/bootanim.rc.orig'
adb push files/bootanim.rc /system/etc/init/bootanim.rc
# animação nativa vira 1 quadro (capivara) enquanto o ART não está pronto
adb shell '[ -f /system/media/bootanimation.zip.orig ] || cp /system/media/bootanimation.zip /system/media/bootanimation.zip.orig'
adb push files/bootanimation.zip /system/media/bootanimation.zip
adb shell chmod 644 /system/media/bootanimation.zip
adb shell chmod 644 /system/etc/init/bootanim.rc
echo "ok — reinicie para ver (adb reboot)"
