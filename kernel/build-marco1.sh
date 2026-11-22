#!/usr/bin/env bash
# Monta do zero a imagem de teste do marco 1: kernel 6.1 do HY300, DTB, initramfs de teste e
# recovery-marco1.img (boot.img header v2) por cima da recovery de fábrica. Não grava nada no
# aparelho.
#
# Uso: kernel/build-marco1.sh [fonte_do_kernel] [dir_de_trabalho] [backup_de_fabrica]
#   padrões: ~/hy300-handoff/kernel-hy300-rk3566, ~/hy300-work/marco1-ack (bsp:
#            ~/hy300-work/marco1), ~/hy300-backup
# Variáveis: KBASE=ack (padrão: kernel Android da Rockchip, branch hy300-ack-6.1, clang) ou
#            KBASE=bsp (BSP Linux, branch hy300-6.1, GCC); ver kernel/lib-kbase.sh.
#            CLANG_DIR (padrão: clang-r547379 dos prebuilts do LineageOS, só leitura),
#            KCONFIG_REQS (padrão ~/android/lineage/kernel/configs/u/android-6.1; na base ack o
#            build falha se o .config não atender),
#            KBUILD_OUT (build do kernel, padrão ~/hy300-work/kbuild-ack-6.1), JOBS,
#            SMOKE=0 para pular o teste de fumaça no QEMU,
#            WIFI=1 para o modo Wi-Fi (hy300.wifi=1 na cmdline; módulos AIC8800, firmware,
#            wpa_supplicant e rede no initramfs). Lê WIFI_CREDENTIALS (padrão
#            ~/hy300-work/wifi/credenciais.conf, modo 600) e VENDOR_IMG (padrão
#            ~/hy300-work/vendor.img); falha se faltar algum. Ver docs/kernel-6.1.md.
#
# Saída: <dir_de_trabalho>/recovery-marco1.img (+ .sha256). Gravar com
# scripts/flash-test-recovery.sh (roteiro em docs/kernel-6.1.md).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=kernel/lib-kbase.sh
. "$REPO/kernel/lib-kbase.sh"
select_kbase "${KBASE:-ack}"
KSRC="$(cd "${1:-$HOME/hy300-handoff/kernel-hy300-rk3566}" && pwd)"
WORK="${2:-$KWORK_DEFAULT}"
FACTORY="${3:-$HOME/hy300-backup}"
KOUT="${KBUILD_OUT:-$KOUT_DEFAULT}"
KCONFIG_REQS="${KCONFIG_REQS:-$HOME/android/lineage/kernel/configs/u/android-6.1}"
JOBS="${JOBS:-$(nproc)}"
SMOKE="${SMOKE:-1}"
WIFI="${WIFI:-0}"
WIFI_WORK="${WIFI_WORK:-$HOME/hy300-work/wifi}"
WIFI_CREDENTIALS="${WIFI_CREDENTIALS:-$WIFI_WORK/credenciais.conf}"
VENDOR_IMG="${VENDOR_IMG:-$HOME/hy300-work/vendor.img}"

DTB_NAME=rk3566-hy300.dtb
MARK="hy300.test=marco1 panic=10"
# Parâmetros extras do teste, depois da marca. console=tty0 por último põe o log do kernel e o
# do /init na tela (framebuffer); hy300.shutdown_debug=1 troca o fim por reboot -f com log.
EXTRA_CMDLINE="${EXTRA_CMDLINE-console=tty0}"
[[ "$WIFI" == 1 ]] && EXTRA_CMDLINE="${EXTRA_CMDLINE:+$EXTRA_CMDLINE }hy300.wifi=1"
RECOVERY_PART_SIZE=113246208

IMAGE="$KOUT/arch/arm64/boot/Image"
DTB="$KOUT/arch/arm64/boot/dts/rockchip/$DTB_NAME"
INITRAMFS="$WORK/initramfs-marco1.cpio.gz"
WIFI_ROOT="$WORK/wifi-root"
AIC_MODULES=(aic8800_bsp aic8800_fdrv)
OUT="$WORK/recovery-marco1.img"

