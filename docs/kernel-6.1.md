# Kernel 6.1: marco 1

Primeiro boot do kernel BSP Rockchip `develop-6.1` no HY300, pela partição `recovery`. O boot
normal continua pela `boot`, com o Android de fábrica. O kernel de teste sobe um initramfs
mínimo que apaga o `boot-recovery` da `misc`, escreve um relatório no log e reinicia sozinho
em cerca de 20 s. O log é lido depois, já no Android, em `/sys/fs/pstore/console-ramoops-0`.

Estado em 22/11/2026: **passou no aparelho** (quinto boot). O 6.1 sobe com o próprio DT,
acha o eMMC e a `misc`, escreve o relatório no pstore e reinicia pelo sysrq `b` aos 20 s. O
Android de fábrica volta sozinho, com Wi-Fi. Ver "Resultado no aparelho".

| Item | Onde |
|---|---|
| DT, Makefile e fragmento de config | branch `hy300-6.1` do `kernel-hy300-rk3566`, commit `8b5abca` sobre `develop-6.1` `77168c8d5ab8` (6.1.172) |
| Script que monta tudo | `kernel/build-marco1.sh` |
| initramfs de teste | `kernel/initramfs-test/` (`init`, `hy300-test.sh`, `build.sh`) |
| Testes | `tests/test_initramfs_misc.py`, `tests/test_dtdiff.py`, `tests/test_dtnorm.py`, `kernel/initramfs-test/smoke-qemu.py` |
| Imagem | `~/hy300-work/marco1/recovery-marco1.img` (fora do repo) |
| Wi-Fi (AIC8800D80) | commits `2b227eb`, `53fa34e` e `12e46e1` do `hy300-6.1`; modo `hy300.wifi=1` do `/init`; ver "Wi-Fi no 6.1" |

## Como reproduzir

Pacotes no Fedora:

```bash
sudo dnf install gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu make flex bison bc \
    openssl-devel elfutils-libelf-devel python3 curl util-linux
# opcionais: teste de fumaça e testes com o busybox de verdade
sudo dnf install qemu-system-aarch64-core qemu-user-static ShellCheck
```

Kernel:

```bash
cd ~/hy300-handoff/kernel-hy300-rk3566
git fetch origin hy300-6.1 && git checkout hy300-6.1
```

Tudo de uma vez (kernel, DTB, initramfs, resource.img, imagem, conferência e QEMU):

```bash
kernel/build-marco1.sh            # fonte, trabalho e backup nos caminhos padrão
SMOKE=0 kernel/build-marco1.sh    # sem o teste no QEMU
```

O script confere o `recovery.img` de fábrica contra `~/hy300-backup/SHA256SUMS` antes de usar.
No fim ele desmonta a imagem gerada e compara cada seção com o arquivo de origem: kernel,
ramdisk, seção dtb, `rk-kernel.dtb` dentro do resource e a marca na cmdline.

Resultado do build de 22/11:

| Arquivo | Tamanho |
|---|---|
| `Image` (6.1.172-hy300) | 40.243.712 bytes |
| `rk3566-hy300.dtb` | 168.061 bytes |
| `initramfs-marco1.cpio.gz` | 739.179 bytes |
| `resource-marco1.img` | 2.985.984 bytes |
| `recovery-marco1.img` | 113.246.208 bytes, igual à partição; 44,1 MB de dados e o resto zeros |

SHA-256 da imagem: `eeaf7352d31eeeeba83530b852cc1808addebbb05e17377e48980983aaf44434`. O
busybox leva a data do build, então outro build dá outro hash. O `build-marco1.sh` grava o
hash do build atual em `recovery-marco1.img.sha256`.

Testes no host:

```bash
python3 -m unittest discover -s tests               # mkboot, initramfs, dtdiff
~/hy300-work/venv-dt/bin/python -m unittest tests.test_dtnorm   # precisa da lib fdt
```

Com o busybox aarch64 já compilado e o binfmt do qemu-aarch64 registrado, os testes do
initramfs rodam duas vezes: no `/bin/sh` do host e no shell do próprio busybox, com um PATH
que só tem os applets dele.

## Toolchain

GCC 16.2.1 cruzado do Fedora (`gcc-aarch64-linux-gnu`). O SDK Linux da Rockchip para o 6.1 usa
GCC 10.3, então GCC é o compilador que o branch espera. O clang 23 do sistema estaria muito à
frente do clang 17 usado no Android para o 6.1. O pacote do Fedora é reproduzível com um
`dnf install` e não depende de toolchain baixada de espelho.

O kernel compilou sem nenhum aviso. Mesmo assim o fragmento desliga `CONFIG_WERROR`, que vem
ligado no `rockchip_linux_defconfig`: um aviso novo de um GCC mais novo não deve parar o build.
Não foi preciso nenhum `HOSTCFLAGS` (o 6.1 já compila com OpenSSL 3).

O busybox precisou de dois contornos, os dois no `build.sh` e sem tocar no fonte:

- O GCC 16 sempre linka `-latomic_asneeded`, e o cross do Fedora não traz a libatomic do alvo.
  O busybox não usa a libatomic, então o script cria um `libatomic_asneeded.a` vazio no sysroot.
- O `SHA*_HWACCEL` do busybox 1.37 só compila em x86 e fica desligado. `TC` também.

A libc é o musl 1.2.5, compilado do fonte com o mesmo GCC. Os headers do Linux saem da própria
árvore do kernel (`make headers_install`). Os tarballs são baixados e conferidos por SHA-256.

## Config

`arch/arm64/configs/rk3566_hy300.config` segue o padrão do branch: um fragmento sobre o defconfig.

