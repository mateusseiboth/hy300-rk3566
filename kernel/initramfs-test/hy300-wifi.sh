# Funções do modo Wi-Fi do /init de teste (hy300.wifi=1). Shell POSIX: roda no busybox do
# initramfs e no /bin/sh do host (tests/test_initramfs_wifi.py).
#
# Sequência (quem chama é o /init): carregar aic8800_bsp (com o caminho do firmware) e
# aic8800_fdrv, esperar a interface sem fio, subir o wpa_supplicant, esperar a associação,
# pôr o IP fixo e abrir o telnetd. Um prazo em arquivo decide quando reiniciar; existir o
# arquivo "ficar" desliga o reinício automático.

# Caminhos usados pelo /init (e criados pelo build com WIFI=1).
# shellcheck disable=SC2034
WIFI_MODULE_DIR=/lib/modules/aic8800
WIFI_FIRMWARE_DIR=/lib/firmware/aic8800
WIFI_WPA_CONF=/etc/wpa_supplicant.conf
WIFI_NET_CONF=/etc/hy300-wifi.conf
WIFI_WPA_LOG=/tmp/wpa_supplicant.log
WIFI_WPA_CTRL=/var/run/wpa_supplicant
WIFI_DEADLINE_FILE=/tmp/hy300-prazo
WIFI_STAY_FILE=/tmp/hy300-ficar
WIFI_TELNET_PORT=23

is_wifi_mode() {
	grep -qw 'hy300.wifi=1' "${1:-/proc/cmdline}"
}

# Valor numérico de "nome=N" na cmdline; o padrão se faltar ou não for número.
read_cmdline_number() {
	value=$(awk -v key="$1=" '{ for (i = 1; i <= NF; i++) if (index($i, key) == 1) v = substr($i, length(key) + 1) } END { print v }' "${3:-/proc/cmdline}")
	case "$value" in
	'' | *[!0-9]*) echo "$2" ;;
	*) echo "$value" ;;
	esac
}

load_wifi_modules() {
	insmod "$1/aic8800_bsp.ko" "aic_fw_path=$2" || { echo "insmod aic8800_bsp falhou"; return 1; }
	insmod "$1/aic8800_fdrv.ko" || { echo "insmod aic8800_fdrv falhou"; return 1; }
}

unload_wifi_modules() {
	rmmod aic8800_fdrv 2>/dev/null
	rmmod aic8800_bsp 2>/dev/null
	return 0
}

# Religar o chip sem tirar da tomada. Desligar o host SDIO (unbind do dwmmc) faz o
# mmc-pwrseq-simple pôr o WL_REG_ON em 0 e cortar o clock de 32 kHz; o bind religa e o núcleo
# MMC enumera o cartão de novo. O pulso no boot é curto e não destrava um chip que falhou.
WIFI_SDIO_HOST_ADDR=fe2c0000
WIFI_SDIO_VENDOR=0xc8a1
WIFI_PLATFORM_DEVICES=/sys/bus/platform/devices
WIFI_SDIO_DRIVER=/sys/bus/platform/drivers/dwmmc_rockchip
WIFI_SDIO_DEVICES=/sys/bus/sdio/devices
WIFI_POWER_OFF_SECONDS=2
WIFI_CARD_WAIT=10

# O nome do nó muda entre as árvores (dwmmc@fe2c0000 no ACK, mmc@fe2c0000 no BSP).
find_sdio_host() {
	for dev in "$WIFI_PLATFORM_DEVICES/$1".*; do
		[ -e "$dev" ] || continue
		basename "$dev"
		return 0
	done
	return 1
}

