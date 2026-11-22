# Funções do /init de teste (marco 1). Shell POSIX: roda no busybox do initramfs e no
# /bin/sh do host (tests/test_initramfs_misc.py).
#
# A `misc` começa com o bootloader_message do AOSP (2048 bytes; os 32 primeiros são o
# comando). O Android 12 grava "boot-recovery" ali no `adb reboot recovery`, e o U-Boot
# volta para a recovery enquanto o comando estiver lá. O init de teste apaga só esses
# 2048 bytes e só quando o comando começa com "boot-recovery".
#
# Não mexer em nada além disso: em 0x800 ficam os dados A/B da Rockchip e em 16 KiB um
# BCB legado de fábrica ("boot-recovery --wipe_all") que o U-Boot ignora.

BCB_SIZE=2048
BCB_COMMAND_SIZE=32
MISC_SECTORS=8192
SYSFS_BLOCK=/sys/class/block

read_bcb_command() {
	{ dd if="$1" bs="$BCB_COMMAND_SIZE" count=1 2>/dev/null; echo; } | tr '\000' '\n' | head -n 1
}

is_recovery_command() {
	case "$1" in
	boot-recovery*) return 0 ;;
	esac
	return 1
}

clear_bcb() {
	dd if=/dev/zero of="$1" bs="$BCB_SIZE" count=1 conv=notrunc,fsync 2>/dev/null
}

clear_bcb_if_recovery() {
	[ -e "$1" ] || { echo "misc: $1 não existe"; return 1; }
	bcb_command=$(read_bcb_command "$1")
	is_recovery_command "$bcb_command" || { echo "misc: comando '$bcb_command' mantido"; return 1; }
	clear_bcb "$1" || { echo "misc: falha ao apagar '$bcb_command'"; return 1; }
	sync
	echo "misc: comando '$bcb_command' apagado"
}

find_partition_by_name() {
	for uevent in "${2:-$SYSFS_BLOCK}"/*/uevent; do
		grep -qx "PARTNAME=$1" "$uevent" 2>/dev/null || continue
		basename "$(dirname "$uevent")"
		return 0
	done
	return 1
}

is_misc_size_expected() {
	[ "$(cat "${2:-$SYSFS_BLOCK}/$1/size" 2>/dev/null)" = "$MISC_SECTORS" ]
}

wait_for_partition() {
	remaining=$2
	while :; do
		find_partition_by_name "$1" "$3" && return 0
		[ "$remaining" -gt 0 ] || return 1
		remaining=$((remaining - 1))
		sleep 1
	done
}

# Relatório: cada linha vira um registro no /dev/kmsg, que o console do pstore guarda.
# Linha vazia é descartada; o prefixo permite achar o relatório com grep.
KMSG=/dev/kmsg

send_lines_to_kmsg() {
	while IFS= read -r line; do
		[ -n "$line" ] || continue
		echo "hy300: [$1] $line" >>"${2:-$KMSG}"
	done
}

report_section() {
	section=$1
	target=$2
	shift 2
	"$@" 2>&1 | send_lines_to_kmsg "$section" "$target"
	return 0
}
