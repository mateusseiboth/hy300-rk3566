#!/usr/bin/env bash
# Remove (para o usuário 0) os pacotes listados em debloat-packages.txt.
# Reversível: ./restore-debloat.sh  ou  adb shell pm install-existing <pacote>
set -euo pipefail
cd "$(dirname "$0")"
while read -r p; do
  [[ -z "$p" || "$p" == \#* ]] && continue
  printf '%-50s ' "$p"
  adb shell pm uninstall -k --user 0 "$p" 2>&1 || true
done < debloat-packages.txt