```bash
make ARCH=arm64 rockchip_linux_defconfig rk3566.config rk3566_hy300.config
```

| Opção | Por quê |
|---|---|
| `PSTORE`, `PSTORE_RAM`, `PSTORE_CONSOLE`, `PSTORE_PMSG`, compressão deflate | log do boot de teste guardado na RAM, no formato que o 4.19 de fábrica lê |
| `DEVTMPFS`, `BLK_DEV_INITRD`, `RD_GZIP` | initramfs vindo da seção ramdisk, com `/dev` |
| `KEXEC` | trocar de kernel nos próximos marcos sem regravar a recovery |
| `PANIC_TIMEOUT=10`, `PANIC_ON_OOPS`, softlockup e hung task com panic | travamento detectável vira reboot quente |
| `DTC_SYMBOLS` | DTB com `__symbols__`, que o overlay da `recovery_dtbo` precisa |
| sem `CPU_FREQ`, DMC e bus devfreq, Mali e NPU | primeiro boot sem DVFS: CPU, DDR e barramentos ficam como o U-Boot deixou |
| `LOCALVERSION=-hy300`, `DEBUG_INFO_NONE` | nome do kernel e build mais rápido |

`FIQ_DEBUGGER` (com `TRUST_ZONE`), `OPTEE` e `ROCKCHIP_DEBUG` ficam ligados, como no 4.19 de
fábrica.

## Onde o U-Boot pega o DTB

O U-Boot de fábrica (`2017.09-gf21494d #txcz`) lê o `rk-kernel.dtb` do resource.img (seção
second) da partição que vai bootar, **passa a usá-lo como DT próprio** (eMMC, display, logo) e o
entrega ao kernel. A seção dtb do header v2 não é usada para isso.

Ele não funciona com o DT do 6.1: trava antes do logo, com o LED azul fixo e o botão de energia
sem resposta, e só volta tirando da tomada. Uma causa certa é o eMMC: este U-Boot só reconhece
o controlador por `snps,dwcmshc-sdhci` (ou `rockchip,rk3588-dwcmshc`), e o 6.1 usa
`rockchip,rk3568-dwcmshc`, `rockchip,dwcmshc-sdhci`. Corrigido isso, ainda travou; o resto não
foi isolado.

Solução adotada: o resource leva o **DT de fábrica** (o U-Boot segue como sempre, com logo) e o
kernel usa o **DT embutido** (`CONFIG_HY300_BUILTIN_DTB`,
`drivers/soc/rockchip/hy300-builtin-dtb.c`). No começo do `setup_machine_fdt` ele copia do DT
do U-Boot o `/chosen` inteiro, os nós `device_type = "memory"` (já sem as áreas do TF-A e do
OP-TEE) e as entradas `/memreserve/`. Se algo falhar, segue com o DT do bootloader e registra
`hy300: DT embutido falhou`. O log mostra `hy300: usando o DT embutido` e o modelo
`HY300 Projector (RK3566, TXCZ y356tx)`. O `build-marco1.sh` confere as duas coisas: resource
de fábrica e Image com o DT do HY300.

Perde-se o que o U-Boot só ajusta no DT dele, como o endereço do logo em `drm-logo` (a tela
apaga entre o logo e o kernel). Mantido o compatible `snps,dwcmshc-sdhci` no eMMC do DT, para
o dia em que o U-Boot receber o DT do 6.1.

A recovery também tem uma `recovery_dtbo` de 623 bytes, que o U-Boot aplica no DT de fábrica:
`bootargs_ext` no `/chosen` e os modos de reboot. Inofensiva.

## Resultado no aparelho (22/11/2026)

| Boot | Imagem | O que aconteceu |
|---|---|---|
| marco 0 | recovery de fábrica + marca | caminho validado: registrador → recovery → reboot pelo menu → marca no pstore |
| 1 | 6.1 com DT no resource | sem logo, ventoinha parada, preso; tirado da tomada, sem log |
| 2 | + watchdog no `/init`, sysrq `b` | igual ao 1 |
| 3 | + ventoinha e watchdog no `setup_arch` | ventoinha não ligou: o kernel nem começou. Problema no U-Boot |
| 4 | resource de fábrica, DT do 6.1 só na seção dtb | ventoinha ligou; o 6.1 subiu com o DT de fábrica até o `/init` (eMMC falha com aquele DT) e travou; o watchdog **desligou** o aparelho (voltou pelo botão, com o log no pstore) |
| 5 | resource de fábrica + DT embutido | **passou**: relatório completo, reboot quente aos 20 s, Android e Wi-Fi de volta |
| 6 | + fbcon (`console=tty0`), `reboot -f` com `initcall_debug` | o `reboot -f` funciona (todos os shutdowns e `reboot: Restarting system`); DRM liga o LVDS em 1024x600, mas a projeção fica preta com a luz acesa |
| 7 | + configuração SPI do painel | **tela funcionando**: o log do kernel aparece na projeção, legível |

Relatório do boot 5 (log em `~/hy300-work/marco1/resultado5/`, fora do repo; tem o serial na
cmdline):
- eMMC em HS200 a 150 MHz, `misc` em `mmcblk2p4`; SDIO do Wi-Fi detectado (`mmc1:390b`);
- DRM com `card0-LVDS-1` (sem cliente, fica desligado), backlight em 200;
- controle IR (`fdd70030.pwm`), teclas do painel (`adc-keys`), `gpio-keys` e o receptor 2.4G USB;
- LEDs `green`, `red`, `Fan_h`, `Lcd_power`; temperatura do SoC 72 °C;
- reguladores com as tensões de fábrica; só o `mtd_vendor_storage` fica adiado;
- 1,45 GB de RAM livre para o kernel.

