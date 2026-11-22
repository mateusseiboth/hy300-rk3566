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

## Kernel 6.1 (marco 1)

Branch `hy300-6.1` do `kernel-hy300-rk3566`: `rk3566-hy300.dts` portado para o BSP
`develop-6.1` e o fragmento `rk3566_hy300.config`. Detalhes, diferenças do DT, pendências e o
roteiro de teste em [`../docs/kernel-6.1.md`](../docs/kernel-6.1.md).

| Arquivo | Conteúdo |
|---|---|
| `build-marco1.sh` | monta do zero kernel, DTB, initramfs e `recovery-marco1.img`, e confere a imagem |
| `initramfs-test/init` | `/init` de teste: limpa o `boot-recovery` da `misc`, relatório no pstore, `reboot -f` em ~20 s |
| `initramfs-test/hy300-test.sh` | funções do init (testadas em `tests/test_initramfs_misc.py`) |
| `initramfs-test/build.sh` | busybox estático (musl, aarch64) compilado do fonte e o cpio |
| `initramfs-test/smoke-qemu.py`, `qemu.config` | teste de fumaça do init num 6.1 no QEMU virt |
| `reboot-recovery/` | binário estático que reinicia para a recovery só pelo registrador de reboot-mode, sem BCB (usado por `scripts/reboot-to-test-slot.sh`) |
| `lib-musl.sh` | baixa e compila o musl (comum ao initramfs e ao `reboot-recovery`) |
| `initramfs-test/hy300-wifi.sh` | funções do modo Wi-Fi do init (`hy300.wifi=1`; testadas em `tests/test_initramfs_wifi.py`) |
| `wifi/build-wpa-supplicant.sh` | `wpa_supplicant` e `wpa_cli` estáticos (musl, libnl, nl80211) para o modo Wi-Fi |

## Próximos passos

1. Gravar e rodar o marco 1 com o usuário presente (roteiro em `../docs/kernel-6.1.md`).
2. Ligar de volta, um por vez, o que o marco 1 deixou de fora: DVFS, GPU, RK628.
3. Driver que não existe no 6.1: motor de foco (`/sys/class/motor_cc`). O Wi-Fi AIC8800 já
   está na árvore (`drivers/net/wireless/aic8800`); falta o teste no aparelho
   (`docs/kernel-6.1.md`, "Wi-Fi no 6.1").
