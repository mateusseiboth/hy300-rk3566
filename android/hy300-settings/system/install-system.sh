#!/usr/bin/env bash
# Instala o app como priv-app (/system/priv-app/HY300Settings) via overlay do adb remount.
# Necessário para o item "Projetor" aparecer no menu principal do TvSettings (com.android.tv.set),
# que só aceita apps com FLAG_SYSTEM. NÃO reinicia: rode "adb reboot" depois.
# Reverter: ./uninstall-system.sh
set -euo pipefail
cd "$(dirname "$0")/.."
APK=app/build/outputs/apk/release/app-release.apk
[[ -f "$APK" ]] || { echo "compile antes: ./gradlew assembleRelease"; exit 1; }
adb root >/dev/null; sleep 3; adb wait-for-device
adb remount
adb shell mkdir -p /system/priv-app/HY300Settings
adb push "$APK" /system/priv-app/HY300Settings/HY300Settings.apk
adb push system/privapp-permissions-hy300-settings.xml /system/etc/permissions/
adb shell chmod 755 /system/priv-app/HY300Settings
adb shell chmod 644 /system/priv-app/HY300Settings/HY300Settings.apk /system/etc/permissions/privapp-permissions-hy300-settings.xml
echo "ok — reinicie (adb reboot). A cópia em /data (mesma assinatura) vira atualização do app de sistema."