Lições:
- **Sinal de vida sem serial:** `CONFIG_HY300_EARLY_BEACON` liga a ventoinha e arma o watchdog
  (~89 s) no começo do `setup_arch`. A ventoinha para no reset e só volta quando um kernel a
  liga, então "ventoinha parada" = o kernel não começou.
- **O reset do watchdog desliga o aparelho** em vez de reiniciar (volta pelo botão de energia).
  A RAM sobrevive: o pstore estava lá.
- **O `reboot -f` funciona.** A suspeita de que ele travava veio do boot 1, em que o kernel
  nem chegou a rodar (era o U-Boot). O `/init` usa o sysrq `b` por padrão e o
  `hy300.shutdown_debug=1` (variável `EXTRA_CMDLINE` do build) usa o `reboot -f` com o
  `initcall_debug`, que registra o shutdown de cada dispositivo.
- **Painel LCD:** o controlador do painel precisa de uma configuração por SPI de 3 fios em
  bit-bang (GPIO1_D5 dados, GPIO1_D6 clock, GPIO1_D7 CS, GPIO2_A0 strobe) que o kernel de
  fábrica manda no `panel_simple_probe` (modificação da TXCZ, string `hason in
  panel_simple_probe spi write`). Sem ela o LVDS funciona e a projeção fica preta. A tabela
  (26 quadros) foi tirada da Image de fábrica com `tools/txcz_panel_seq.py` e vai no DT em
  `hy300,spi-init-sequence`; o `panel-simple` do 6.1 a envia no `prepare`, depois do reset.
  O teste `tests/test_panel_init_seq.py` confere o DTS contra a Image de fábrica.
- **Log na tela:** `CONFIG_FRAMEBUFFER_CONSOLE` e `console=tty0` (padrão do `EXTRA_CMDLINE`). A
  imagem sai sem a correção de keystone, que é feita pelo Android.
- **Wi-Fi:** depois do reboot pelo sysrq `b` o AIC8800 voltou sozinho. Nos reboots normais do
  Android de fábrica ele costuma não voltar (é preciso desligar e ligar o Wi-Fi).

## O que foi portado

O `rk3566-hy300.dts` inclui a mesma placa de referência da fábrica no 6.1
(`rk3566-box-demo-v10.dtsi` + `rk3568-android.dtsi`) e escreve só as diferenças.

| Bloco | No marco 1 |
|---|---|
| Memória | o U-Boot corrige o nó `memory` como na fábrica; CMA de 8 MB em `0x10000000`, igual |
| ramoops | igual à fábrica: `0x110000`, `0xf0000`; record `0x20000`, console `0x80000`, ftrace 0, pmsg `0x50000`, sem ECC; ordem das zonas igual (dmesg, console, pmsg). O 6.1 arredonda o pmsg para `0x40000`, mas o console continua em `0x130000` |
| eMMC | `sdhci` em HS200 a 150 MHz, como no dmesg de fábrica |
| Reguladores | sem PMIC: fixos, `vdd_cpu`/`vdd_logic` por PWM. `vdd_cpu` inicia em 1,0 V e `vdd_fixed` é 1,0 V, como na fábrica; VCCIO4 e VCCIO6 de 1,8 V |
| Clocks | os do `rk356x.dtsi` do 6.1. O SCMI inicia a CPU em 1104 MHz (a fábrica usa 1416 MHz) |
| UART de debug | `fiq-debugger` no UART2, 1.500.000 baud, `console=ttyFIQ0`; `earlycon` vem do `/chosen` |
| Controle IR | `remotectl-pwm` no PWM3, com as seis tabelas de fábrica |
| Teclas | painel no SARADC canal 1 (back, down, left, ok, right, up); energia no GPIO1_B0 |
| LEDs e ventoinha | `gpio-leds` com os nomes da TXCZ: `green`, `red`, `Fan_h` (ligada no boot), `Lcd_power` |
| Painel e backlight | `simple-panel` LVDS 1024x600 no VP1, backlight no PWM4. Portado, mas o teste não depende dele |
| Áudio | I2S1 com codec mudo, I2S3 para a entrada HDMI; HDMI de saída desligado |
| USB | só a porta A, em modo host |
| Acelerômetro | SC7A20 no I2C0, com driver no 6.1 |
| Watchdog | habilitado no DT, como na fábrica; nada o arma no marco 1 |

### Diferenças do DTB contra o de fábrica

Método: `tools/dtnorm.py` em cada DTB (phandles viram caminhos; agora também o pcfg de
`rockchip,pins` e o `native-mode`) e `tools/dtdiff.py` entre os dois.

```bash
PY=~/hy300-work/venv-dt/bin/python
$PY tools/dtnorm.py device-tree/rk3566-hy300-txcz.dtb > fabrica.norm
$PY tools/dtnorm.py ~/hy300-work/kbuild-6.1/arch/arm64/boot/dts/rockchip/rk3566-hy300.dtb > marco1.norm
python3 tools/dtdiff.py fabrica.norm marco1.norm --skip /pinctrl,/__symbols__,/qos,/otp@fe38c000,/power-management@fdd90000,/cpu0-opp-table,/opp-table-0,/opp-table-1,/opp-table2,/npu-opp-table,/bus-npu-opp-table,/dmc-opp-table
```

São 673 linhas sem filtro e 220 com o filtro acima. Quase tudo vem do BSP, não da placa:
nomes de nó (`dwmmc`/`sdhci` viraram `mmc@`, `dmac` virou `dma-controller`), compatíveis
novos (`rockchip,rk3568-i2c` etc.), propriedades renomeadas (`rockchip,clk-trcm` virou
`rockchip,trcm-sync-tx-only`), tabelas de OPP e células do OTP.