# Nome neutro no "Linux version": a imagem não deve carregar usuário/máquina de quem compilou.
export KBUILD_BUILD_USER=hy300 KBUILD_BUILD_HOST=build

kmake() {
	make -s -C "$KSRC" O="$1" ARCH=arm64 "${KMAKE_TOOLCHAIN[@]}" -j"$JOBS" "${@:2}"
}

require_factory_recovery() {
	local want got
	want="$(awk '$2 == "recovery.img" || $2 == "./recovery.img" { print $1 }' "$FACTORY/SHA256SUMS")"
	got="$(sha256sum "$FACTORY/recovery.img" | cut -c1-64)"
	[[ -n "$want" && "$want" == "$got" ]] || { echo "recovery.img de fábrica não confere com SHA256SUMS"; exit 1; }
}

build_kernel() {
	echo ">> kernel ($KBASE): $(git -C "$KSRC" rev-parse --abbrev-ref HEAD) $(git -C "$KSRC" rev-parse --short HEAD)"
	mkdir -p "$KOUT"
	kmake "$KOUT" "${KCONFIGS[@]}" >/dev/null 2>&1
	check_android_kconfig "$KOUT/.config" "$KCONFIG_REQS" "$WORK/kconfig-check.txt" \
		"$(kmake "$KOUT" kernelversion)" || exit 1
	kmake "$KOUT" Image modules "rockchip/$DTB_NAME"
}

# Raiz extra do modo Wi-Fi, só em ~/hy300-work: credenciais e firmware nunca vão para o repo.
build_wifi_root() {
	echo ">> modo Wi-Fi: módulos, firmware, wpa_supplicant e rede"
	rm -rf "$WIFI_ROOT"
	python3 "$REPO/tools/wifi_payload.py" build --credentials "$WIFI_CREDENTIALS" \
		--vendor-img "$VENDOR_IMG" --out "$WIFI_ROOT" || exit 1
	mkdir -p "$WIFI_ROOT/lib/modules/aic8800" "$WIFI_ROOT/usr/sbin"
	for module in "${AIC_MODULES[@]}"; do
		"$KSTRIP" --strip-debug -o "$WIFI_ROOT/lib/modules/aic8800/$module.ko" \
			"$(find "$KOUT/drivers/net/wireless/aic8800" -name "$module.ko")"
	done
	"$REPO/kernel/wifi/build-wpa-supplicant.sh" "$WIFI_ROOT/usr/sbin" "$WIFI_WORK/build"
}

build_initramfs() {
	echo ">> initramfs"
	local extra=()
	[[ "$WIFI" == 1 ]] && { build_wifi_root; extra=("$WIFI_ROOT"); }
	"$REPO/kernel/initramfs-test/build.sh" "$KSRC" "$INITRAMFS" "$WORK/initramfs" "${extra[@]}"
}

# O U-Boot de fábrica usa o rk-kernel.dtb do resource.img (seção second) como DT próprio e
# trava com o DT do 6.1. O resource fica o de fábrica; o kernel usa o DT embutido
# (CONFIG_HY300_BUILTIN_DTB) e só copia o /chosen e a memória do DT do U-Boot.
build_resource() {
	echo ">> resource.img"
	python3 "$REPO/tools/rk_resource.py" boot-extract "$FACTORY/recovery.img" "$WORK/resource-fabrica.img" >/dev/null
	cp "$WORK/resource-fabrica.img" "$WORK/resource-marco1.img"
}

# O DT embutido tem o modelo do HY300; o de fábrica não.
require_builtin_dtb() {
	grep -qa 'HY300 Projector' "$1" || { echo "FALHOU: Image sem o DT embutido do HY300"; exit 1; }
}

