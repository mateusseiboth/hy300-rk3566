# Kernel 6.1: marco 1

Primeiro boot do kernel BSP Rockchip `develop-6.1` no HY300, pela partição `recovery`. O boot
normal continua pela `boot`, com o Android de fábrica. O kernel de teste sobe um initramfs
mínimo que apaga o `boot-recovery` da `misc`, escreve um relatório no log e reinicia sozinho
em cerca de 20 s. O log é lido depois, já no Android, em `/sys/fs/pstore/console-ramoops-0`.

Estado em 22/11/2026: **passou no aparelho** (quinto boot). O 6.1 sobe com o próprio DT,
acha o eMMC e a `misc`, escreve o relatório no pstore e reinicia pelo sysrq `b` aos 20 s. O
Android de fábrica volta sozinho, com Wi-Fi. Ver "Resultado no aparelho".

**Base nova (22/11, ainda não testada no aparelho):** os patches do HY300 foram levados para o
kernel Android da Rockchip, branch `hy300-ack-6.1` (ver "Base Android"). É a base do LineageOS
24.0. O `hy300-6.1` (BSP Linux) continua intacto e é o que já funcionou no aparelho; o
`build-marco1.sh` compila os dois (`KBASE=ack`, o padrão, ou `KBASE=bsp`).

| Item | Onde |
|---|---|
| DT, Makefile e fragmento de config | branch `hy300-ack-6.1` do `kernel-hy300-rk3566` sobre `lineage-23.2` do Lineage-Rockchip `f4f8107cf7cf` (6.1.172). Antes: branch `hy300-6.1`, commit `8b5abca` sobre `develop-6.1` `77168c8d5ab8` |
| Script que monta tudo | `kernel/build-marco1.sh` (+ `kernel/lib-kbase.sh`) |
| initramfs de teste | `kernel/initramfs-test/` (`init`, `hy300-test.sh`, `build.sh`) |
| Testes | `tests/test_initramfs_misc.py`, `tests/test_dtdiff.py`, `tests/test_dtnorm.py`, `tests/test_dt_gpio_irq.py` (teclas do `gpio-keys`: pino de fábrica, tipo da IRQ e LED no mesmo pino; `HY300_PORT_DTB=<dtb>` confere o DT do porte), `tests/test_kbase.py`, `tests/test_smoke_qemu.py`, `kernel/initramfs-test/smoke-qemu.py` |
| Imagem | base ack: `~/hy300-work/marco1-ack/recovery-marco1.img`; base bsp: `~/hy300-work/marco1/recovery-marco1.img` (fora do repo) |
| Wi-Fi (AIC8800D80) | commits `2b227eb`, `53fa34e` e `12e46e1` do `hy300-6.1` (no `hy300-ack-6.1`: `2011306`, `3c7ca16`, `fcca870` e `1e3aa6b`); modo `hy300.wifi=1` do `/init`; ver "Wi-Fi no 6.1" |

## Base Android (`hy300-ack-6.1`)

O LineageOS 24.0 (Android 17) só aceita o 6.1 pela matriz de FCM nível 8, que exige
binder, ashmem, `dm-default-key`, `cpufreq_times`, `uid_sys_stats`, `xt_quota2` e o resto do
`kernel/configs/u/android-6.1`. O `develop-6.1` é o BSP Linux e não tem esses drivers (ver
`docs/lineageos.md`, "Kernel"). Os patches do HY300 foram para um kernel que já os tem.

**Base: `github.com/Lineage-Rockchip/android_kernel_rockchip_kernel-6.1`, branch
`lineage-23.2`** (commit `f4f8107cf7cf`, 20/10/2026, remoto `lineage-rockchip` no clone). O
histórico de primeiro pai é o ACK `android14-6.1` (tag `android14-6.1-2026-06_r1` mesclada) e o
`develop-6.1` da Rockchip entra por merge, **até o mesmo commit `77168c8d5ab8` em que o
`hy300-6.1` foi feito**. Por isso os 10 commits do HY300 entraram por cherry-pick com um conflito
só (duas linhas no `drivers/net/wireless/{Kconfig,Makefile}`, ao lado do `rtl8821cu`). Por cima
vêm placas da Khadas, Hardkernel e da H96 (Lineage-Rockchip), que não tocam no RK3566 além do
que está na tabela abaixo. O próprio `android14-6.1` do Google não serve: não tem a parte da
Rockchip (VOP2, RK628, remotectl, `rk_vendor_storage`, dtsi do RK356x), e a Rockchip não publica
o kernel do SDK Android.