Diferenças de placa, todas de propósito:

| Nó | Fábrica | Marco 1 | Motivo |
|---|---|---|---|
| `ethernet@fe010000` | okay | disabled | não há Ethernet; na fábrica ele falha no boot, mas antes muxa os pinos do gmac1m1 e mexe num GPIO de reset |
| `xin32k` | sem pinctrl | sem pinctrl | o 6.1 põe o clock de 32 kHz no GPIO0_B0, que nesta placa é o enable do RK628 |
| `vop@fe040000` | sem `vop-supply` | sem `vop-supply` e sem OPP | o 6.1 desceria o `vdd_logic` para 0,875-0,95 V conforme o clock do VOP |
| `pinctrl/cam/camera-pwr` | GPIO0_C3 | GPIO0_C5 | a fábrica aponta para o pino do PWM4 (backlight); o regulador usa o C5 |
| `rk628_csi_v4l2@50` | okay | disabled | RK628 fica para depois |
| `hdmi-sound` | okay | disabled | sem HDMI de saída; na fábrica ele fica esperando um codec desligado |
| `model` | "Rockchip RK3566 BOX DEMO V10 ANDROID Board" | "HY300 Projector (RK3566, TXCZ y356tx)" | aparece no `Machine model:` do log |

O `compatible` ficou igual ao de fábrica.

O que existe só no 6.1 e fica ligado: `vendor-storage` e `vendor-storage-rm` (o U-Boot antigo
não preenche e o driver só falha), `spi@fe300000/flash@0` (SPI NAND, a sondagem falha como o
`sfc` de fábrica), `video-codec@fdea0400`, `mipi-csi2-hw`. Nós que só a fábrica tem e não
fazem falta agora: `seekwcn_boot` (Wi-Fi SeekWave, não montado), `arm-pmu`.

## initramfs de teste

O `/init` faz, nesta ordem:

1. monta `proc`, `sys`, `devtmpfs`, `debugfs` e `pstore`, e liga `printk_devkmsg`, senão o
   kernel limita as escritas no `/dev/kmsg`;
2. agenda um reboot de segurança aos 45 s;
3. espera até 15 s pela partição com `PARTNAME=misc` em `/sys/class/block`, exige 8192
   setores (4 MiB) e chama `clear_bcb_if_recovery`;
4. aos 10 s escreve o relatório no `/dev/kmsg`, uma linha por registro com prefixo
   `hy300: [seção]`: versão, cmdline, modelo, memória, `/proc/iomem`, partições e nomes, mmc
   (`ios` do debugfs), `/sys/class/drm`, backlight, entrada, LEDs, temperatura, resumo dos
   reguladores, GPIOs, `devices_deferred`, interrupções e o `ls` do pstore;
5. aos 20 s faz `sync` e `reboot -f`. É reboot quente com motivo normal: o `reboot-mode` grava
   `0x5242c300` e o U-Boot sobe a `boot`.

A `misc` é a única escrita no eMMC. A regra está em `kernel/initramfs-test/hy300-test.sh`:

- lê os 32 primeiros bytes (comando do `bootloader_message`) até o primeiro NUL;
- só se o comando começar com `boot-recovery`, zera os 2048 bytes do `bootloader_message`
  com `dd conv=notrunc,fsync`, e depois `sync`;
- não toca em mais nada. Em `0x800` ficam os dados A/B da Rockchip (`\0AB0`). Em 16 KiB a
  `misc` de fábrica tem um BCB legado com `boot-recovery\nrecovery\n--wipe_all`. O U-Boot
  ignora esse bloco, senão o aparelho viveria na recovery. Um init que "limpasse" ali mudaria
  a `misc` à toa.

Como a `misc` de fábrica tem o BCB do offset 0 vazio, depois do teste a `misc` volta a ser
igual ao backup, e o `check-test-boot.sh` deve dizer "igual à fábrica".

O teste de fumaça no QEMU (`smoke-qemu.py`, chamado pelo `build-marco1.sh`) boota o mesmo
kernel com PL011 e virtio (fragmento `kernel/initramfs-test/qemu.config`) e um disco GPT falso
cuja `misc` é a `misc.img` de fábrica com `boot-recovery` no offset 0. Ele confere que o BCB foi
zerado, que o resto da `misc` e as outras partições ficaram iguais, que o relatório saiu e que
o reboot veio por volta dos 20 s. Esse teste achou um bug real antes do aparelho: os applets do
busybox ficam em `/usr/bin` e o PATH do init não tinha esse diretório, então `cut` falhava, o
uptime vinha vazio e o reboot de segurança disparava na hora.

## Wi-Fi no 6.1

Objetivo: um terminal ao vivo no 6.1 sem console serial. Com `hy300.wifi=1` na cmdline o
`/init` de teste carrega o driver do AIC8800, conecta na rede de casa com IP fixo, abre um
`telnetd` (busybox, porta 23, `/bin/sh` de root, sem senha) e fica no ar até um prazo.

### Chip e driver

- **Variante: AIC8800D80, revisão U02.** O dmesg de fábrica (`kernel/dmesg-boot.txt`) mostra
  o SDIO `vid:0xC8A1 did:0x0082` (função 2: `0x0182`), que no driver é o
  `PRODUCT_ID_AIC8800D80`, e o `aic8800_bsp` carrega `fw_patch_table_8800d80_u02.bin`,
  `fw_adid_8800d80_u02.bin`, `fw_patch_8800d80_u02.bin` e `fmacfw_8800d80_u02.bin`. Os
  `aic_userconfig_8800dc/dw.txt` do vendor são de outras montagens.
