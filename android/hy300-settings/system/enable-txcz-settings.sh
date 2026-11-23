#!/usr/bin/env bash
# Reverte disable-txcz-settings.sh: reativa o app de configurações da TXCZ e volta o
# protetor de tela padrão para o dele. Não religa persist.txcz.tt.enable (o keystone
# automático da TXCZ) nem desliga o F12KeyService; para isso:
#   adb shell setprop persist.txcz.tt.enable 1
#   adb shell settings put secure enabled_accessibility_services null
set -euo pipefail
PKG=com.android.tv.settings
TXCZ_DREAM=com.android.tv.settings/com.shzhtxcz.txbox.service.MyDreamService
AOSP_DREAM=com.android.dreams.basic/com.android.dreams.basic.Colors

adb root >/dev/null; sleep 3; adb wait-for-device
adb shell pm enable "$PKG"
adb shell pm disable io.github.hy300.settings/.AndroidSettingsActivity
for key in screensaver_components screensaver_default_component; do
    cur=$(adb shell settings get secure "$key" | tr -d '\r')
    [[ "$cur" == "$AOSP_DREAM" ]] && adb shell settings put secure "$key" "$TXCZ_DREAM"
done
echo "android.settings.SETTINGS agora resolve para:"
adb shell cmd package resolve-activity --brief -a android.settings.SETTINGS | tail -1
echo "ok"