Commits no `hy300-ack-6.1` (em ordem):

| Commit | O quê |
|---|---|
| `79e4d31`, `1c1687d`, `ff4f724` | DT do HY300 (iguais aos do `hy300-6.1`) |
| `54589e4`, `55433d7` | sinal de vida (ventoinha e watchdog) e DT embutido; o hook no `setup.c` entrou limpo |
| `67cf4f3`, `07a3d0b` | console no framebuffer; painel SPI no `panel-simple` |
| `2011306`, `3c7ca16`, `fcca870` | driver AIC8800 e o módulo no fragmento |
| `a9ca5ee` | fragmento sobre o `rockchip_defconfig` + `android-14.config` (ver "Config") |
| `67972d3` | `certs/extract-cert.c` e `scripts/sign-file.c` iguais aos do `develop-6.1` (provider pkcs11 do OpenSSL 3): o OpenSSL 4.0 do Fedora 45 não tem mais a API ENGINE que a árvore Android usa |
| `1e3aa6b` | AIC8800 no clang e no cfg80211 do ACK (abaixo) |
| `e74809d` a `73e0ec0` | os 7 commits que entraram no `hy300-6.1` depois (Alpine de recuperação: overlayfs/f2fs/erofs/exfat, device mapper, `KEXEC_FILE`, Ethernet USB, GPU no formato do Panfrost, Panfrost como módulo, fonte Terminus) |

O que muda em relação ao `hy300-6.1` que já funcionou:

- **Nomes de nó.** O `rk356x.dtsi` desta árvore usa os nomes antigos: o eMMC é
  `sdhci@fe310000` (no BSP Linux, `mmc@fe310000`) e o SDIO do Wi-Fi é `dwmmc@fe2c0000`. O
  `/init` acha a `misc` pelo `PARTNAME`, então não muda nada no teste. No Android,
  `androidboot.boot_devices=fe310000.sdhci`, igual à fábrica (a árvore `device-hy300` já foi
  ajustada).
- **AIC8800.** O ACK traz do 6.3 o `cfg80211_ch_switch_notify` e o
  `cfg80211_ch_switch_started_notify` com `link_id` e `punct_bitmap`, mas a versão continua 6.1.
  O Makefile do `aic8800_fdrv` procura `u16 punct_bitmap` no `include/net/cfg80211.h` e define
  `AICWF_CFG80211_PUNCT_BITMAP`. O clang também recusou um `u8 *` recebendo o `dev_addr`
  (`const`) e o comentário `/* fall-through */`.
- **Config Android.** `PREEMPT` (antes `PREEMPT_VOLUNTARY`), `RANDOMIZE_BASE` (KASLR),
  `SHADOW_CALL_STACK`, SELinux ligado (sem política carregada nada é negado),
  `STATIC_USERMODEHELPER`, `PRINTK_CALLER` (cada linha do log ganha `[T1]` ou `[C0]` depois do
  tempo), o `rk_system_heap` do dma-buf (pede o mapa da DDR ao TF-A no boot; se o TF-A de
  fábrica não souber responder, o driver segue sem ele). Muitos drivers a menos (DVB, MTD,
  NFS, EFI, Bluetooth por UART); nenhum que o HY300 use no marco 1.
- **Toolchain.** clang 20 (`clang-r547379`) no lugar do GCC 16. A `Image` ficou com 34,9 MiB
  (antes 38,4 MiB).

## Como compilar (base Android)

```bash
cd ~/hy300-handoff/kernel-hy300-rk3566
git fetch origin hy300-ack-6.1 && git checkout hy300-ack-6.1
cd ~/hy300-handoff/hy300-rk3566
KBASE=ack WIFI=1 kernel/build-marco1.sh      # KBASE=ack é o padrão
```

