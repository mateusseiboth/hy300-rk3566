#!/usr/bin/env bash
# Monta o initramfs de teste do marco 1: busybox estático (aarch64, musl), /init e
# /lib/hy300-test.sh. Nada é baixado sem conferir o SHA-256; nenhum binário vai para o repo.
#
# Uso: build.sh <fonte_do_kernel> <saida.cpio.gz> [dir_de_trabalho]
#   fonte_do_kernel: árvore do kernel (dá os headers do Linux para o musl/busybox e o
#                    gen_init_cpio, que cria /dev/console sem precisar de root)
#   dir_de_trabalho: padrão ~/hy300-work/marco1/initramfs
#
# Requer: aarch64-linux-gnu-gcc (Fedora: gcc-aarch64-linux-gnu), make, curl, gzip.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
KSRC="$(cd "$1" && pwd)"
OUT="$2"
WORK="${3:-$HOME/hy300-work/marco1/initramfs}"
CROSS="${CROSS_COMPILE:-aarch64-linux-gnu-}"
JOBS="${JOBS:-$(nproc)}"

BUSYBOX_VERSION=1.37.0
BUSYBOX_SHA256=3311dff32e746499f4df0d5df04d7eb396382d7e108bb9250e7b519b837043a4

DL="$WORK/dl"
SYSROOT="$WORK/sysroot"
ROOTFS="$WORK/rootfs"

# shellcheck source=kernel/lib-musl.sh
. "$HERE/../lib-musl.sh"

install_kernel_headers() {
	make -s -C "$KSRC" O="$WORK/kheaders" ARCH=arm64 INSTALL_HDR_PATH="$SYSROOT" headers_install
}

# defconfig do busybox, estático. TC não compila com headers novos e não é usado; o
# SHA "HWACCEL" do 1.37 só compila em x86.
configure_busybox() {
	make -s defconfig >/dev/null 2>&1
	sed -i -e 's/^# CONFIG_STATIC is not set/CONFIG_STATIC=y/' \
		-e 's/^CONFIG_TC=y/# CONFIG_TC is not set/' \
		-e 's/^CONFIG_FEATURE_TC_INGRESS=y/# CONFIG_FEATURE_TC_INGRESS is not set/' \
		-e 's/^CONFIG_SHA1_HWACCEL=y/# CONFIG_SHA1_HWACCEL is not set/' \
		-e 's/^CONFIG_SHA256_HWACCEL=y/# CONFIG_SHA256_HWACCEL is not set/' .config
	make -s oldconfig </dev/null >/dev/null 2>&1
}

build_busybox() {
	fetch "https://busybox.net/downloads/busybox-$BUSYBOX_VERSION.tar.bz2" "$BUSYBOX_SHA256"
	extract "$DL/busybox-$BUSYBOX_VERSION.tar.bz2" "$WORK/busybox"
	(cd "$WORK/busybox" &&
		configure_busybox &&
		REALGCC="${CROSS}gcc" make -s -j"$JOBS" CROSS_COMPILE="$CROSS" CC="$SYSROOT/bin/musl-gcc" \
			busybox busybox.links)
}

build_gen_init_cpio() {
	gcc -O2 -o "$WORK/gen_init_cpio" "$KSRC/usr/gen_init_cpio.c"
}

stage_rootfs() {
	rm -rf "$ROOTFS"
	install -D -m 755 "$WORK/busybox/busybox" "$ROOTFS/bin/busybox"
	install -D -m 755 "$HERE/init" "$ROOTFS/init"
	install -D -m 644 "$HERE/hy300-test.sh" "$ROOTFS/lib/hy300-test.sh"
}

# Lista do gen_init_cpio: diretórios, /dev/console e os links do busybox.
write_cpio_list() {
	printf 'dir %s 755 0 0\n' /bin /sbin /usr /usr/bin /usr/sbin /dev /proc /sys /tmp /lib
	echo "nod /dev/console 600 0 0 c 5 1"
	echo "nod /dev/kmsg 644 0 0 c 1 11"
	echo "file /init $ROOTFS/init 755 0 0"
	echo "file /lib/hy300-test.sh $ROOTFS/lib/hy300-test.sh 644 0 0"
	echo "file /bin/busybox $ROOTFS/bin/busybox 755 0 0"
	grep -v '^/bin/busybox$' "$WORK/busybox/busybox.links" | while read -r link; do
		echo "slink $link /bin/busybox 777 0 0"
	done
}

main() {
	mkdir -p "$WORK"
	install_kernel_headers
	build_musl
	build_busybox
	build_gen_init_cpio
	stage_rootfs
	write_cpio_list >"$WORK/cpio.list"
	"$WORK/gen_init_cpio" -t 0 "$WORK/cpio.list" | gzip -n -9 >"$OUT"
	echo "ok $OUT ($(stat -c %s "$OUT") bytes)"
}

main
