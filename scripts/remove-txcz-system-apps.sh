#!/usr/bin/env bash
# Remove do /system e /product (via overlay do adb remount) os apps TXCZ com telemetria/backdoor:
#   com.shzhtxcz.txbox          backdoor: instala/desinstala APKs do servidor, envia logcat (reverse-engineering/telemetria)
#   com.shzhtxcz.txbox.launcher launcher que envia serial/MACs em HTTP
#   com.txcz.update             Adups FOTA (envia androidId/MAC)
# Reverter: restaurar a super do backup, ou apagar os whiteouts em /mnt/scratch/overlay/{system,product}/upper.
set -euo pipefail
adb root >/dev/null; sleep 3; adb wait-for-device
adb remount
# 1) atualização em /data do txbox (senão vira app de usuário órfão)
adb shell pm uninstall com.shzhtxcz.txbox 2>/dev/null || true
# 2) apaga os APKs de sistema
adb shell 'rm -rf /system/app/txczbox /system/app/txcz_launcher /product/app/FotaUpdate'
# 3) dados residuais
adb shell 'rm -rf /data/data/com.shzhtxcz.txbox /data/data/com.shzhtxcz.txbox.launcher /data/data/com.txcz.update /data/user_de/0/com.shzhtxcz.txbox* /data/user_de/0/com.txcz.update'
echo "ok — reinicie (adb reboot)"
