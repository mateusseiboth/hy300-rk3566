#!/usr/bin/env bash
# Compila o wpa_supplicant e o wpa_cli estáticos (aarch64, musl) para o modo Wi-Fi do
# initramfs de teste. Driver nl80211 com a libnl 3 estática; criptografia interna do hostap
# (sem OpenSSL), que cobre WPA/WPA2-PSK. WPA3-SAE precisaria de OpenSSL.
#
# Uso: build-wpa-supplicant.sh <saida_bin> [dir_de_trabalho]
#   saida_bin:       diretório onde ficam wpa_supplicant e wpa_cli
#   dir_de_trabalho: padrão ~/hy300-work/wifi/build (o musl vem do initramfs de teste,
#                    ~/hy300-work/marco1/initramfs/sysroot, que o build.sh compila)
#
# Requer: aarch64-linux-gnu-gcc, make, curl. Tarballs conferidos por SHA-256.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$1"
WORK="${2:-$HOME/hy300-work/wifi/build}"
CROSS="${CROSS_COMPILE:-aarch64-linux-gnu-}"
JOBS="${JOBS:-$(nproc)}"
DL="$WORK/dl"
SYSROOT="${MUSL_SYSROOT:-$HOME/hy300-work/marco1/initramfs/sysroot}"
PREFIX="$WORK/prefix"

LIBNL_VERSION=3.11.0
LIBNL_SHA256=2a56e1edefa3e68a7c00879496736fdbf62fc94ed3232c0baba127ecfa76874d
WPA_VERSION=2.11
WPA_SHA256=912ea06f74e30a8e36fbb68064d6cdff218d8d591db0fc5d75dee6c81ac7fc0a

# shellcheck source=kernel/lib-musl.sh
. "$HERE/../lib-musl.sh"

require_musl() {
	[[ -x "$SYSROOT/bin/musl-gcc" ]] ||
		{ echo "musl ausente em $SYSROOT: rode antes kernel/initramfs-test/build.sh"; exit 1; }
}

build_libnl() {
	fetch "https://github.com/thom311/libnl/releases/download/libnl${LIBNL_VERSION//./_}/libnl-$LIBNL_VERSION.tar.gz" "$LIBNL_SHA256"
	extract "$DL/libnl-$LIBNL_VERSION.tar.gz" "$WORK/libnl"
	(cd "$WORK/libnl" &&
		REALGCC="${CROSS}gcc" ./configure --host="${CROSS%-}" --prefix="$PREFIX" --disable-shared \
			--enable-static --disable-cli --disable-debug CC="$SYSROOT/bin/musl-gcc" >/dev/null &&
		REALGCC="${CROSS}gcc" make -s -j"$JOBS" >"$WORK/libnl-build.log" 2>&1 &&
		REALGCC="${CROSS}gcc" make -s install >>"$WORK/libnl-build.log" 2>&1)
}

# Só o necessário: nl80211, WPA-PSK, ctrl_iface para o wpa_cli e log em arquivo (-f).
write_wpa_config() {
	cat <<'EOF'
CONFIG_DRIVER_NL80211=y
CONFIG_LIBNL32=y
CONFIG_TLS=internal
CONFIG_INTERNAL_LIBTOMMATH=y
CONFIG_CRYPTO=internal
CONFIG_CTRL_IFACE=y
CONFIG_BACKEND=file
CONFIG_NO_CONFIG_WRITE=y
CONFIG_GETRANDOM=y
CONFIG_ELOOP_POLL=y
CONFIG_DEBUG_FILE=y
CONFIG_IEEE80211W=y
CONFIG_IEEE80211N=y
CONFIG_IEEE80211AC=y
EOF
}

build_wpa() {
	fetch "https://w1.fi/releases/wpa_supplicant-$WPA_VERSION.tar.gz" "$WPA_SHA256"
	extract "$DL/wpa_supplicant-$WPA_VERSION.tar.gz" "$WORK/wpa"
	write_wpa_config >"$WORK/wpa/wpa_supplicant/.config"
	(cd "$WORK/wpa/wpa_supplicant" &&
		REALGCC="${CROSS}gcc" make -s -j"$JOBS" CC="$SYSROOT/bin/musl-gcc" PKG_CONFIG=false \
			EXTRA_CFLAGS="-Os -I$PREFIX/include/libnl3" LDFLAGS="-static -L$PREFIX/lib" \
			LIBS="-lnl-genl-3 -lnl-3" wpa_supplicant wpa_cli >/dev/null)
}

main() {
	require_musl
	mkdir -p "$WORK" "$OUT"
	build_libnl
	build_wpa
	for bin in wpa_supplicant wpa_cli; do
		"${CROSS}strip" -o "$OUT/$bin" "$WORK/wpa/wpa_supplicant/$bin"
	done
	echo "ok $OUT: wpa_supplicant $WPA_VERSION e wpa_cli (libnl $LIBNL_VERSION, musl, estáticos)"
}

main
