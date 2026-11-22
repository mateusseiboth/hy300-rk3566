# Base do kernel do build-marco1.sh (testes em tests/test_kbase.py).
#
#   ack (padrão): kernel Android da Rockchip, branch hy300-ack-6.1 (ACK android14-6.1 com o BSP
#                 da Rockchip, do Lineage-Rockchip). Configs do Android 14 e clang dos
#                 prebuilts do LineageOS (CLANG_DIR).
#   bsp:          BSP Linux develop-6.1, branch hy300-6.1 (marco 1 original). GCC cruzado.
#
# select_kbase define KCONFIGS, KMAKE_TOOLCHAIN, KSTRIP, KOUT_DEFAULT, KWORK_DEFAULT,
# KANDROID, KTREE_MARKERS e CLANG_DIR.
# shellcheck shell=bash disable=SC2034  # variáveis lidas por quem inclui

KBASE_TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../tools" && pwd)"
LINEAGE_CLANG="$HOME/android/lineage/prebuilts/clang/host/linux-x86/clang-r547379"

select_kbase_ack() {
	KCONFIGS=(rockchip_defconfig android-14.config rk3566_hy300.config)
	KMAKE_TOOLCHAIN=(LLVM=1 LLVM_IAS=1)
	KSTRIP=llvm-strip
	KOUT_DEFAULT="$HOME/hy300-work/kbuild-ack-6.1"
	KWORK_DEFAULT="$HOME/hy300-work/marco1-ack"
	KANDROID=1
	KTREE_MARKERS=(kernel/configs/android-14.config arch/arm64/configs/rockchip_defconfig)
	CLANG_DIR="${CLANG_DIR:-$LINEAGE_CLANG}"
}

select_kbase_bsp() {
	KCONFIGS=(rockchip_linux_defconfig rk3566.config rk3566_hy300.config)
	KMAKE_TOOLCHAIN=(CROSS_COMPILE=aarch64-linux-gnu-)
	KSTRIP=aarch64-linux-gnu-strip
	KOUT_DEFAULT="$HOME/hy300-work/kbuild-6.1"
	KWORK_DEFAULT="$HOME/hy300-work/marco1"
	KANDROID=0
	KTREE_MARKERS=(arch/arm64/configs/rockchip_linux_defconfig)
}

select_kbase() {
	KBASE="$1"
	declare -F "select_kbase_$1" >/dev/null || { echo "base do kernel desconhecida: $1 (use ack ou bsp)" >&2; return 1; }
	"select_kbase_$1"
}

# O defconfig Android só existe na árvore ack, e o fragmento sobre ele não serve no BSP Linux.
require_kbase_tree() {
	local tree="$1" marker
	for marker in "${KTREE_MARKERS[@]}"; do
		[[ -e "$tree/$marker" ]] || { echo "FALHOU: $tree não é a base $KBASE (falta $marker)" >&2; return 1; }
	done
	[[ "$KANDROID" == 1 || ! -e "$tree/kernel/configs/android-14.config" ]] ||
		{ echo "FALHOU: $tree não é a base $KBASE (é a árvore Android; use KBASE=ack)" >&2; return 1; }
}

use_kbase_toolchain() {
	[[ "$KANDROID" == 1 ]] || return 0
	[[ -x "$CLANG_DIR/bin/clang" ]] || { echo "FALHOU: clang ausente em $CLANG_DIR/bin (CLANG_DIR)" >&2; return 1; }
	export PATH="$CLANG_DIR/bin:$PATH"
}

# Requisitos de config do Android (kernel/configs/u/android-6.1, FCM 8). Só na base ack.
check_android_kconfig() {
	local dotconfig="$1" reqs="$2" report="$3" version="$4"
	[[ "$KANDROID" == 1 ]] || { echo ">> kconfig Android: pulado (base $KBASE)"; return 0; }
	[[ -d "$reqs" ]] || { echo ">> kconfig Android: pulado (sem $reqs)"; return 0; }
	python3 -I "$KBASE_TOOLS/kconfig_check.py" "$reqs" "$dotconfig" --kernel-version "$version" >"$report" ||
		{ cat "$report"; echo "FALHOU: o .config não atende $reqs (relatório em $report)"; return 1; }
	echo ">> kconfig Android: $(tail -n 1 "$report") contra $reqs"
}
