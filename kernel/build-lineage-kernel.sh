#!/usr/bin/env bash
# Kernel do LineageOS do HY300 como prebuilt da árvore do aparelho (device/txcz/hy300).
#
# Compila um commit FIXO do branch hy300-ack-6.1 a partir de um `git archive` (não mexe no
# checkout do kernel, que outro trabalho usa), confere os requisitos de config do Android
# (FCM 8) e instala na árvore: prebuilt/Image.gz (DT do HY300 embutido), prebuilt/dtb/,
# prebuilt/resource.img (de FÁBRICA, tirado do boot.img do aparelho), prebuilt/modules/*.ko
# (GPU: Panfrost e dependências) e prebuilt/VERSION. Nada disso vai para o git.
#
# Uso: kernel/build-lineage-kernel.sh [árvore_do_aparelho]
#   padrão: ~/android/lineage/device/txcz/hy300
# Variáveis: KREF (padrão hy300-ack-6.1), KSRC_GIT (padrão ~/hy300-handoff/kernel-hy300-rk3566),
#            LKWORK (padrão ~/hy300-work/lineage-kernel), FACTORY (padrão ~/hy300-backup),
#            KCONFIG_REQS (padrão ~/android/lineage/kernel/configs/u/android-6.1),
#            LK_MODULES (padrão "drm_shmem_helper gpu-sched panfrost"), JOBS (padrão 12).
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
read -r -a LK_MODULES <<<"${LK_MODULES:-drm_shmem_helper gpu-sched panfrost}"
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

main() {
	use_kbase_toolchain || exit 1
	export_source
	require_kbase_tree "$KSRC" || exit 1
	build_kernel
	collect_modules
	install_prebuilts
	cat "$DEVICE_TREE/prebuilt/VERSION"
}

main