- **Driver:** `aic8800_bsp` e `aic8800_fdrv` (SDIO) do `aic8800d_linux_sdk_V3.0_2023_1107_581567ff`,
  na cópia que a Radxa publica em `github.com/radxa-pkg/aic8800` (tag `3.0+git20231107.581567ff-2`,
  commit `956e3e8c239f`; o `debian/copyright` declara `src/*` como GPL-2 e os módulos têm
  `MODULE_LICENSE("GPL")`). Escolhido por ser a versão do firmware de fábrica: o
  `fmacfw_8800d80_u02.bin` do HY300 tem o mesmo MD5 (`2aa840ea...`) do SDK dessa data, e o
  dmesg de fábrica mostra `RELEASE_DATE:2023_1108`. As versões mais novas do SDK (V4, V5) trazem
  firmware novo, e misturar driver novo com firmware antigo é risco à toa.
- **Na árvore:** `drivers/net/wireless/aic8800/` do branch `hy300-6.1`, `CONFIG_AIC8800=m` no
  `rk3566_hy300.config`. Ficou de fora o `aicwf_firmware_array.c` (firmware embutido como
  vetores em C, só usado com `CONFIG_FIRMWARE_ARRAY`) e o `aic8800_btlpm` (Bluetooth).
  Ajustes para o 6.1: `cfg80211_ch_switch_notify` com 3 argumentos, `eth_hw_addr_set` no lugar
  de escrever no `dev_addr`, `REGULATORY_IGNORE_STALE_KICKOFF` (removido no 6.1.39) e um
  `printk` com argumentos trocados.
- **Plataforma:** compilado sem `CONFIG_PLATFORM_ROCKCHIP*`. Quem liga o chip é o
  `sdio-pwrseq` do DT (WL_REG_ON no GPIO2_B1, 32 kHz do RTC), e o 6.1 já enumera o cartão
  (`mmc1: new ultra high speed SDR104 SDIO card at address 390b`). O `aic8800_bsp` só registra
  o driver SDIO e acha o cartão. O DT não mudou: `wifi_chip_type = "ap6398s"` é herança da
  placa de referência, igual na fábrica, e o driver não usa o `rfkill-wlan`. O SDIO segue
  limitado a 50 MHz, como na fábrica.
- **Firmware:** lido pelo `aic8800_bsp` de `/lib/firmware/aic8800` (parâmetro `aic_fw_path`,
  também é o padrão do build). Não vai para o repositório.

### Como o build pega firmware e rede

```bash
WIFI=1 kernel/build-marco1.sh
```

Com `WIFI=1` o `build-marco1.sh` acrescenta `hy300.wifi=1` à cmdline e monta uma raiz extra
em `~/hy300-work/marco1/wifi-root` que o `initramfs-test/build.sh` copia por cima da raiz:

| No initramfs | De onde vem |
|---|---|
| `/lib/modules/aic8800/aic8800_{bsp,fdrv}.ko` | build do kernel (`make modules`), sem símbolos de depuração |
| `/lib/firmware/aic8800/` | `tools/wifi_payload.py` tira do `~/hy300-work/vendor.img` (ext4, `debugfs`) os 4 binários acima e o `aic_userconfig_8800d80.txt`, e confere o MD5 de cada um (os dos binários são os que o driver de fábrica imprime no dmesg) |
| `/usr/sbin/wpa_supplicant`, `wpa_cli` | `kernel/wifi/build-wpa-supplicant.sh`: wpa_supplicant 2.11 e libnl 3.11.0, estáticos com musl, driver nl80211 e criptografia interna do hostap (WPA/WPA2-PSK; WPA3-SAE precisaria de OpenSSL). Tarballs conferidos por SHA-256 |
| `/etc/wpa_supplicant.conf` (modo 600) | gerado do arquivo de credenciais: SSID em hexadecimal e a PSK já derivada (PBKDF2), sem a senha em claro |
| `/etc/hy300-wifi.conf` | IP com prefixo, gateway e DNS, validados (o gateway tem de estar na rede do IP) |

As credenciais ficam só em `~/hy300-work/wifi/credenciais.conf` (ou `WIFI_CREDENTIALS`), com
modo 600. O build recusa o arquivo se ele faltar, se outro usuário puder lê-lo, se faltar uma
chave ou se um valor for inválido, e diz o que corrigir. Formato (valores fictícios):

```
WIFI_SSID=NomeDaRede
WIFI_PSK=senha-da-rede
WIFI_ADDRESS=192.0.2.10/24
WIFI_GATEWAY=192.0.2.1
WIFI_DNS=192.0.2.1
```

O IP é fixo (sem DHCP): o coordenador já sabe onde procurar o aparelho. O `vendor.img` vem de
`VENDOR_IMG` (padrão `~/hy300-work/vendor.img`). Nada disso sai do `~/hy300-work`. A imagem
gerada tem as credenciais da rede: não publicar a `recovery-marco1.img` nem o initramfs.

### O que o `/init` faz com `hy300.wifi=1`

1. Arma o watchdog (60 s) e **alimenta a cada 10 s** (o reset do watchdog desliga o aparelho).
2. Grava o prazo: início + `hy300.wifi_limit` segundos (padrão 900, 15 min). Um laço confere o
   prazo a cada 5 s e, quando ele chega, mata o daemon do watchdog com `kill -9` (sem o
   fechamento mágico o watchdog continua armado) e faz o `sysrq b`, como o marco 1.