O script, nesta ordem: confere a árvore (`kernel/configs/android-14.config` tem de existir),
põe o clang na frente do PATH, gera o `.config` com
`make ARCH=arm64 LLVM=1 LLVM_IAS=1 rockchip_defconfig android-14.config rk3566_hy300.config`,
roda `tools/kconfig_check.py` contra `KCONFIG_REQS` (padrão
`~/android/lineage/kernel/configs/u/android-6.1`) e **para se houver diferença** (relatório em
`~/hy300-work/marco1-ack/kconfig-check.txt`), compila `Image`, módulos e DTB em
`~/hy300-work/kbuild-ack-6.1`, monta a imagem em `~/hy300-work/marco1-ack/recovery-marco1.img` e
roda o smoke no QEMU (kernel à parte em `~/hy300-work/kbuild-ack-6.1-qemu`).

| Variável | Padrão |
|---|---|
| `KBASE` | `ack`; `bsp` refaz o marco 1 antigo (branch `hy300-6.1`, GCC, `~/hy300-work/marco1`) |
| `CLANG_DIR` | `~/android/lineage/prebuilts/clang/host/linux-x86/clang-r547379` (só leitura) |
| `KCONFIG_REQS` | `~/android/lineage/kernel/configs/u/android-6.1`; se não existir, a conferência é pulada |
| `KBUILD_OUT` | `~/hy300-work/kbuild-ack-6.1` |

Pacotes no host: os mesmos do marco 1 (o GCC cruzado ainda compila o musl, o busybox e o
wpa_supplicant do initramfs). O kernel usa só o clang dos prebuilts do LineageOS.

Por que o `clang-r547379` (clang 20): é o mais antigo dos prebuilts do checkout, o mais perto
do clang 17 com que o Google testa o `android14-6.1`. O padrão do Lineage 24.0
(`ClangDefaultVersion`, `clang-r584948`, clang 22) também deve servir, mas não foi testado. Se
o kernel um dia for compilado pelo próprio build do Lineage, `TARGET_KERNEL_CLANG_VERSION :=
r547379` mantém o mesmo compilador.

Resultado do build de 22/11 (`hy300-ack-6.1` `73e0ec0`, `WIFI=1`):

| Arquivo | Tamanho |
|---|---|
| `Image` (6.1.172-hy300, clang 20) | 36.565.000 bytes |
| `Image.gz` (`gzip -9 -n`, para a `boot` do Lineage) | 15.172.609 bytes |
| `rk3566-hy300.dtb` | 168.686 bytes |
| `recovery-marco1.img` | 113.246.208 bytes, igual à partição |

SHA-256 da imagem desse build (`WIFI=1`, tem as credenciais da rede: não publicar):
`ce3a481c100d6557939e3cf5374239ff66ed6e137be9fabbdd875a6787fdbc14`. Outro build dá outro hash
(data do busybox); o script grava o do build atual em `recovery-marco1.img.sha256`.

`kconfig_check.py` contra `u/android-6.1`: **0 diferenças**, kernel 6.1.172 >= 6.1.0.
Smoke no QEMU: passa nos três modos (padrão, `hy300.shutdown_debug=1`, `hy300.wifi=1`).

O smoke precisou de dois ajustes para esta base: o `rk_system_heap` faz SMC ao TF-A no
initcall (o virt não tem TF-A; entrou no `initcall_blacklist` junto do `rockchip_drm_init`), e o
`PRINTK_CALLER` mudou o formato da linha do `sysrq: Resetting`.

### Riscos do primeiro boot da base Android

O fluxo é o mesmo do marco 1 (slot `recovery`, `reboot-to-test-slot.sh`, watchdog, pstore).
O que pode dar diferente:

1. **Kernel não sobe ou trava cedo.** Outro compilador, KASLR, shadow call stack e
   `PREEMPT` completo. O sinal de vida continua: ventoinha ligada = o `setup_arch` rodou;
   watchdog de 89 s reinicia se travar (antes desligava; ver "Reinício sozinho em panic e travamento").