build_image() {
	echo ">> recovery-marco1.img"
	python3 "$REPO/tools/mkboot.py" build --like "$FACTORY/recovery.img" -o "$OUT" \
		--kernel "$IMAGE" --ramdisk "$INITRAMFS" --second "$WORK/resource-marco1.img" --dtb "$DTB" \
		--append-cmdline "$MARK${EXTRA_CMDLINE:+ $EXTRA_CMDLINE}" --pad-to-like
}

require_same() {
	cmp -s "$1" "$2" || { echo "FALHOU: $3"; exit 1; }
}

# O U-Boot de fábrica troca o próprio DT pelo rk-kernel.dtb do resource e só reconhece o
# eMMC por "snps,dwcmshc-sdhci" (ou rk3588). Sem esse compatible ele perde o eMMC, não lê
# a imagem e trava antes do logo: foi o que aconteceu nos primeiros testes do marco 1.
require_uboot_emmc() {
	grep -qa 'snps,dwcmshc-sdhci' "$1" ||
		{ echo "FALHOU: o eMMC do DTB não tem o compatible que o U-Boot de fábrica conhece"; exit 1; }
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
	require_same "$check/second" "$WORK/resource-fabrica.img" "resource de fábrica"
	require_builtin_dtb "$check/kernel"
	require_uboot_emmc "$check/res/rk-kernel.dtb"
	grep -q "$MARK" "$check/header.json" || { echo "FALHOU: cmdline sem a marca"; exit 1; }
	[[ "$WIFI" == 1 ]] && require_wifi_payload "$check"
	sha256sum "$OUT" | tee "$OUT.sha256"
	echo "ok: $(stat -c %s "$OUT") bytes (partição: $RECOVERY_PART_SIZE)"
}

require_wifi_payload() {
	local listing="$1/initramfs.txt" path
	grep -q 'hy300.wifi=1' "$1/header.json" || { echo "FALHOU: cmdline sem hy300.wifi=1"; exit 1; }
	gzip -dc "$INITRAMFS" | cpio -it --quiet >"$listing"
	for path in etc/wpa_supplicant.conf etc/hy300-wifi.conf usr/sbin/wpa_supplicant \
		lib/modules/aic8800/aic8800_bsp.ko lib/modules/aic8800/aic8800_fdrv.ko \
		lib/firmware/aic8800/fmacfw_8800d80_u02.bin; do
		grep -qx "$path" "$listing" || { echo "FALHOU: initramfs sem $path"; exit 1; }
	done
	rm -f "$listing"
	echo "ok: modo Wi-Fi no initramfs e na cmdline"
}

# Teste de fumaça do /init num kernel com PL011/virtio (build à parte, incremental).
run_smoke() {
	[[ "$SMOKE" == 1 ]] || { echo ">> smoke: pulado (SMOKE=$SMOKE)"; return; }
	command -v qemu-system-aarch64 >/dev/null || { echo ">> smoke: pulado (sem qemu-system-aarch64)"; return; }
	echo ">> smoke (QEMU)"
	local qout="$KOUT-qemu"
	mkdir -p "$qout"
	kmake "$qout" "${KCONFIGS[@]}" >/dev/null 2>&1
	"$KSRC/scripts/kconfig/merge_config.sh" -m -O "$qout" "$qout/.config" \
		"$REPO/kernel/initramfs-test/qemu.config" >/dev/null
	kmake "$qout" olddefconfig >/dev/null
	kmake "$qout" Image
	python3 "$REPO/kernel/initramfs-test/smoke-qemu.py" "$qout/arch/arm64/boot/Image" "$INITRAMFS" \
		"$WORK/qemu" "$FACTORY/misc.img"
}

main() {
	mkdir -p "$WORK"
	require_kbase_tree "$KSRC" || exit 1
	use_kbase_toolchain || exit 1
	require_factory_recovery
	build_kernel
	build_initramfs
	build_resource
	build_image
	verify_image
	run_smoke
}

main
