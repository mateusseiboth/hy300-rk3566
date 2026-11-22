# Material para kernel próprio

Kernel de fábrica: `Linux 4.19.232 #1107 SMP PREEMPT Thu Jan 18 18:07:36 CST 2024` (BSP Rockchip,
placa de referência *RK3566 BOX DEMO V10*). Userspace Android 32 bits, kernel arm64.

| Arquivo | Conteúdo |
|---|---|
| `config-4.19.232-txcz` | `.config` exato (`/proc/config.gz`) |
| `version.txt` | `/proc/version` (toolchain usada) |
| `dmesg-boot.txt` | dmesg de um boot completo — **sanitizado** (serial, MACs, IPs, SSID; spam `AICWFDBG` removido) |
| `vendor-modules.txt` | `modinfo` dos `.ko` em `/vendor/lib/modules` + `modules.load` |
| `vendor-firmware-list.txt` | firmwares em `/vendor/etc/firmware` |
| `proc-cpuinfo-iomem-interrupts.txt` | `/proc/cpuinfo` (sem serial), `/proc/iomem`, `/proc/interrupts` |

Device tree: ver [`../device-tree/`](../device-tree/) (`*-live.dts` = DT após fixups do U-Boot,
`board-nodes.dts` = só os nós específicos da placa).

## Hardware relevante

| Bloco | Driver / nó | Observação |
|---|---|---|
| Painel | `simple-panel` LVDS, **1024×600** @ ~40,2 MHz, 217×136 mm | Android renderiza 1280×720 e o HWC escala para 1024×600 |
| Brilho do LED | `pwm-backlight` | |
| Wi-Fi/BT | AIC8800 (`aic8800_bsp.ko`, `aic8800_fdrv.ko`, `aic8800_btlpm.ko`), `wlan-platdata` | fora da árvore; DT também prevê Seekwave SV6160, RTL8723CS/8821CS/8822BS, BCMDHD |
| GPU | `mali_kbase.ko` (Bifrost G52) | módulo do vendor |
| HDMI-in | RK628 `rockchip,rk628-csi-v4l2` → rkcif/rkisp | I²S `fe430000` para o áudio |
| Áudio | `rockchip,dummy-codec` + `simple-audio-card` (I²S `fe410000`), `linux,spdif-dit` | |
| Foco | `rk_motor` / `usb-cam-gpio` → `/sys/class/motor_cc` | ver `../reverse-engineering/libfocus/` |
| Keystone auto | `qmi8658_acc`/`qmi8658_gyro` (alternativas `gs_sc7a20`, `gs_mma7660`) | |
| Ventoinha/LEDs | `gpio-leds` (`Fan`, `Fan_h`, `LED_CRL`, `Lcd_power`) | |
| IR | `rockchip,remotectl-pwm` (keymap no DT; foco pelo controle tratado no kernel) | |
| Console | `rockchip,fiq-debugger` → `ttyFIQ0` (UART2 `fe660000`, 1500000 8N1) | |

## Próximos passos

1. Fonte: kernel BSP Rockchip 4.19 (ex.: `rockchip-linux/kernel` branch `develop-4.19`) +
   `.config` acima; os drivers `rk_motor`/`usb-cam-gpio`, sensores `qmi8658` e partes do
   `remotectl` da TXCZ provavelmente não são públicos (GPL: dá para pedir o fonte ao fabricante).
2. Validar boot com `boot.img` novo mantendo ramdisk e `resource.img` (DTB) originais.
3. Mainline: portar `board-nodes.dts` para um `rk3566-hy300.dts` sobre `rk3566.dtsi` upstream.
