#!/usr/bin/env bash
# Compila o reboot-recovery estático para aarch64 com musl. O binário não vai para o repo.
# O kernel de fábrica é arm64, então um binário aarch64 estático roda mesmo com o
# userspace Android de 32 bits.
#
# Uso: build.sh [saida] [dir_de_trabalho]
#   saida:           padrão ~/hy300-work/marco1/reboot-recovery/reboot-recovery
#   dir_de_trabalho: onde fica o musl; padrão ~/hy300-work/marco1/initramfs (o mesmo do
#                    initramfs de teste, que já compila o musl)
# Testes: python3 -m unittest tests.test_reboot_recovery (unidade no host e strace no qemu-user)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$HOME/hy300-work/marco1/reboot-recovery/reboot-recovery}"
WORK="${2:-$HOME/hy300-work/marco1/initramfs}"
CROSS="${CROSS_COMPILE:-aarch64-linux-gnu-}"
JOBS="${JOBS:-$(nproc)}"
DL="$WORK/dl"
SYSROOT="$WORK/sysroot"

# shellcheck source=kernel/lib-musl.sh
. "$HERE/../lib-musl.sh"

main() {
	mkdir -p "$WORK" "$(dirname "$OUT")"
	build_musl
	REALGCC="${CROSS}gcc" "$SYSROOT/bin/musl-gcc" -static -Os -std=c11 -D_GNU_SOURCE \
		-Wall -Wextra -Werror -o "$OUT" "$HERE/main.c" "$HERE/reboot_recovery.c"
	"${CROSS}strip" "$OUT"
	echo "ok $OUT ($(stat -c %s "$OUT") bytes)"
	sha256sum "$OUT"
}

main