2. **Driver novo no boot.** O `rockchip_defconfig` liga coisas que o `rockchip_linux_defconfig`
   não ligava (por exemplo o `rk_system_heap`, binder, ashmem, incfs, netfilter do Android). Um
   panic reinicia em 10 s e fica no `dmesg-ramoops-0`.
3. **eMMC com outro nome** (`fe310000.sdhci`). Só importa para o Android; o `/init` de teste
   procura pelo nome da partição.
4. **Wi-Fi.** O AIC8800 compilou com a API do cfg80211 do ACK; o caminho de troca de canal
   (CSA, só no modo AP) mudou e não é usado no teste. O modo `hy300.wifi=1` carrega os módulos
   desta árvore (mesmo `vermagic`).
5. **Tela.** Mesmo DRM e mesmo painel; o `VT` foi religado no fragmento porque o
   `rockchip_defconfig` o desliga e sem ele não há fbcon.

## Como reproduzir (marco 1, BSP Linux)

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
KBASE=bsp kernel/build-marco1.sh            # marco 1 no BSP Linux (hy300-6.1)
KBASE=bsp SMOKE=0 kernel/build-marco1.sh    # sem o teste no QEMU
```

Sem `KBASE` o script compila a base Android (seção "Como compilar (base Android)").

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

Base Android (`hy300-ack-6.1`): clang 20 dos prebuilts do LineageOS (`LLVM=1 LLVM_IAS=1`), ver
"Como compilar (base Android)". O resto desta seção é do BSP Linux.

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
make ARCH=arm64 rockchip_linux_defconfig rk3566.config rk3566_hy300.config          # hy300-6.1
make ARCH=arm64 LLVM=1 LLVM_IAS=1 rockchip_defconfig android-14.config rk3566_hy300.config   # hy300-ack-6.1
```

No `hy300-ack-6.1` o fragmento muda em dois pontos (commit `a9ca5ee`): o Android exige
`CPU_FREQ`, `CPU_FREQ_STAT` e `CPU_FREQ_TIMES`, então o núcleo do cpufreq fica ligado e só os
drivers saem (`CPUFREQ_DT`, `ARM_ROCKCHIP_CPUFREQ`; sem driver a frequência não muda, como
antes), e `VT=y` volta para o fbcon existir. Os Mali Midgard e Utgard do `rockchip_defconfig`
também saem. A tabela abaixo continua valendo.

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

**Testado no aparelho em 22/11/2026: funciona.** O telnet abriu cerca de 20 s depois do reboot
(firmware carregado, conectado aos 27 s, gateway respondendo aos 28 s). O sysrq `b` pelo telnet
volta ao Android, que subiu com Wi-Fi. Retrato do hardware tirado pelo telnet (sem dados de
rede): placas ALSA `rockchip,rockchip-i2s-sound` e `rockchip,hdmiin`; entrada (IR, painel,
energia, receptor 2.4G) ok; no I2C0 os sensores aparecem sem driver (`gs_sc7a20` em 0x19, além
de 0x4c e 0x6b que a placa de referência declara); GPU `fde60000.gpu` sem driver (Mali desligado
no config; o caminho é o Panfrost); sem cpufreq (CPU fixa em 1104 MHz pelo SCMI); sem a classe
`motor_cc`; SoC a 67 °C. O driver do AIC8800 está com o log de depuração (`AICWFDBG`) ligado,
que enche o console: baixar o nível.

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
WIFI=1 kernel/build-marco1.sh                      # imagem com hy300.wifi=1 (+ .sha256), base ack
scripts/flash-test-recovery.sh ~/hy300-work/marco1-ack/recovery-marco1.img
# base bsp (hy300-6.1): KBASE=bsp WIFI=1 kernel/build-marco1.sh e ~/hy300-work/marco1/recovery-marco1.img
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
| módulo não carrega / chip não responde | `primeira carga falhou`, o estado do SDIO (`hy300: [sdio]`), `religando o chip`, e `FALHOU: ... (segunda tentativa)` se a segunda também falhar | reinicia em 2 min |
| sem `wlan0` | `FALHOU: nenhuma interface sem fio em 20 s` | reinicia em 2 min |
| senha errada, rede fora do alcance, roteador só WPA3 | `FALHOU: sem conexão em 60 s (estado SCANNING/4WAY_HANDSHAKE/...)` | reinicia em 2 min |
| conectou mas o PC não alcança | linhas de status normais | `ping`, ARP; esperar o prazo de 15 min |
| kernel trava ou dá panic no driver | log para | panic reinicia em 5 s; travamento sem panic: detectores e watchdog reiniciam (base ack, ver "Reinício sozinho em panic e travamento") |

