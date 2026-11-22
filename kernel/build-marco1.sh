#!/usr/bin/env bash
# Monta do zero a imagem de teste do marco 1: kernel BSP Rockchip 6.1 (branch hy300-6.1),
# DTB do HY300, initramfs de teste e recovery-marco1.img (boot.img header v2) por cima da
# recovery de fábrica. Não grava nada no aparelho.
#
# Uso: kernel/build-marco1.sh [fonte_do_kernel] [dir_de_trabalho] [backup_de_fabrica]
#   padrões: ~/hy300-handoff/kernel-hy300-rk3566, ~/hy300-work/marco1, ~/hy300-backup
# Variáveis: KBUILD_OUT (build do kernel, padrão ~/hy300-work/kbuild-6.1), JOBS,
#            SMOKE=0 para pular o teste de fumaça no QEMU.
#
# Saída: <dir_de_trabalho>/recovery-marco1.img (+ .sha256). Gravar com
# scripts/flash-test-recovery.sh (roteiro em docs/kernel-6.1.md).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
KSRC="$(cd "${1:-$HOME/hy300-handoff/kernel-hy300-rk3566}" && pwd)"
WORK="${2:-$HOME/hy300-work/marco1}"
FACTORY="${3:-$HOME/hy300-backup}"
KOUT="${KBUILD_OUT:-$HOME/hy300-work/kbuild-6.1}"
JOBS="${JOBS:-$(nproc)}"
SMOKE="${SMOKE:-1}"

CROSS=aarch64-linux-gnu-
DTB_NAME=rk3566-hy300.dtb
CONFIGS=(rockchip_linux_defconfig rk3566.config rk3566_hy300.config)
MARK="hy300.test=marco1 panic=10"
RECOVERY_PART_SIZE=113246208

IMAGE="$KOUT/arch/arm64/boot/Image"
DTB="$KOUT/arch/arm64/boot/dts/rockchip/$DTB_NAME"
INITRAMFS="$WORK/initramfs-marco1.cpio.gz"
OUT="$WORK/recovery-marco1.img"

# Nome neutro no "Linux version": a imagem não deve carregar usuário/máquina de quem compilou.
export KBUILD_BUILD_USER=hy300 KBUILD_BUILD_HOST=build

kmake() {
	make -s -C "$KSRC" O="$1" ARCH=arm64 CROSS_COMPILE="$CROSS" -j"$JOBS" "${@:2}"
}

require_factory_recovery() {
	local want got
	want="$(awk '$2 == "recovery.img" || $2 == "./recovery.img" { print $1 }' "$FACTORY/SHA256SUMS")"
	got="$(sha256sum "$FACTORY/recovery.img" | cut -c1-64)"
	[[ -n "$want" && "$want" == "$got" ]] || { echo "recovery.img de fábrica não confere com SHA256SUMS"; exit 1; }
}

build_kernel() {
	echo ">> kernel: $(git -C "$KSRC" rev-parse --abbrev-ref HEAD) $(git -C "$KSRC" rev-parse --short HEAD)"
	mkdir -p "$KOUT"
	kmake "$KOUT" "${CONFIGS[@]}" >/dev/null
	kmake "$KOUT" Image "rockchip/$DTB_NAME"
}

build_initramfs() {
	echo ">> initramfs"
	"$REPO/kernel/initramfs-test/build.sh" "$KSRC" "$INITRAMFS" "$WORK/initramfs"
}

# O U-Boot de fábrica lê o DTB do kernel da seção dtb do header v2 e, sem ela, do
# rk-kernel.dtb do resource.img (seção second). Os dois recebem o DTB novo.
build_resource() {
	echo ">> resource.img"
	python3 "$REPO/tools/rk_resource.py" boot-extract "$FACTORY/recovery.img" "$WORK/resource-fabrica.img" >/dev/null
	python3 "$REPO/tools/rk_resource.py" replace "$WORK/resource-fabrica.img" rk-kernel.dtb "$DTB" \
		"$WORK/resource-marco1.img" >/dev/null
}

build_image() {
	echo ">> recovery-marco1.img"
	python3 "$REPO/tools/mkboot.py" build --like "$FACTORY/recovery.img" -o "$OUT" \
		--kernel "$IMAGE" --ramdisk "$INITRAMFS" --second "$WORK/resource-marco1.img" --dtb "$DTB" \
		--append-cmdline "$MARK" --pad-to-like
}

require_same() {
	cmp -s "$1" "$2" || { echo "FALHOU: $3"; exit 1; }
}

verify_image() {
	local check="$WORK/check"
	(($(stat -c %s "$OUT") <= RECOVERY_PART_SIZE)) || { echo "FALHOU: maior que a partição"; exit 1; }
	rm -rf "$check"
	python3 "$REPO/tools/mkboot.py" unpack "$OUT" "$check" >/dev/null
	python3 "$REPO/tools/rk_resource.py" unpack "$check/second" "$check/res" >/dev/null
	require_same "$check/kernel" "$IMAGE" "kernel"
	require_same "$check/ramdisk" "$INITRAMFS" "ramdisk"
	require_same "$check/dtb" "$DTB" "seção dtb"
	require_same "$check/res/rk-kernel.dtb" "$DTB" "rk-kernel.dtb do resource"
	grep -q "$MARK" "$check/header.json" || { echo "FALHOU: cmdline sem a marca"; exit 1; }
	sha256sum "$OUT" | tee "$OUT.sha256"
	echo "ok: $(stat -c %s "$OUT") bytes (partição: $RECOVERY_PART_SIZE)"
}

# Teste de fumaça do /init num kernel com PL011/virtio (build à parte, incremental).
run_smoke() {
	[[ "$SMOKE" == 1 ]] || { echo ">> smoke: pulado (SMOKE=$SMOKE)"; return; }
	command -v qemu-system-aarch64 >/dev/null || { echo ">> smoke: pulado (sem qemu-system-aarch64)"; return; }
	echo ">> smoke (QEMU)"
	local qout="$KOUT-qemu"
	mkdir -p "$qout"
	kmake "$qout" "${CONFIGS[@]}" >/dev/null
	"$KSRC/scripts/kconfig/merge_config.sh" -m -O "$qout" "$qout/.config" \
		"$REPO/kernel/initramfs-test/qemu.config" >/dev/null
	kmake "$qout" olddefconfig >/dev/null
	kmake "$qout" Image
	python3 "$REPO/kernel/initramfs-test/smoke-qemu.py" "$qout/arch/arm64/boot/Image" "$INITRAMFS" \
		"$WORK/qemu" "$FACTORY/misc.img"
}

main() {
	mkdir -p "$WORK"
	require_factory_recovery
	build_kernel
	build_initramfs
	build_resource
	build_image
	verify_image
	run_smoke
}

main