3. Apaga o `boot-recovery` da `misc` (mesma regra do marco 1) e aos 10 s escreve o relatório.
4. `insmod aic8800_bsp.ko aic_fw_path=/lib/firmware/aic8800`, `insmod aic8800_fdrv.ko`, espera
   até 20 s pela interface sem fio (`/sys/class/net/*/wireless`, normalmente `wlan0`).
5. `wpa_supplicant -B -D nl80211` (log em `/tmp/wpa_supplicant.log`) e espera até 60 s pelo
   `wpa_state=COMPLETED`.
6. IP fixo, rota padrão e `/etc/resolv.conf`; ARP não solicitado (o IP pode ter sido do Android,
   com outro MAC); `ping` no gateway (só informativo); `telnetd -p 23 -l /bin/sh`.
7. A cada 15 s escreve na tela e no `/dev/kmsg` (pstore):
   `hy300: [wifi] IP <ip>, telnet <ip> 23; reinicia em <n> s`.

Cada etapa sai com o prefixo `hy300: [wifi]`. Se uma etapa falha, aparece
`hy300: [wifi] FALHOU: <motivo>` e o prazo cai para 2 minutos: a mensagem fica na tela e o
aparelho volta ao Android sozinho. Sem a flag o `/init` é o do marco 1 (reinicia aos 20 s).

Pelo telnet:

```sh
touch /tmp/hy300-ficar            # desliga o reinício automático (o watchdog segue alimentado)
rm /tmp/hy300-ficar               # religa; se o prazo já passou, reinicia em até 5 s
cat /tmp/wpa_supplicant.log; wpa_cli -i wlan0 status; dmesg | tail
echo b > /proc/sysrq-trigger      # reinicia agora (volta ao Android)
```

O log do pstore e o `/tmp/wpa_supplicant.log` podem ter o SSID e os MACs: limpar antes de
publicar, como o serial.

### Testes

- `tests/test_wifi_payload.py`: credenciais (arquivo ausente, modo, chaves, IP e gateway, limites
  do SSID e da senha), PSK contra o vetor do IEEE 802.11i, conteúdo dos arquivos gerados,
  extração e MD5 do firmware.
- `tests/test_initramfs_wifi.py`: as funções de `hy300-wifi.sh` com `insmod`, `ip`, `wpa_cli`,
  `wpa_supplicant` e `arping` falsos, no `/bin/sh` do host e no busybox.
- `smoke-qemu.py` ganhou uma terceira rodada com `hy300.wifi=1 hy300.wifi_limit=50`: o virt não
  tem SDIO, então o `aic8800_bsp` carrega, não acha o chip em 2 s e o `aic8800_fdrv` falha
  (`No such device`). O teste confere BCB apagado, relatório, `FALHOU`, nenhum reboot aos 20 s e
  o reboot no prazo (50 a 70 s). As duas rodadas antigas continuam iguais.

### Roteiro do teste no aparelho

```bash
WIFI=1 kernel/build-marco1.sh                      # imagem com hy300.wifi=1 (+ .sha256)
scripts/flash-test-recovery.sh ~/hy300-work/marco1/recovery-marco1.img
scripts/reboot-to-test-slot.sh --dry-run
scripts/reboot-to-test-slot.sh
```

Na tela, em ordem (cerca de 30 s depois do logo):

1. `hy300: [init] wifi: início (t=... s), reinicia em 900 s; touch /tmp/hy300-ficar para ficar`;
2. o relatório (`hy300: [versao]`, `[mmc]` etc.);
3. `aicbsp_init`, `aicbsp: aicbsp_sdio_probe:1 vid:0xC8A1  did:0x0082`, as linhas
   `rwnx_load_firmware ... md5` e `ieee80211 phy0: ...`;
4. `hy300: [wifi] interface wlan0, iniciando o wpa_supplicant`, `conectado`, `gateway ... responde`,
   `telnetd na porta 23`;
5. a cada 15 s: `hy300: [wifi] IP <ip>, telnet <ip> 23; reinicia em <n> s`.

No PC: `telnet <ip>` (o IP do `credenciais.conf`; também aparece na tela). Se o aparelho não
responder, `ping <ip>` e `ip neigh` para ver se o ARP chegou. Para sair do teste: `echo b >
/proc/sysrq-trigger` pelo telnet, ou esperar o prazo. Depois, de volta no Android:
`scripts/check-test-boot.sh hy300.test=marco1` e `adb pull /sys/fs/pstore/console-ramoops-0`.

| Falha | Na tela | O que acontece |
|---|---|---|
| módulo não carrega / chip não responde | `FALHOU: insmod ... aic8800_fdrv falhou` (e as linhas `aicbsp` antes) | reinicia em 2 min |
| sem `wlan0` | `FALHOU: nenhuma interface sem fio em 20 s` | reinicia em 2 min |
| senha errada, rede fora do alcance, roteador só WPA3 | `FALHOU: sem conexão em 60 s (estado SCANNING/4WAY_HANDSHAKE/...)` | reinicia em 2 min |
| conectou mas o PC não alcança | linhas de status normais | `ping`, ARP; esperar o prazo de 15 min |
| kernel trava ou dá panic no driver | log para | panic reinicia em 10 s; travamento sem panic: o watchdog desliga o aparelho em ~60 s (ligar pelo botão, o log fica no pstore) |

## Pendências por driver

