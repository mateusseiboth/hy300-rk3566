#!/usr/bin/env bash
# Instala o app como priv-app (/system/priv-app/HY300Settings) via overlay do adb remount.
# Necessário para o item "Projetor" aparecer no menu principal do TvSettings (com.android.tv.set),
# que só aceita apps com FLAG_SYSTEM. Também instala:
#  - privapp-permissions (WRITE_SECURE_SETTINGS, para ligar o atalho F12 pelo app);
#  - /system/etc/init/hy300-settings.rc (chmod dos LEDs indicadores no boot).
# NÃO reinicia: rode "adb reboot" depois. Reverter: ./uninstall-system.sh
# Aparelho: use ANDROID_SERIAL=<ip:porta> se houver mais de um conectado.
set -euo pipefail
cd "$(dirname "$0")/.."
APK=app/build/outputs/apk/release/app-release.apk
[[ -f "$APK" ]] || { echo "compile antes: ./gradlew assembleRelease"; exit 1; }
adb root >/dev/null; sleep 3; adb wait-for-device
adb remount
adb shell mkdir -p /system/priv-app/HY300Settings
adb push "$APK" /system/priv-app/HY300Settings/HY300Settings.apk
adb push system/privapp-permissions-hy300-settings.xml /system/etc/permissions/
adb push system/hy300-settings.rc /system/etc/init/hy300-settings.rc
adb shell chmod 755 /system/priv-app/HY300Settings
adb shell chmod 644 /system/priv-app/HY300Settings/HY300Settings.apk \
    /system/etc/permissions/privapp-permissions-hy300-settings.xml /system/etc/init/hy300-settings.rc
# A cópia em /data tem de ter a mesma assinatura e versão >= a do /system, ou o PackageManager
# descarta a de /data no boot. Instalar o mesmo APK nos dois lugares garante isso.
adb install -r "$APK"
echo "ok. Reinicie (adb reboot)."
