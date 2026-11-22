#!/usr/bin/env bash
# Bloqueia os endereços de telemetria da TXCZ/Adups (reverse-engineering/telemetria/README.md),
# como segunda barreira: os apps que os usavam (txbox, launcher TXCZ, Adups, toofifi) já foram removidos.
#   - domínios: /system/etc/hosts (overlay do remount) apontando para 0.0.0.0
#   - IP fixo 47.113.90.237: regra de iptables aplicada agora e em todo boot (init .rc no overlay)
# Reverter: ./unblock-telemetry.sh
set -euo pipefail
IP=47.113.90.237
DOMAINS=(shzhtxcz.com www.shzhtxcz.com fota5p.adups.com fota5p.adups.cn fruet.adups.com mfcopenapi.info)

adb root >/dev/null; sleep 3; adb wait-for-device
adb remount >/dev/null
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

{
  printf '127.0.0.1       localhost\n::1             ip6-localhost\n\n# telemetria TXCZ/Adups (hy300-rk3566)\n'
  printf '0.0.0.0 %s\n' "${DOMAINS[@]}"
} > "$TMP/hosts"

# O iptables precisa de um domínio SELinux próprio: o init não roda executável que ficaria
# no domínio dele. O su existe no build userdebug.
cat > "$TMP/hy300-telemetria.rc" <<RC
service hy300-telemetria /system/bin/iptables -w -I OUTPUT -d $IP -j REJECT
    user root
    group root
    seclabel u:r:su:s0
    oneshot
    disabled

on property:sys.boot_completed=1
    start hy300-telemetria
RC

# adb push, nunca `adb exec-in`: neste aparelho o exec-in passa por um terminal e deixou o
# .rc com modo 666, que o init ignora ("insecure file").
push_file() {
  adb push "$1" "$2" >/dev/null
  adb shell "chmod 644 $2"
}
push_file "$TMP/hosts" /system/etc/hosts
push_file "$TMP/hy300-telemetria.rc" /system/etc/init/hy300-telemetria.rc
adb shell "iptables -w -C OUTPUT -d $IP -j REJECT 2>/dev/null || iptables -w -I OUTPUT -d $IP -j REJECT"
echo "ok (o .rc vale a partir do próximo boot)"
