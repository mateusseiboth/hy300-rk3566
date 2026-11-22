#!/usr/bin/env bash
# Instala o overlay estático (RRO) que troca o sabor do TvSettings do aparelho (com.android.tv.set)
# de "Classic" para "X": menu principal e "Preferências do dispositivo" completos (Armazenamento,
# Protetor de tela, Economia de energia, Acessibilidade, Reiniciar, Avançado...).
# Vai para /product/overlay pelo overlay do adb remount; nada é apagado da partição.
# NÃO reinicia: rode "adb reboot" depois. Reverter: ./uninstall-tvsettings-overlay.sh
# Aparelho: use ANDROID_SERIAL=<ip:porta> se houver mais de um conectado.
set -euo pipefail
cd "$(dirname "$0")/.."
APK=tvsettings-overlay/build/outputs/apk/release/tvsettings-overlay-release.apk
[[ -f "$APK" ]] || { echo "compile antes: ./gradlew assembleRelease"; exit 1; }
adb root >/dev/null; sleep 3; adb wait-for-device
adb remount
adb shell mkdir -p /product/overlay/HY300TvSettingsOverlay
adb push "$APK" /product/overlay/HY300TvSettingsOverlay/HY300TvSettingsOverlay.apk
adb shell chmod 755 /product/overlay/HY300TvSettingsOverlay
adb shell chmod 644 /product/overlay/HY300TvSettingsOverlay/HY300TvSettingsOverlay.apk
echo "ok. Reinicie (adb reboot) e confira: adb shell cmd overlay list com.android.tv.set"
