#!/usr/bin/env bash
# Grava uma imagem de teste na partição `recovery` (o slot de teste do kernel) e confere o
# SHA-256 no próprio aparelho. Manda comprimido: a recovery tem dezenas de MB de zeros.
#
# Uso: ./flash-test-recovery.sh imagem.img [backup_de_fabrica]
# Reverter: ./flash-test-recovery.sh ~/hy300-backup/recovery.img
#
# Só grava se a recovery atual for a de fábrica ou uma imagem que este script já gravou
# (registradas em ~/hy300-backup/recovery-gravadas.txt), para não perder nada sem backup.
set -euo pipefail
IMG="$1"
FACTORY="${2:-$HOME/hy300-backup}"
KNOWN="$FACTORY/recovery-gravadas.txt"
PART=/dev/block/by-name/recovery

device_hash() { adb shell "sha256sum $PART" | cut -c1-64; }
factory_hash() { awk '$2 == "recovery.img" || $2 == "./recovery.img" { print $1 }' "$FACTORY/SHA256SUMS"; }
is_known() { [[ "$1" == "$(factory_hash)" ]] || grep -qx "$1" "$KNOWN" 2>/dev/null; }

adb root >/dev/null; sleep 3; adb wait-for-device
part_size="$(adb shell "blockdev --getsize64 $PART" | tr -d '\r')"
(( $(stat -c %s "$IMG") <= part_size )) || { echo "imagem maior que a partição ($part_size)"; exit 1; }
current="$(device_hash)"
is_known "$current" || { echo "recovery atual ($current) não tem backup conhecido; abortando"; exit 1; }

want="$(sha256sum "$IMG" | cut -c1-64)"
echo ">> gravando $(basename "$IMG") na recovery"
gzip -1 -c "$IMG" | adb exec-in "gzip -dc > $PART && sync"
padded="$(adb shell "head -c $(stat -c %s "$IMG") $PART | sha256sum" | cut -c1-64)"
[[ "$padded" == "$want" ]] || { echo "FALHOU: hash gravado $padded != $want"; exit 1; }
device_hash >> "$KNOWN"
echo "ok: recovery = $(basename "$IMG") ($want)"