| Bloco | O que há no 6.1 | Falta |
|---|---|---|
| Wi-Fi AIC8800 (SDIO) | `aic8800_bsp` e `aic8800_fdrv` na árvore (`CONFIG_AIC8800=m`), carregados pelo `/init` com `hy300.wifi=1` | testar no aparelho ("Wi-Fi no 6.1"); Bluetooth (`aic8800_btlpm`) não foi portado |
| RK628 (entrada HDMI) | `VIDEO_RK628_CSI` (`drivers/media/i2c/rk628`) e `drivers/misc/rk628`, ligados no config | o nó está portado e desligado. Ligar depois que o display funcionar e conferir o caminho `csi2-dphy0` → `rkisp` |
| Motor de foco | nada. Na fábrica o nó `rk_motor` (`usb-cam-gpio`) não tem propriedades: o driver fechado da TXCZ fixa os GPIOs no código | escrever o driver a partir de `reverse-engineering/libfocus/README.md`, mantendo `/sys/class/motor_cc` |
| QMI8658 | sem driver. O chip nem está montado: no dmesg de fábrica o QMI8658 lê devid 0, e quem responde é o SC7A20 em `0x19` (id `0x11`) | conferir no relatório se o `gsensor` do SC7A20 aparece em `entrada` |
| Mali G52 | `MALI_BIFROST` no BSP | ligar com devfreq depois do primeiro boot |
| DVFS de CPU, DDR e barramentos | drivers no BSP | ligar um por vez; o DMC depende do TF-A de fábrica |
| NPU | `ROCKCHIP_RKNPU` | desligada também na fábrica |

## Como entrar na recovery sem tocar na misc

O `adb reboot recovery` do Android 12 grava `boot-recovery` no BCB da `misc` (o init do
Android faz isso quando o comando está vazio). O U-Boot volta para a recovery enquanto esse
comando estiver lá, e quem apaga seria o nosso `/init`. Se o kernel de teste morresse antes,
todo boot cairia de novo na recovery, e tirar da tomada não resolveria. Por isso o teste não
usa mais o `adb reboot recovery`.

O caminho novo usa só o registrador do `reboot-mode`:

1. `scripts/reboot-to-test-slot.sh` manda o `reboot-recovery` (`kernel/reboot-recovery/`,
   C estático com musl, aarch64) para `/data/local/tmp` e roda como root.
2. O binário faz `sync`, escreve `u` em `/proc/sysrq-trigger` (remonta só-leitura tudo que tem
   dispositivo de bloco), espera o `/proc/mounts` mostrar isso (até 10 s), faz `sync` de novo e
   chama `reboot(0xfee1dead, 0x28121969, LINUX_REBOOT_CMD_RESTART2, "recovery")`. O init do
   Android fica de fora, então ninguém escreve na `misc`.
3. O kernel de fábrica (`syscon-reboot-mode` no `pmugrf` `0xfdc20000`, `offset = 0x200`) grava
   `mode-recovery = 0x5242c303` em `0xfdc20200`. É o mesmo valor depois do overlay da
   `recovery_dtbo`.
4. O PSCI faz o reset global do SoC. O PMU_GRF fica no domínio de energia que esse reset não
   alcança, então o valor sobrevive ao reboot quente. É o mesmo mecanismo do
   `adb reboot bootloader` de fábrica. Sem energia o registrador zera, porque ele não tem
   bateria nem cópia em memória não volátil.
5. O U-Boot lê `0xfdc20200` e, com o BCB vazio, mostra "boot mode: recovery (cmd)", sobe a
   recovery e grava `0x5242c300` (normal) no registrador. Só vale para um boot.

O que o U-Boot de fábrica faz com cada valor (desmontagem do `rockchip_get_boot_mode` do
`uboot.img`, função em `0xa02d10`; todos os chamadores escolhem a recovery só com o modo 1):

| Registrador | Mensagem | Modo | Limpa o registrador? | Partição |
|---|---|---|---|---|
| `0x5242c300` normal | "boot mode: normal" | 0 | sim | boot |
| `0x5242c303` recovery | "boot mode: recovery (cmd)" | 1 | sim, volta para normal | recovery |
| `0x5242c307` panic | "boot mode: panic" | 7 | não | boot |
| `0x5242c308` watchdog | "boot mode: watchdog" | 8 | não | boot |
| `0x5242c301` loader | "boot mode: loader" | 3 | sim | Rockusb |
| `0x5242c309` fastboot | "boot mode: bootloader" | 2 | sim | fastboot do U-Boot |
| qualquer outro, ou 0 depois de faltar energia | "boot mode: None---" | 10 | não | boot |

A ordem de prioridade no U-Boot é: loader/fastboot pelo registrador, depois o BCB da `misc`,
depois o resto do registrador. Um `boot-recovery` no BCB ganha do registrador. Por isso o
`reboot-to-test-slot.sh` se recusa a seguir com qualquer comando no BCB.

O que o 6.1 grava quando reinicia sozinho (`drivers/power/reset/reboot-mode.c` do BSP):

- `reboot -f` do nosso init: comando vazio, grava `mode-normal` `0x5242c300`. Vai para a boot.
- panic (inclusive softlockup e hung task): o notificador de panic grava `mode-panic`
  `0x5242c307`, e o restart seguinte não sobrescreve. Vai para a boot.
- reset por watchdog ou pela proteção térmica do TSADC: ninguém escreve; fica o `0x5242c300` que o
  U-Boot deixou ao entrar na recovery. Vai para a boot.
- só um `reboot recovery` ou `reboot fastboot` explícito gravaria `0x5242c303` de novo, e o
  initramfs de teste não faz isso.

Nenhum desses caminhos leva de volta à recovery. O `/init` continua apagando um
`boot-recovery` do BCB, se aparecer, como segunda proteção.

