#!/usr/bin/env bash
# Desfaz o block-telemetry.sh: apaga do overlay o hosts alterado e o .rc, e tira a regra atual.
set -euo pipefail
adb root >/dev/null; sleep 3; adb wait-for-device
adb shell 'rm -f /mnt/scratch/overlay/system/upper/etc/hosts /mnt/scratch/overlay/system/upper/etc/init/hy300-telemetria.rc'
adb shell 'iptables -w -D OUTPUT -d 47.113.90.237 -j REJECT 2>/dev/null || true'
echo "ok, reinicie (adb reboot) para o hosts original voltar"
