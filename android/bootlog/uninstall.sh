#!/usr/bin/env bash
set -euo pipefail
adb root >/dev/null; sleep 3; adb wait-for-device
adb remount
adb shell 'mv /system/etc/init/bootanim.rc.orig /system/etc/init/bootanim.rc && rm -rf /system/media/bootlog'
echo "ok — animação original restaurada (reinicie)"