### Falha do Wi-Fi no kernel ACK (22/11)

No BSP (`hy300-6.1`, GCC) o Wi-Fi funcionou; no ACK (`hy300-ack-6.1`, clang) falhou duas vezes.
Logs em `~/hy300-work/marco1-ack/resultado{,2}/console-ramoops-0.txt`.

- **Boot 1.** O cartão enumerou igual à fábrica (SDR104 a 50 MHz, fase 135) e o chip respondeu,
  mas cada resposta demorou mais que a anterior: a leitura da revisão levou 0,2 s, os dois
  blocos do `fw_adid` 1,7 s, os quatro primeiros do `fw_patch` uns 9 s, e o quinto estourou os
  3 s do `cmd_mgr` (`tkn[7] cmd:1035`, endereço `0x1e1000`). Na fábrica a carga inteira leva
  40 ms. Depois disso o núcleo MMC deu o cartão por removido (`-123`, `ENOMEDIUM`).
- **Boot 2.** Falhou no primeiro comando. O `sdio_clock=50000000` desse boot não mudou nada: no
  D80 o driver só imprime "FEATURE_SDIO_CLOCK 150 MHz", o `set_ios` que aplicaria o valor fica
  num `#if 0`, e o barramento já roda a 50 MHz pelo `max-frequency` do DT. O parâmetro foi
  revertido (kernel e `/init`). O chip continuava travado do boot 1: depois de uma falha nem o
  reboot quente nem o Android de fábrica o recuperam, só tirar da tomada.

O que não difere entre as árvores: `dw_mmc*`, o núcleo SDIO (`sdio_irq.c`, `sdio_io.c`,
`pwrseq_simple.c`), o nó `dwmmc@fe2c0000` do DT (só o nome) e o código do `aic8800_bsp`
(o `1e3aa6b` mexe só no `aic8800_fdrv`, em API do cfg80211). Sem LTO e sem CFI nos dois;
`VMAP_STACK` nos dois e os buffers de DMA do driver são `kmalloc`/`skb`. O que difere: clang 20 no
lugar do GCC, `PREEMPT` completo, `SHADOW_CALL_STACK`, `ARCH_DMA_MINALIGN` 64 (era 128; a linha
de cache do A55 é 64), os flags `claimed`/`retune_*` do `struct mmc_host` em campos de bit
(KABI do ACK) e o estado do chip no início do teste.

Hipóteses, da mais para a menos provável:

1. **A resposta do chip chega e o aviso não** (interrupção SDIO in-band atrasada ou perdida no
   ACK). Combina com respostas que chegam, mas cada vez mais tarde, até não chegarem. O
   caminho (dw_mmc → `sdio_irq_work` → tratador do `aic8800_bsp` → `busrx`) é o mesmo código nas
   duas árvores; a diferença teria de vir de compilador, preempção ou tempo.
2. **O chip começou o boot 1 num estado ruim** (firmware do Android ainda rodando, o pulso do
   `WL_REG_ON` no boot não reseta). O boot 2 mostra que um chip travado atravessa o reboot
   quente; contra: o teste do BSP partiu do mesmo jeito (`reboot-to-test-slot.sh` com o Wi-Fi do
   Android no ar) e funcionou.
3. **O chip demora porque recebe dado errado** (cache/DMA no envio). Menos provável: o CRC8 do
   cabeçalho e a resposta correta da revisão (7, U03) mostram que os comandos chegam inteiros.

O que mudou para o próximo teste:

- `aic8800_bsp` (kernel `f1fdbdc`): a resposta é esperada em fatias de 50 ms e, entre uma e outra,
  o driver lê o `misc_int_status` do chip; se houver resposta pendente, trata como a interrupção
  trataria. Log: os 8 primeiros comandos com 20 ms ou mais (`aicbsp: tkn[n] cmd c lento: envio
  X ms, resposta Y ms (achada por polling)`), um resumo no fim da carga (`aicbsp: N comandos,
  ... com resposta por polling, maior espera ...` e `aicbsp: interrupções SDIO ...`) e, no
  estouro, os registradores do chip lidos por CMD52 e o estado do host.
- `/init`: se a carga falhar, grava o estado do host SDIO (`hy300: [sdio]`: `ios` e `regs` do
  debugfs do dw_mmc, a linha do `fe2c0000` no `/proc/interrupts`, o `gpio-73` = `WL_REG_ON`),
  descarrega os módulos, desliga o host SDIO por 2 s (unbind do `dwmmc_rockchip`: o
  `mmc-pwrseq-simple` põe o `WL_REG_ON` em 0 e corta o 32 kHz), religa, espera o cartão da
  AICSemi (`vendor 0xc8a1`) e carrega de novo.

Como ler o próximo boot (tirar da tomada antes, para o chip partir do zero):

| No log | Conclusão |
|---|---|
| resumo com 0 lentos e `telnet` no ar | o problema era o estado do chip; o polling não foi preciso |
| comandos lentos "achada por polling" e carga completa | hipótese 1: a interrupção SDIO não chega no ACK (o polling contorna) |
| lentos sem polling, `envio` alto | o atraso está no envio (controle de fluxo ou `bustx`), não na resposta |
| estouro com `int_status 0x00` e CMD52 ok | o chip não respondeu: estado do chip (hipótese 2) ou dado errado (3) |
| estouro com `ret -110`/`-123` no CMD52 | o barramento SDIO morreu |
| `chip de volta no SDIO` e a segunda carga passa | o `WL_REG_ON` por 2 s destrava o chip sem tirar da tomada |

Imagem: `~/hy300-work/marco1-ack/recovery-wifi-diag.img` (kernel `4b06e02`, `WIFI=1`, com as
credenciais: não publicar), SHA-256 `ed6749becca5f13e4c456c2e01fbe412aebe31a2bc2a27b61eb2fdeda68321b1`.

## Reinício sozinho em panic e travamento (base ack)

Kernel `a1e01ec`..`4b06e02` do `hy300-ack-6.1`. Objetivo: qualquer panic ou travamento termina
num reinício normal (o pstore guarda o log e o próximo boot decide o que subir), nunca num
aparelho desligado.

| Caso | Quem pega | Tempo até reiniciar |
|---|---|---|
| panic, oops | `PANIC_ON_OOPS`, `PANIC_TIMEOUT=5` (sem depender da cmdline) | 5 s |
| CPU presa sem ceder (IRQs ligadas) | softlockup com panic | ~20 s + 5 s |
| CPU presa com IRQs desligadas | detector "buddy" do ACK (`HARDLOCKUP_DETECTOR_OTHER_CPU`): a CPU vizinha vê o hrtimer parado; panic | ~10 a 20 s + 5 s |
| tarefa em D por 120 s | hung task com panic (o padrão do ACK era 10 s) | 120 a 240 s + 5 s |
| todas as CPUs presas | watchdog do SoC: 1º estouro = pré-timeout (IRQ, panic), 2º = reset de hardware | até 2 TOPs |

- **Watchdog.** O núcleo do watchdog agora alimenta o dw-wdt armado cedo (`HY300_EARLY_BEACON`,
  89 s) até alguém abrir o `/dev/watchdog`; antes ninguém alimentava e um sistema sem daemon
  reiniciaria aos 89 s. O dw-wdt sobe no modo de pré-timeout (`DW_WATCHDOG_PRETIMEOUT_DEFAULT`,
  governador `panic`): o primeiro estouro vira panic e reinício normal com log; o segundo é o
  reset de hardware. O mesmo commit corrige o intervalo do ping do núcleo no modo de
  interrupção, que caía em cima do pré-timeout.
