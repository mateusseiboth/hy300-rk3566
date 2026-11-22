#!/usr/bin/env bash
# Remove do /system e do /odm (via overlay do adb remount) dois apps que rodam com uid system:
#   com.rockchips.mediacenter  player do SDK Rockchip; uid system com INSTALL/DELETE_PACKAGES,
#                              MASTER_CLEAR, READ_LOGS, INJECT_EVENTS, internet e DLNA; sobe no boot
#   com.android.toofifi        espelhamento da TXCZ (TXCZTVApp), processo persistente uid system
# Opcional: instala um player comum no lugar (sem privilégio), ex. o VLC armeabi-v7a de
# https://get.videolan.org/vlc-android/last/ (confira o .sha256 publicado ao lado).
#
# Uso: ./remove-mediacenter-toofifi.sh [player.apk]
# Reverter: ./restore-mediacenter-toofifi.sh
set -euo pipefail
PLAYER_APK="${1:-}"

adb root >/dev/null; sleep 3; adb wait-for-device
adb remount
adb shell 'rm -rf /system/priv-app/MediaCenter /odm/bundled_persist-app/TXCZTVApp_FTZX_*'
adb shell 'rm -rf /data/data/com.rockchips.mediacenter /data/data/com.android.toofifi \
  /data/user_de/0/com.rockchips.mediacenter /data/user_de/0/com.android.toofifi'
[[ -n "$PLAYER_APK" ]] && adb install -r "$PLAYER_APK"
echo "ok, reinicie (adb reboot)"