has_wifi_card() {
	for vendor in "$WIFI_SDIO_DEVICES"/*/vendor; do
		[ "$(cat "$vendor" 2>/dev/null)" = "$WIFI_SDIO_VENDOR" ] && return 0
	done
	return 1
}

wait_for_wifi_card() {
	remaining=$1
	while :; do
		has_wifi_card && return 0
		[ "$remaining" -gt 0 ] || return 1
		remaining=$((remaining - 1))
		sleep 1
	done
}

cycle_wifi_chip() {
	echo "$1" 2>/dev/null >"$WIFI_SDIO_DRIVER/unbind" || { echo "unbind de $1 falhou"; return 1; }
	sleep "$2"
	echo "$1" 2>/dev/null >"$WIFI_SDIO_DRIVER/bind" || { echo "bind de $1 falhou"; return 1; }
}

recover_wifi_chip() {
	unload_wifi_modules
	host=$(find_sdio_host "$WIFI_SDIO_HOST_ADDR") || { echo "host SDIO $WIFI_SDIO_HOST_ADDR não encontrado"; return 1; }
	cycle_wifi_chip "$host" "$WIFI_POWER_OFF_SECONDS" || return 1
	wait_for_wifi_card "$WIFI_CARD_WAIT" || { echo "o chip não voltou ao barramento SDIO em $WIFI_CARD_WAIT s"; return 1; }
}

# Estado do host SDIO para o relatório: debugfs do dw_mmc, contagem de interrupções e o
# WL_REG_ON (GPIO2_B1 = gpio-73, "reset" do mmc-pwrseq).
dump_sdio_state() {
	for file in ios regs; do
		sed "s/^/$file: /" "/sys/kernel/debug/mmc1/$file" 2>/dev/null
	done
	grep "$WIFI_SDIO_HOST_ADDR" /proc/interrupts
	grep "gpio-73 " /sys/kernel/debug/gpio 2>/dev/null
	return 0
}

find_wireless_iface() {
	for dir in "${1:-/sys/class/net}"/*; do
		[ -d "$dir/wireless" ] || [ -e "$dir/phy80211" ] || continue
		basename "$dir"
		return 0
	done
	return 1
}

wait_for_wireless_iface() {
	remaining=$1
	while :; do
		find_wireless_iface "$2" && return 0
		[ "$remaining" -gt 0 ] || return 1
		remaining=$((remaining - 1))
		sleep 1
	done
}

start_wpa_supplicant() {
	wpa_supplicant -B -D nl80211 -i "$1" -c "$2" -f "$3"
}

read_wpa_state() {
	wpa_cli -p "$WIFI_WPA_CTRL" -i "$1" status 2>/dev/null | sed -n 's/^wpa_state=//p'
}

# Espera o wpa_state=COMPLETED; se o tempo acabar, imprime o último estado.
wait_for_wpa_completed() {
	remaining=$2
	while :; do
		state=$(read_wpa_state "$1")
		[ "$state" = COMPLETED ] && return 0
		[ "$remaining" -gt 0 ] || { echo "${state:-sem resposta do wpa_supplicant}"; return 1; }
		remaining=$((remaining - 1))
		sleep 1
	done
}

# O arquivo de rede é gerado e validado no build (tools/wifi_payload.py): só atribuições.
configure_static_ip() {
	# shellcheck source=/dev/null
	. "$2"
	ip link set lo up
	ip addr add "$WIFI_ADDRESS" dev "$1" || return 1
	ip link set "$1" up || return 1
	ip route add default via "$WIFI_GATEWAY" dev "$1" || return 1
	echo "nameserver $WIFI_DNS" >"${3:-/etc/resolv.conf}"
}

announce_ip() {
	arping -U -c 2 -I "$1" "$2" >/dev/null 2>&1
}

read_iface_ip() {
	ip -4 -o addr show dev "$1" | awk '{ split($4, a, "/"); print a[1]; exit }'
}

start_telnetd() {
	mkdir -p /dev/pts
	mount -t devpts devpts /dev/pts 2>/dev/null
	telnetd -p "$1" -l /bin/sh
}

# Prazo em segundos de uptime, num arquivo: o modo Wi-Fi encurta o prazo quando algo falha.
read_deadline() {
	value=$(cat "$1" 2>/dev/null)
	case "$value" in
	'' | *[!0-9]*) echo 0 ;;
	*) echo "$value" ;;
	esac
}

shorten_deadline() {
	[ "$(read_deadline "$1")" -gt 0 ] && [ "$(read_deadline "$1")" -le "$2" ] && return 0
	echo "$2" >"$1"
}

is_deadline_reached() {
	[ -e "$3" ] && return 1
	[ "$1" -ge "$2" ]
}

build_countdown() {
	[ -e "$3" ] && { echo "sem reinício automático"; return; }
	echo "reinicia em $(($2 - $1)) s"
}

build_wifi_status() {
	echo "IP $1, telnet $1 $WIFI_TELNET_PORT; $(build_countdown "$2" "$3" "$4")"
}
