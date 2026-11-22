#!/usr/bin/env bash
# Backup das partições do sistema via adb root (exceto userdata/cache).
# Uso: ./backup-partitions.sh [destino]   (padrão: ~/hy300-backup)
set -euo pipefail
DEST="${1:-$HOME/hy300-backup}"
mkdir -p "$DEST"; cd "$DEST"
adb root >/dev/null; sleep 2
for n in uboot trust misc dtbo vbmeta boot recovery security baseparameter backup cust metadata; do
  echo ">> $n"
  adb exec-out "dd if=/dev/block/by-name/$n bs=4M 2>/dev/null" > "$n.img"
done
echo ">> super (gzip no aparelho; ~3 GB, demora pelo Wi-Fi)"
adb exec-out 'dd if=/dev/block/by-name/super bs=4M 2>/dev/null | gzip -1' > super.img.gz
gzip -t super.img.gz
adb exec-out 'dd if=/dev/block/mmcblk2 bs=512 count=34 2>/dev/null' > gpt_head.bin
adb exec-out 'dd if=/dev/block/mmcblk2boot0 2>/dev/null' > mmcblk2boot0.img
adb shell getprop > props.txt
adb shell pm list packages -f -u > packages.txt
sha256sum ./*.img ./*.gz ./*.bin > SHA256SUMS
echo "ok -> $DEST"
