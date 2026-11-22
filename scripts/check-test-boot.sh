#!/usr/bin/env bash
# Depois de um boot de teste pela `recovery` e da volta ao Android (reboot quente, sem tirar
# da tomada): mostra se o kernel de teste bootou (marca na cmdline gravada no pstore), de onde
# a recovery tirou os argumentos e se a `misc` continua igual à de fábrica.
#
# Uso: ./check-test-boot.sh [marca] [backup_de_fabrica]   (padrão: hy300.test)
set -euo pipefail
MARK="${1:-hy300.test}"
FACTORY="${2:-$HOME/hy300-backup}"
adb root >/dev/null; sleep 3; adb wait-for-device

echo "== pstore (boot anterior)"
adb shell "grep -m1 -E 'Kernel command line|Linux version' /sys/fs/pstore/console-ramoops-0; \
  grep -c '$MARK' /sys/fs/pstore/console-ramoops-0" || echo "sem pstore ou sem a marca"

echo "== registros do pstore (dmesg-ramoops-* aparece se o kernel de teste deu panic)"
adb shell "ls -l /sys/fs/pstore" || true

echo "== /init de teste (marco 1 em diante: linhas 'hy300: [init]' e 'hy300: [misc]')"
adb shell "grep -E 'hy300: \[(init|misc)\]' /sys/fs/pstore/console-ramoops-0" || echo "nenhuma linha do /init de teste"

echo "== argumentos da recovery (/cache/recovery/last_log)"
adb shell "grep -iE 'arguments|boot message|Command:' /cache/recovery/last_log" || echo "nada no last_log"

echo "== misc"
factory="$(awk '$2 == "misc.img" || $2 == "./misc.img" { print $1 }' "$FACTORY/SHA256SUMS")"
current="$(adb shell 'sha256sum /dev/block/by-name/misc' | cut -c1-64)"
[[ "$current" == "$factory" ]] && echo "igual à fábrica" || { echo "MUDOU:"; adb shell 'head -c 64 /dev/block/by-name/misc | od -c | head -4'; }
