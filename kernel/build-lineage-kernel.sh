#!/usr/bin/env bash
# Kernel do LineageOS do HY300 como prebuilt da árvore do aparelho (device/txcz/hy300).
#
# Compila um commit FIXO do branch hy300-ack-6.1 a partir de um `git archive` (não mexe no
# checkout do kernel, que outro trabalho usa), confere os requisitos de config do Android
# (FCM 8) e instala na árvore: prebuilt/Image.gz (DT do HY300 embutido), prebuilt/dtb/,
# prebuilt/resource.img (de FÁBRICA, tirado do boot.img do aparelho), prebuilt/modules/*.ko
# (GPU: Panfrost e dependências; Wi-Fi: aic8800_bsp e aic8800_fdrv), prebuilt/VERSION e, se o
# vendor.img de fábrica existir, prebuilt/firmware/aic8800 (firmware da AICSemi, conferido por
# MD5 pelo tools/wifi_payload.py). Nada disso vai para o git.
#
# Uso: kernel/build-lineage-kernel.sh [árvore_do_aparelho]
#   padrão: ~/android/lineage/device/txcz/hy300
# Variáveis: KREF (padrão hy300-ack-6.1), KSRC_GIT (padrão ~/hy300-handoff/kernel-hy300-rk3566),
#            LKWORK (padrão ~/hy300-work/lineage-kernel), FACTORY (padrão ~/hy300-backup),
#            KCONFIG_REQS (padrão ~/android/lineage/kernel/configs/u/android-6.1),
#            LK_MODULES (padrão "drm_shmem_helper gpu-sched panfrost aic8800_bsp aic8800_fdrv aic8800_btlpm"),
#            VENDOR_IMG (padrão ~/hy300-work/vendor.img), JOBS (padrão 12).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=kernel/lib-kbase.sh
. "$REPO/kernel/lib-kbase.sh"
select_kbase ack

DEVICE_TREE="$(cd "${1:-$HOME/android/lineage/device/txcz/hy300}" && pwd)"
KREF="${KREF:-hy300-ack-6.1}"
KSRC_GIT="${KSRC_GIT:-$HOME/hy300-handoff/kernel-hy300-rk3566}"
LKWORK="${LKWORK:-$HOME/hy300-work/lineage-kernel}"
FACTORY="${FACTORY:-$HOME/hy300-backup}"
KCONFIG_REQS="${KCONFIG_REQS:-$HOME/android/lineage/kernel/configs/u/android-6.1}"
read -r -a LK_MODULES <<<"${LK_MODULES:-drm_shmem_helper gpu-sched panfrost aic8800_bsp aic8800_fdrv aic8800_btlpm}"
VENDOR_IMG="${VENDOR_IMG:-$HOME/hy300-work/vendor.img}"
JOBS="${JOBS:-12}"
DTB_NAME=rk3566-hy300.dtb

export KBUILD_BUILD_USER=hy300 KBUILD_BUILD_HOST=build

COMMIT="$(git -C "$KSRC_GIT" rev-parse --short=12 "$KREF^{commit}")"
KSRC="$LKWORK/src-$COMMIT"
KOUT="$LKWORK/out-$COMMIT"
MODULES_DIR="$LKWORK/modules-$COMMIT"

kmake() {
	nice -n 10 make -s -C "$KSRC" O="$KOUT" ARCH=arm64 "${KMAKE_TOOLCHAIN[@]}" -j"$JOBS" "$@"
}

export_source() {
	[[ -e "$KSRC/Makefile" ]] && return 0
	echo ">> fonte: $KREF = $COMMIT (git archive)"
	rm -rf "$KSRC.tmp" && mkdir -p "$KSRC.tmp"
	git -C "$KSRC_GIT" archive "$COMMIT" | tar -x -C "$KSRC.tmp"
	mv "$KSRC.tmp" "$KSRC"
}

build_kernel() {
	echo ">> kernel $COMMIT (${KCONFIGS[*]})"
	mkdir -p "$KOUT"
	kmake "${KCONFIGS[@]}" >/dev/null
	check_android_kconfig "$KOUT/.config" "$KCONFIG_REQS" "$LKWORK/kconfig-check-$COMMIT.txt" \
		"$(kmake kernelversion)"
	kmake Image modules "rockchip/$DTB_NAME"
}

# Tecla do gpio-keys no pino de fábrica e fora das saídas de LED (tests/test_dt_gpio_irq.py), e os
# nós do motor de foco, acelerômetro, Bluetooth e HDMI-in (tests/test_port_dt_hardware.py).
check_dt_keys() {
	local dtb="$KOUT/arch/arm64/boot/dts/rockchip/$DTB_NAME"
	python3 -I "$REPO/tools/dt_gpio_irq.py" check "$dtb" --factory "$REPO/device-tree/rk3566-hy300-txcz.dtb"
	HY300_PORT_DTB="$dtb" python3 -I -m unittest discover -s "$REPO/tests" -p test_port_dt_hardware.py
}

collect_modules() {
	rm -rf "$MODULES_DIR" && mkdir -p "$MODULES_DIR"
	local module path
	for module in "${LK_MODULES[@]}"; do
		path="$(find "$KOUT" -name "$module.ko" -print -quit)"
		[[ -n "$path" ]] || { echo "FALHOU: módulo $module.ko não foi gerado" >&2; exit 1; }
		"$KSTRIP" --strip-debug -o "$MODULES_DIR/$module.ko" "$path"
	done
}

install_prebuilts() {
	python3 -I "$REPO/tools/lineage_prebuilt.py" install --image "$KOUT/arch/arm64/boot/Image" \
		--dtb "$KOUT/arch/arm64/boot/dts/rockchip/$DTB_NAME" --factory-boot "$FACTORY/boot.img" \
		--out "$DEVICE_TREE/prebuilt" --kernel-ref "$KREF $COMMIT" --modules-dir "$MODULES_DIR"
}

install_wifi_firmware() {
	local dest="$DEVICE_TREE/prebuilt/firmware/aic8800"
	[[ -f "$VENDOR_IMG" ]] || { echo ">> firmware do Wi-Fi: pulado (sem $VENDOR_IMG)"; return 0; }
	rm -rf "$dest"
	python3 -I "$REPO/tools/wifi_payload.py" firmware --vendor-img "$VENDOR_IMG" --out "$dest"
}

main() {
	use_kbase_toolchain || exit 1
	export_source
	require_kbase_tree "$KSRC" || exit 1
	build_kernel
	check_dt_keys
	collect_modules
	install_prebuilts
	install_wifi_firmware
	cat "$DEVICE_TREE/prebuilt/VERSION"
}

main