- **Reset do watchdog desligava o aparelho.** O dw-wdt usa o reset global escolhido no
  `CRU_GLB_RST_CON` (`0xfdd20000 + 0xdc`); no valor de reset (bit 1 = 0) é o "second global
  reset", e é ele que deixa o HY300 desligado. O reinício normal usa o "first global reset"
  (`CRU_GLB_SRST_FST`). `HY300_WDT_REBOOT` liga o bit 1 num `early_initcall` e escreve no log
  `hy300: watchdog com first global reset (CRU_GLB_RST_CON 0x... -> 0x...)`. O layout do
  registrador é o do RK3368/PX30 no U-Boot (bit 0 TSADC, bit 1 WDT); para o RK3568 ainda é
  hipótese até o teste do watchdog no aparelho. O TSADC fica como está.
- **Pseudo-NMI.** `ARM64_PSEUDO_NMI` vem compilado, mas não é padrão (a cmdline teria de ter
  `irqchip.gicv3_pseudo_nmi=1`): mexe na máscara de prioridades do GIC em toda interrupção e
  não foi testado com o TF-A de fábrica. O detector por perf/NMI do arm64 só existe a partir do
  6.4; o "buddy" do ACK não precisa de NMI, e o `PSCI SYSTEM_RESET` reinicia mesmo com uma CPU
  presa.
- **LKDTM** (`CONFIG_LKDTM=y`) para provocar cada caso pelo debugfs.

Teste no aparelho (como root, pelo telnet do modo Wi-Fi ou no Alpine). Cada linha é um boot;
em todos o esperado é voltar sozinho ao boot seguinte (no fluxo de teste, o Android de fábrica)
sem apertar o botão, e o log do panic aparecer no `console-ramoops-0`:

```sh
dmesg | grep 'first global reset'                       # bit do CRU_GLB_RST_CON
echo c > /proc/sysrq-trigger                              # panic: reinicia em ~5 s
echo HARDLOCKUP > /sys/kernel/debug/provoke-crash/DIRECT  # uma CPU presa sem IRQ: ~15 a 25 s
echo SOFTLOCKUP > /sys/kernel/debug/provoke-crash/DIRECT  # ~25 s
# todas as CPUs presas: só o watchdog do SoC sobra (pré-timeout não roda, vale o reset de
# hardware). Com o /init de teste (watchdog -T 60) leva até ~90 s. Se desligar em vez de
# reiniciar, o bit do CRU_GLB_RST_CON não é o certo.
for c in 0 1 2 3; do taskset -c $c sh -c 'echo HARDLOCKUP > /sys/kernel/debug/provoke-crash/DIRECT' & done
# pré-timeout sozinho: parar quem alimenta o watchdog (o /init de teste usa o applet watchdog)
kill -STOP $(pidof watchdog)                              # panic "watchdog pretimeout event" em ~45 s
```

## DVFS (base ack)

Kernel `875bf75` e `b9b6b61`. Até aqui a CPU ficava fixa em 1104 MHz, a DDR no que o loader
deixou e a GPU no clock do SCMI.

| Bloco | Driver | Faixa | Governador padrão (outros) |
|---|---|---|---|
| CPU (4x A55) | `rockchip-cpufreq` sobre o `cpufreq-dt`, `vdd_cpu` PWM | 408 MHz a 1,8 GHz (o máximo da fábrica) | schedutil (performance, ...) |
| DDR | `rockchip_dmc` + TF-A de fábrica (V1.02) | 780 MHz normal, 528 MHz no reboot, como na fábrica | `dmc_ondemand` da Rockchip (performance) |
| GPU | devfreq do Panfrost | 200 a 700 MHz, `vdd_fixed` 1,0 V fixo | simple_ondemand (performance) |

- **Tensões da CPU.** Tabela do BSP, escolhida pelo PVTM do OTP. Este chip (pvtm 89400, o que a
  fábrica também mede) cai na faixa L2 do BSP e na L1 da fábrica; o BSP dá 25 mV a mais em cada
  frequência (1,075 V contra 1,05 V em 1,8 GHz). Teto da tabela 1,15 V, do regulador 1,2 V.
