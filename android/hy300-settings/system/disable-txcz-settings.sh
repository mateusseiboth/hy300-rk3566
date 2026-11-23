#!/usr/bin/env bash
# Aposenta o app de configurações da TXCZ (com.android.tv.settings, /system/app/TxczSetting)
# de forma reversível: "pm disable" do pacote inteiro, nada é apagado da partição.
#
# Por quê: ele era o único destino de android.settings.SETTINGS, então "Configurações do
# Android" (Projectivy, atalhos) abria a tela da TXCZ. Com ele desativado, a ação cai no
# AndroidSettingsActivity deste app, que repassa para o TvSettings (com.android.tv.set). Esse
# componente vem desligado no manifesto (no LineageOS ele duplicaria o TvSettings) e é ligado
# aqui com "pm enable".
#
# O que o pacote fazia no boot (conferido no jadx, ver README do app): SoundBoxService
# (só com persist.txcz.sound.enable=1), Sensorservice (só com o app com.hysd.txczscreen,
# ausente) e TaitouService (keystone automático, por persist.txcz.tt.enable). Nada disso
# é necessário para o keystone ou a fonte: o SurfaceFlinger lê persist.sys.keystone.* e o
# services.jar lê persist.txcz.source/boot.app sozinhos.
#
# Também:
#  - grava persist.txcz.tt.enable=0, para o TaitouService não voltar se o pacote for reativado;
#  - troca o protetor de tela padrão (era o da TXCZ) pelo Colors do AOSP, se for o caso;
#  - liga o F12KeyService (a tecla F12 abria a tela da TXCZ pelo framework).
# Reverter: ./enable-txcz-settings.sh
# Aparelho: use ANDROID_SERIAL=<ip:porta> se houver mais de um conectado.
set -euo pipefail
PKG=com.android.tv.settings
TXCZ_DREAM=com.android.tv.settings/com.shzhtxcz.txbox.service.MyDreamService
AOSP_DREAM=com.android.dreams.basic/com.android.dreams.basic.Colors
F12=io.github.hy300.settings/io.github.hy300.settings.F12KeyService

adb root >/dev/null; sleep 3; adb wait-for-device

adb shell pm path io.github.hy300.settings >/dev/null || { echo "instale o app antes (adb install ou install-system.sh)"; exit 1; }

adb shell pm disable "$PKG"
# Desligada no manifesto (no LineageOS o TvSettings já trata android.settings.SETTINGS).
adb shell pm enable io.github.hy300.settings/.AndroidSettingsActivity
adb shell setprop persist.txcz.tt.enable 0

for key in screensaver_components screensaver_default_component; do
    cur=$(adb shell settings get secure "$key" | tr -d '\r')
    [[ "$cur" == "$TXCZ_DREAM" ]] && adb shell settings put secure "$key" "$AOSP_DREAM"
done

adb shell pm grant io.github.hy300.settings android.permission.WRITE_SECURE_SETTINGS || true
services=$(adb shell settings get secure enabled_accessibility_services | tr -d '\r')
if [[ "$services" != *"$F12"* ]]; then
    [[ -z "$services" || "$services" == "null" ]] && services="$F12" || services="$services:$F12"
    adb shell settings put secure enabled_accessibility_services "$services"
fi
adb shell settings put secure accessibility_enabled 1

echo "android.settings.SETTINGS agora abre:"
adb shell cmd package resolve-activity --brief -a android.settings.SETTINGS | tail -1
echo "ok. Não precisa reiniciar."