O preço é um reboot sem o desligamento normal do Android: os serviços não param. O `sync`
duplo e o sysrq `u` deixam os sistemas de arquivos de bloco limpos antes do reboot. Se alguma
montagem continuar rw depois de 10 s, o binário avisa e reinicia mesmo assim, porque o `sync`
já foi feito.

Compilar e testar no host:

```bash
kernel/reboot-recovery/build.sh          # ~/hy300-work/marco1/reboot-recovery/reboot-recovery
python3 -m unittest tests.test_reboot_recovery tests.test_reboot_to_test_slot
```

Os testes compilam os testes de unidade em C com o gcc do host e rodam o binário aarch64 no
`qemu-aarch64-static -strace` com um sysrq e um `/proc/mounts` falsos. Como usuário comum, o
kernel do host recusa o reboot com EPERM. O `strace` do host decodifica a chamada:
`reboot(LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2, LINUX_REBOOT_CMD_RESTART2, "recovery")`. O
script é testado com um `adb` falso: recusa com BCB preenchido ou com outra imagem na recovery,
e o `--dry-run` nunca roda o reboot de verdade.

## Riscos do primeiro boot

1. **Loop na recovery.** Com o caminho acima o BCB fica vazio, então um kernel de teste que
   morre cedo não prende o aparelho: tirar da tomada zera o registrador e o U-Boot sobe o
   Android. O risco volta se alguém usar `adb reboot recovery` ou se o BCB já tiver comando (o
   script confere). O BCB legado em 16 KiB não conta, o U-Boot não lê aquele bloco.
2. **Travamento sem panic.** Panic, oops, softlockup e hung task reiniciam em 10 s. Um
   travamento que nenhum detector pega fica parado, porque o watchdog não é armado. Aí é tirar
   da tomada. O reboot frio perde a RAM e o log, mas volta ao Android.
3. **Log incompleto.** O pstore só guarda o que vier depois do probe do ramoops (o console
   repassa o buffer desde o começo). Um crash antes disso não deixa log. Se houver panic, o
   `dmesg-ramoops-0` também aparece, com deflate, que o 4.19 lê.
4. **Tensões.** As de `vdd_cpu`, `vdd_logic`, `vdd_fixed` e das VCCIO são as de fábrica. Sem DVFS
   nada muda depois do probe dos reguladores PWM. O SCMI pede 1104 MHz para a CPU, abaixo dos
   1416 MHz de fábrica. A proteção térmica de hardware do TSADC reseta o SoC a 120 °C.
5. **Display.** O painel pode ficar preto ou com lixo e o backlight pode apagar. O U-Boot ainda
   mostra o logo, e a passagem para o DRM do 6.1 não foi testada. O teste não depende da tela.
6. **Ventoinha.** `Fan_h` liga no probe do `gpio-leds`. Até lá ela fica como o U-Boot deixou.
   O teste dura cerca de 20 s.
7. **Nada além da `misc`.** O init não monta nem escreve outra partição. O U-Boot, a `boot` e a
   `super` não são tocados.

## Roteiro de teste (com o usuário presente)

```bash
# 0. marco 0 já feito, recovery de fábrica gravada e Android normal
kernel/reboot-recovery/build.sh
scripts/flash-test-recovery.sh ~/hy300-work/marco1/recovery-marco1.img
scripts/reboot-to-test-slot.sh --dry-run    # confere BCB vazio e roda o binário em modo seco
scripts/reboot-to-test-slot.sh              # confere a imagem na recovery e reinicia
# esperar ~1 min: o U-Boot sobe o 6.1, o init reinicia sozinho e o Android de fábrica volta.
scripts/check-test-boot.sh hy300.test=marco1
adb pull /sys/fs/pstore/console-ramoops-0 ~/hy300-work/marco1/console-marco1.txt
scripts/flash-test-recovery.sh ~/hy300-backup/recovery.img   # recovery de fábrica de volta
```

O que acontece em cada falha:

| Falha | O que o usuário vê | O que fazer |
|---|---|---|
| O script recusa (BCB com comando, imagem errada na recovery, binário errado) | nada reinicia | ler a mensagem; o aparelho segue no Android |
| O binário não consegue escrever o sysrq | nada reinicia, "nada foi reiniciado" | o Android segue rodando; ver permissão de root |
| Montagem que não ficou só-leitura em 10 s | aviso, reboot mesmo assim | nada; o Android pode rodar fsck no boot seguinte |
| U-Boot não sobe o kernel de teste (DTB, imagem) | volta sozinho ao Android, ou fica no logo | se ficar no logo, tirar da tomada: o Android volta |
| Kernel trava antes do ramoops | tela parada | esperar 2 min e tirar da tomada; volta ao Android sem log |
| Kernel dá panic | reboot em 10 s, volta ao Android | `check-test-boot.sh` mostra `dmesg-ramoops-0` |
| Kernel sobe mas o init falha | reboot de segurança aos 45 s ou panic | log no pstore |
| Tudo certo | Android volta em ~1 min | `check-test-boot.sh` mostra a marca, as linhas do init e a `misc` "igual à fábrica" |

Só um caminho não volta sozinho tirando da tomada: um BCB com `boot-recovery` gravado por fora
(por exemplo um `adb reboot recovery` dado por engano). Nesse caso o `/init` de teste apaga o
comando se chegar a rodar.

O `check-test-boot.sh` mostra a cmdline do boot anterior (deve ter `hy300.test=marco1`), os
registros do pstore, as linhas `hy300: [init]` e `hy300: [misc]` e o hash da `misc`. O relatório
completo está no `console-marco1.txt` (`grep 'hy300: \['`). Antes de publicar esse log, tirar o
serial (`androidboot.serialno`) e o que identificar o aparelho.