- **GPU.** A tabela de OPP voltou ao nó, sem o `opp-supported-hw` (o núcleo de OPP descarta
  toda OPP com ele quando ninguém informa o hardware, e o Panfrost não informa). Os 800 MHz da
  fábrica ficam de fora, como no `rk3566-box.dtsi`.
- **Throttling.** `soc-thermal`: passivo em 75 e 85 °C (power allocator sobre CPU e GPU),
  crítico em 115 °C (desliga). Antes não havia quem resfriar.
- Barramentos (`ARM_ROCKCHIP_BUS_DEVFREQ`) e NPU continuam desligados.

Como conferir no aparelho:

```sh
cd /sys/devices/system/cpu/cpu0/cpufreq
cat scaling_available_frequencies scaling_available_governors scaling_governor
echo performance > scaling_governor; cat scaling_cur_freq cpuinfo_cur_freq   # 1800000
grep vdd_cpu /sys/kernel/debug/regulator/regulator_summary                    # ~1075 mV
dmesg | grep -e 'cpu cpu0' -e rockchip-dmc                                     # pvtm-volt-sel, rates
cat /sys/class/devfreq/dmc/cur_freq /sys/class/devfreq/dmc/available_governors
# carga nos 4 núcleos e temperatura a cada 5 s; acima de 85 °C o scaling_cur_freq tem de cair
for i in 1 2 3 4; do (while :; do :; done) & done
while :; do echo "$(cat /sys/class/thermal/thermal_zone0/temp) $(cat scaling_cur_freq)"; sleep 5; done
kill $(jobs -p)                                                                # fim da carga
# GPU (precisa do panfrost.ko: Alpine/Lineage; o initramfs de teste não o tem)
modprobe panfrost; cat /sys/class/devfreq/fde60000.gpu/available_frequencies
```

Imagem com tudo (Wi-Fi com diagnóstico, reinício em travamento e DVFS):
`~/hy300-work/marco1-ack-dvfs/recovery-marco1.img` (kernel `b9b6b61`, `WIFI=1`, com as
credenciais: não publicar), SHA-256 `edf6c8e0b5d4654c4328a739a2f33812791a58bcbf8cc43c059368c4f021caff`.
O smoke do QEMU passa nos três modos, mas o virt não tem nada disso: o DVFS só se prova no
aparelho. Para o teste do Wi-Fi, a imagem sem DVFS (`recovery-wifi-diag.img`) isola uma
variável.

## Pendências por driver

| Bloco | O que há no 6.1 | Falta |
|---|---|---|
| Wi-Fi AIC8800 (SDIO) | `aic8800_bsp` e `aic8800_fdrv` na árvore (`CONFIG_AIC8800=m`), carregados pelo `/init` com `hy300.wifi=1` | testar no aparelho ("Wi-Fi no 6.1"); Bluetooth (`aic8800_btlpm`) não foi portado |
| RK628 (entrada HDMI) | `VIDEO_RK628_CSI` (`drivers/media/i2c/rk628`) e `drivers/misc/rk628`, ligados no config | o nó está portado e desligado. Ligar depois que o display funcionar e conferir o caminho `csi2-dphy0` → `rkisp` |
| Motor de foco | nada. Na fábrica o nó `rk_motor` (`usb-cam-gpio`) não tem propriedades: o driver fechado da TXCZ fixa os GPIOs no código | escrever o driver a partir de `reverse-engineering/libfocus/README.md`, mantendo `/sys/class/motor_cc` |
| QMI8658 | sem driver. O chip nem está montado: no dmesg de fábrica o QMI8658 lê devid 0, e quem responde é o SC7A20 em `0x19` (id `0x11`) | conferir no relatório se o `gsensor` do SC7A20 aparece em `entrada` |
| Mali G52 | Panfrost (módulo) com devfreq | testar o devfreq e o throttling no aparelho |
| DVFS de CPU, DDR e barramentos | CPU, DDR e GPU ligados na base ack ("DVFS") | testar no aparelho; barramentos continuam desligados |
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
