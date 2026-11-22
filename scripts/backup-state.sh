#!/usr/bin/env bash
# Backup do estado atual do aparelho, incremental sobre o backup de fábrica.
#
# Não copia de novo o que o backup de fábrica já tem: calcula o SHA-256 de cada partição
# NO APARELHO e só puxa as que diferem do SHA256SUMS da fábrica. A super não é copiada:
# o que mudou nela é o overlay do `adb remount`, que vai como arquivo.
#
# Uso: ./backup-state.sh [backup_de_fabrica] [destino]
#   padrão: ~/hy300-backup  e  ~/hy300-backup/estado-AAAAMMDD-HHMM
# Precisa de adb root. Use ANDROID_SERIAL para escolher o aparelho.
set -euo pipefail

FACTORY="${1:-$HOME/hy300-backup}"
DEST="${2:-$FACTORY/estado-$(date +%Y%m%d-%H%M)}"
PARTS=(uboot trust misc dtbo vbmeta boot recovery security baseparameter backup cust metadata)

factory_hash() { awk -v f="$1.img" '$2 == f || $2 == "./" f { print $1 }' "$FACTORY/SHA256SUMS"; }
device_hash() { adb shell "sha256sum /dev/block/by-name/$1" | cut -c1-64; }

save_changed_partitions() {
  mkdir -p "$DEST/particoes"
  for n in "${PARTS[@]}"; do
    [[ "$(device_hash "$n")" == "$(factory_hash "$n")" ]] && { echo "   $n: igual à fábrica"; continue; }
    echo ">> $n: mudou, copiando"
    adb exec-out "dd if=/dev/block/by-name/$n bs=4M 2>/dev/null" > "$DEST/particoes/$n.img"
  done
}

save_overlay() {
  echo ">> overlay do remount (/mnt/scratch/overlay/*/upper)"
  adb exec-out 'tar -cf - -C /mnt/scratch overlay' > "$DEST/overlay.tar"
}

save_system_state() {
  echo ">> props persistentes e estado do sistema"
  adb exec-out 'tar -cf - -C / data/property data/system/users/0 data/system/packages.xml data/system/packages.list data/system/overlays.xml data/misc/wifi 2>/dev/null' \
    > "$DEST/sistema.tar"
  adb shell getprop > "$DEST/props.txt"
  adb shell pm list packages -f -u > "$DEST/packages.txt"
  adb shell pm list packages -d > "$DEST/packages-desativados.txt"
  adb shell cmd overlay list > "$DEST/overlays.txt"
  adb shell settings list secure > "$DEST/settings-secure.txt"
  adb shell settings list global > "$DEST/settings-global.txt"
  adb shell settings list system > "$DEST/settings-system.txt"
}

save_user_apps() {
  mkdir -p "$DEST/apps"
  for p in $(adb shell pm list packages -3 | cut -d: -f2 | tr -d '\r'); do
    local apk_dir
    apk_dir="$(adb shell pm path "$p" | head -1 | cut -d: -f2 | tr -d '\r' | xargs dirname)"
    echo ">> app $p"
    adb exec-out "tar -cf - -C / ${apk_dir#/} data/data/$p data/user_de/0/$p 2>/dev/null" > "$DEST/apps/$p.tar"
  done
}

adb root >/dev/null; sleep 3
mkdir -p "$DEST"
save_changed_partitions
save_overlay
save_system_state
save_user_apps
( cd "$DEST" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS )
echo "ok -> $DEST"
