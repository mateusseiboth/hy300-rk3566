#!/usr/bin/env bash
# Reinstala para o usuário 0 os pacotes removidos pelo debloat.sh.
set -euo pipefail
cd "$(dirname "$0")"
while read -r p; do
  [[ -z "$p" || "$p" == \#* ]] && continue
  printf '%-50s ' "$p"
  adb shell pm install-existing "$p" 2>&1 || true
done < debloat-packages.txt
