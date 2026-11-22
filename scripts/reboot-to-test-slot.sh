#!/usr/bin/env bash
# Reinicia o aparelho direto para o slot de teste (partição recovery) sem gravar nada na misc.
#
# Usa o kernel/reboot-recovery: sync, remonta só-leitura (sysrq 'u') e
# reboot(RESTART2, "recovery"). O kernel de fábrica grava 0x5242c303 no PMU_GRF; o U-Boot
# sobe a recovery uma vez e volta o registrador para "normal". Se o kernel de teste travar,
# tirar da tomada apaga o registrador e o aparelho volta ao Android de fábrica.
#
# Uso: ./reboot-to-test-slot.sh [--dry-run]
#   --dry-run: manda o binário e só mostra o que ele faria, sem reiniciar.
# Variáveis: REBOOT_BIN (binário, padrão ~/hy300-work/marco1/reboot-recovery/reboot-recovery),
#            TEST_IMAGE (imagem que deve estar na recovery, padrão
#            ~/hy300-work/marco1/recovery-marco1.img).
set -euo pipefail

BIN="${REBOOT_BIN:-$HOME/hy300-work/marco1/reboot-recovery/reboot-recovery}"
IMG="${TEST_IMAGE:-$HOME/hy300-work/marco1/recovery-marco1.img}"
DEST=/data/local/tmp/hy300-reboot-recovery
MISC=/dev/block/by-name/misc
PART=/dev/block/by-name/recovery
MODE="${1:-}"

fail() { echo "$1"; exit 1; }

require_binary() {
	[[ -f "$BIN" ]] || fail "binário não encontrado: $BIN (kernel/reboot-recovery/build.sh)"
	file "$BIN" | grep -q 'ARM aarch64.*statically linked' || fail "$BIN não é aarch64 estático"
}

connect_root() {
	adb root >/dev/null
	sleep 3
	adb wait-for-device
	[[ "$(adb shell uname -m | tr -d '\r')" == aarch64 ]] || fail "kernel do aparelho não é arm64"
}

# Com um comando no BCB, o U-Boot iria pela misc (e ficaria preso nela): não seguir.
require_empty_bcb() {
	local command
	command="$(adb shell "dd if=$MISC bs=32 count=1 2>/dev/null | tr -d '\\000'" | tr -d '\r')"
	[[ -z "$command" ]] || fail "a misc tem o comando '$command' no BCB; limpe antes de seguir"
}

# A recovery precisa ter a imagem de teste, senão o reboot sobe outra coisa.
require_test_image() {
	local want got
	[[ "$MODE" == --dry-run ]] && return
	want="$(sha256sum "$IMG" | cut -c1-64)"
	got="$(adb shell "sha256sum $PART" | cut -c1-64)"
	[[ "$got" == "$want" ]] || fail "a recovery não tem $(basename "$IMG") ($got); grave com flash-test-recovery.sh"
}

push_binary() {
	adb push "$BIN" "$DEST" >/dev/null
	adb shell "chmod 755 $DEST"
	adb shell "$DEST --dry-run"
}

main() {
	require_binary
	connect_root
	require_empty_bcb
	require_test_image
	push_binary
	[[ "$MODE" == --dry-run ]] && { echo "dry-run: nada reiniciado"; return; }
	echo ">> reiniciando para a recovery (a conexão adb cai agora)"
	adb shell "$DEST" || true
}

main
