# LineageOS 24.0 (Android 17) no HY300: inventário, decisões e plano

Estado em 23/11/2026: **primeiro build completo** do LineageOS 24.0 TV para o HY300, com GPU
aberta (Panfrost) e vídeo por hardware (Codec2 + MPP). Árvore em
`~/android/lineage/device/txcz/hy300` (GitHub `mateusseiboth/android_device_hy300_rk3566`, branch
`lineage-24.0`). Nada foi gravado no aparelho. Como compilar, onde
ficam os artefatos, como gravar pelo Alpine e os riscos estão em "Build e primeiro boot", logo
abaixo. O inventário e as decisões de antes seguem nas seções seguintes.

## Build e primeiro boot (22/11/2026)

### Onde está cada coisa

| O quê | Onde |
|---|---|
| Checkout `lineage-24.0` | `~/android/lineage` (no NVMe). Os objetos git (`.repo/project-objects`, 29 GB) foram para o HD ext4: `/mnt/hd/android-lineage/.repo/project-objects`, com link simbólico. O resto do `.repo` fica no NVMe: o sandbox (nsjail) do Lineage monta `.repo/manifests.git` com escrita (`BUILD_BROKEN_SRC_DIR_RW_ALLOWLIST`) e falha se o caminho passar por um link para outro sistema de arquivos |
| local_manifests | `.repo/local_manifests/hy300.xml` (árvore, este repositório em `vendor/hy300/hy300-rk3566`, aospext, codec2, libmpp, librga, libhardware_rockchip; os de terceiros fixados por commit), `hy300-remove.xml` (só `prebuilts/qemu-kernel` e os webview x86) e `hy300-prune.xml` (poda, abaixo). Os `kernel/prebuilts/*`, `common-modules/*` e `prebuilts/android-emulator` que tinham sido removidos voltaram: o Soong do 24.0 não analisa sem eles |
| Árvore do aparelho | `device/txcz/hy300` (não `device/hy300/rk3566`: o build só acha o `BoardConfig.mk` em `device/*/<PRODUCT_DEVICE>`, e o finder do Soong não segue link simbólico). `~/android/device-hy300` agora é link para lá |
| Kernel prebuilt | `kernel/build-lineage-kernel.sh` (este repo) gera `device/txcz/hy300/prebuilt/` de um commit fixo do `hy300-ack-6.1` (`git archive`, sem mexer no checkout do kernel) e grava o commit e os sha256 em `prebuilt/VERSION` |
| Ferramentas de host do Mesa | `device/txcz/hy300/tools/build-mesa-host-tools.sh` → `~/hy300-work/mesa-host/install/bin` (LLVM 22: o LLVM 23 do Fedora não compila o `clc_helpers.cpp` do Mesa 26.1-devel) |
| Logs | `~/hy300-work/lineage-build/m-*.log`, `~/hy300-work/lineage-kernel-build*.log` |

### Como compilar

```sh
cd ~/android/lineage
repo sync -c device/txcz/hy300 vendor/hy300/hy300-rk3566 vendor/glodroid/aospext hardware/rockchip/codec2 \
    hardware/rockchip/libmpp hardware/rockchip/librga hardware/rockchip/libhardware_rockchip
device/txcz/hy300/tools/apply_patches.py .                 # patches/ da árvore (codec2, librga)
device/txcz/hy300/tools/build-mesa-host-tools.sh .         # uma vez
~/hy300-handoff/hy300-rk3566/kernel/build-lineage-kernel.sh  # prebuilt/ (Image.gz, módulos, resource)
export PATH="$HOME/hy300-work/mesa-host/install/bin:$PATH"
export GOMEMLIMIT=20GiB SOONG_INCREMENTAL_ANALYSIS=false   # 31 GB de RAM: ver abaixo
export ALLOW_MISSING_DEPENDENCIES=true                     # poda do checkout: ver abaixo
source build/envsetup.sh && lunch lineage_hy300-cp2a-userdebug
nice -n 10 m -j12
python3 ~/hy300-handoff/hy300-rk3566/tools/lineage_prebuilt.py verify-boot \
    out/target/product/hy300/boot.img --factory-boot ~/hy300-backup/boot.img \
    --kernel-gz device/txcz/hy300/prebuilt/Image.gz
```

Dependências instaladas no Fedora: `lz4`, `ncurses-compat-libs`, `llvm22-devel`, `clang22-devel`,
`spirv-llvm-translator22-devel`, `libclc22-devel`, `spirv-tools-devel`, `glslang`, `python3-ply`,
`libdrm-devel`, `expat-devel` (meson, ninja, mako e pyyaml já existiam).

**Poda do checkout** (`hy300-prune.xml`, 132 projetos): `cts`, `test/vts-testcase/*` (menos `hal`), `system/software_defined_vehicle/*`, `hardware/qcom-caf/*`,
`hardware/qcom/*`, `vendor/qcom/opensource/*`, `device/qcom/*`, `device/google/{cuttlefish,
cuttlefish_prebuilts,cuttlefish_vmm,sdv,sdv_display_safety,trout}` e `device/google_car`. Nenhum
entra no produto do HY300 (`device/google/atv` fica). Os diretórios foram movidos para
`/mnt/hd/android-lineage/removed/<caminho>` (5,7 GB); os objetos git continuam no
`.repo/project-objects`. O build roda com `ALLOW_MISSING_DEPENDENCIES=true` para dependência de
teste desses projetos não parar a análise. Para voltar um projeto: apagar a linha dele no
`hy300-prune.xml` e `repo sync -l <caminho>` (ou mover o diretório de volta). Voltaram porque o produto depende deles
(o `ALLOW_MISSING_DEPENDENCIES` só adia o erro para o ninja): `platform_testing`
(`PlatformMotionTestingComposeValues`, do SystemUI), `test/vts-testcase/hal` (dirgroup do
trusty) e, como cópia parcial fora do controle do repo, `cts/libs/json` (`jsonlib`, do
`protologtool`) e `device/google/cuttlefish/apex/keys` (chave do APEX do Gatekeeper por
software). Conferência: os módulos com dependência ausente estão nas regras `missing
dependencies` dos `out/soong/build.*.ninja`; fora testes, nenhum pode sobrar.

**Memória**: a análise do Soong do 24.0 passa de 24 GB de RSS. Com 31 GB e a sessão do usuário
aberta, o primeiro `m` ficou mais de uma hora em swap, com ~1 min de CPU a cada 10. Ele foi
interrompido e relançado com `GOMEMLIMIT=20GiB` e `SOONG_INCREMENTAL_ANALYSIS=false` (sem
`--incremental-build-actions`), e travou do mesmo jeito: o heap vivo passa do que sobra da RAM.
Por isso a poda acima. Durante o build houve swap
temporário: 16 GB em `/mnt/hd/swap-build` e um `zram1` de 16 GB (zstd, prioridade 50), os dois
fora do fstab e removidos no fim. O que destravou a análise foi o `zram1`: o heap do Go comprime
bem; com ele a análise levou ~22 min.

### O que entrou no build

- **Produto**: Lineage TV (`atv_base.mk` + `common_full_tv.mk`), 64 bits, `atv_lowram_defaults.mk`,
  FCM 8, header v2, `lineage_hy300-cp2a-userdebug`, SELinux permissive pela cmdline.
- **Kernel**: `hy300-ack-6.1` como prebuilt (`Image.gz` com o DT embutido) + módulos da GPU
  (`drm_shmem_helper`, `gpu-sched`, `panfrost`) em `/vendor/lib/modules`, carregados no
  `early-init` pelo `modprobe` do vendor.
- **GPU (direto, sem passar por software)**: Mesa 26.1 do próprio `external/mesa3d` compilado
  pelo aospext do GloDroid (meson dentro do build), só o driver `panfrost`; `mesa_clc`,
  `vtn_bindgen2` e `panfrost_compile` vêm do host (`-Dmesa-clc=system -Dprecomp-compiler=system`).
  `ro.hardware.egl=mesa`, `drm.gpu.vendor_name=panfrost` (o EGL abre o nó do Panfrost, não o do
  rockchip), GLES 3.1. Composer: `android.hardware.composer.hwc3-service.drm` do AOSP. Gralloc:
  minigbm `generic`, **sem patch**: o rockchip é driver dumb no minigbm e o kernel Android libera
  `CREATE_DUMB` no render node (`drm_ioctl.c`, `DRM_RENDER_ALLOW`); o Panfrost importa por dma-buf.
- **Vídeo por hardware**: ver "Vídeo" abaixo.
- **Segurança por software**: `android.hardware.security.keymint-service` (C++ puresoft, exigido
  pelo FBE), `com.android.hardware.gatekeeper.nonsecure`, health de exemplo.
- **Rede**: só cabo por adaptador USB (`android.hardware.ethernet.xml`), até o Wi-Fi do ACK.
- **Desempenho**: CPU, GPU (devfreq do Panfrost) e DDR (`dmc`) no governador `performance` no
  `init.rk3566.rc`; o térmico do kernel limita por cima. lmkd por PSI com `kill_heaviest_task`,
  `thrashing_limit=30`, stall completo de 700 ms para virar crítico: o app de vídeo em primeiro
  plano é o último a sair. zram 75 % lz4, `swappiness=100`.
- **Animação de boot com log**: ver "Animação de boot" abaixo.
- **App de configurações do projetor** (`android/hy300-settings`, `HY300Settings`): compilado do
  fonte pelo `Android.bp` do app, priv-app no `/product` com a chave de plataforma, targetSdk 32.
  Abre pelo item "Projetor" do TvSettings do Lineage (ação `com.android.tv.settings.SOUND`, título
  e ícone vindos do app) e pela tecla F12. Motor e LEDs com 0666 no `init.rk3566.rc`, como a
  fábrica. **Sem efeito no primeiro build**: keystone (as props `persist.sys.keystone.*` são
  gravadas, mas ninguém lê até o patch do SurfaceFlinger), foco (depende do driver `motor_cc` no
  kernel Android), brilho/contraste/saturação/matiz (eram aplicados pelo HWC da Rockchip; o
  drm_hwcomposer não lê essas props), abrir HDMI (o app de câmera da Rockchip não existe) e o
  keystone automático (sem HAL de sensores).

### Vídeo por hardware (Codec2 + MPP)

Tudo fonte, por local_manifest, sem blob nos nossos repositórios:

| Projeto | Origem | Licença | O que faz |
|---|---|---|---|
| `hardware/rockchip/codec2` | `Lineage-Rockchip/android_hardware_rockchip_codec2` (`df12a8f`) | Apache-2.0 (cabeçalhos dos fontes) | serviço `android.hardware.media.c2@1.1-service` (HIDL 1.1, aceito no FCM 8), componentes `c2.rk.*` |
| `hardware/rockchip/libmpp` | `rockchip-linux/mpp` (`9b56348`, branch develop) | Apache-2.0 / MIT (`LICENSES/`) | `libmpp` do fonte (o `Android.bp` é do próprio MPP) |
| `hardware/rockchip/librga` | `Lineage-Rockchip/android_hardware_rockchip_librga` (`1a0f26b`) | Apache-2.0 (`COPYING`) | cópia/conversão por hardware (RGA) |
| `hardware/rockchip/libhardware_rockchip` | `Lineage-Rockchip/android_hardware_rockchip_libhardware_rockchip` (`ac66dee`) | **sem licença declarada** nos headers `gralloc_rockchip.h`, `hardware_rockchip.h`, `rga.h` (o `img_gralloc_public.h` é MIT) | só headers (constantes de formato e de uso do gralloc) |

Patches da árvore (`device/txcz/hy300/patches`, aplicados por `tools/apply_patches.py`):

1. `codec2/0001`: o namespace não importa mais `vendor/rockchip/rk35xx-common` (onde o
   Lineage-Rockchip pega `libmpp` e `librga` em binário); **sem NPU**: os modelos yolov5 `.rknn`
   não entram na imagem. O código do yolov5 continua compilado, mas só abre o `librknnrt.so` por
   `dlopen`, que não existe no aparelho: o modo "smart v3" do encoder cai no modo normal.
2. `codec2/0002`: **gralloc genérico (minigbm)**. O Codec2 da Rockchip foi escrito para o gralloc
   da Rockchip: aloca com `RK_GRALLOC_USAGE_SPECIFY_STRIDE` e outros bits privados, formato
   `HAL_PIXEL_FORMAT_YCrCb_NV12` (0x15, da Rockchip), e importa os buffers do gralloc direto no
   MPP. O minigbm recusa bit de uso desconhecido (`Unhandled gralloc usage`) e não conhece o 0x15.
   Com `C2_RK_GENERIC_GRALLOC` o decoder fica sempre em "buffer mode": o MPP decodifica nos buffers
   internos dele (dma-heap/drm) e cada quadro é copiado pela RGA (ou CPU, se a RGA falhar) para um
   bloco `YCBCR_420_888` (NV12 no minigbm) sem bits privados. Custo: uma cópia de RGA por quadro.
3. `librga/0001`: `librga` compilada do fonte no modo `android_ndk` do `CMakeLists.txt` (só a API
   por fd, sem o gralloc da Rockchip), que é o que o Codec2 usa.

`media_codecs.xml` / `media_codecs_c2_rk.xml` (vendor): decoders `c2.rk.{avc,hevc,vp9,vp8,mpeg2,
m4v,h263}` até **1920x1088** a 60 fps. O RK3566 faz H.264/HEVC/VP9 até 4K60, mas o painel é
1024x600 e os buffers de 4K não cabem bem em 1,5 GB; limitar faz o Netflix e o Crunchyroll pedirem
no máximo 1080p. Os codecs de software (`c2.android.*`) seguem disponíveis pelo APEX swcodec.

`/dev/mpp_service` e `/dev/rga` ficam `0660 system system` (o serviço roda como `mediacodec` com
grupo `system`). No kernel, o `rk3566-box-demo-v10.dtsi` liga rkvdec, vdpu, iep, jpegd e RGA.

Fica de fora por enquanto: **10 bits** (HEVC Main10, VP9 perfil 2) e **encoders**: o caminho de
P010 e o de entrada do encoder dependem dos bits de uso do gralloc da Rockchip. AV1 não existe no
RK3566.

### DRM (Netflix, Crunchyroll)

Netflix e Crunchyroll exigem **Widevine**. O HAL do Widevine (`android.hardware.drm-service.widevine`,
`libwvhidl`/`liboemcrypto`) é binário do Google, não existe no AOSP/Lineage e **não vai para os
nossos repositórios**. Sem ele os dois apps não tocam vídeo protegido. Com o Widevine num Lineage
não certificado o nível é **L3** (software) e o Netflix limita L3 a **SD** (até 480p);
Crunchyroll costuma aceitar mais. Não há como subir de nível sem certificação, e não se tenta
contornar. O Widevine de fábrica é de 32 bits (Android 12, vendor 32 bits) e não roda neste
Lineage só de 64 bits; um Widevine de 64 bits para Android 15/16 existe nos blobs do
Lineage-Rockchip (`proprietary_vendor_rockchip_rk35xx-common`), só como opção local do usuário.

### Animação de boot

A animação com log ao vivo do Android 12 (`android/bootlog`) entra no build pelo próprio repositório
(`vendor/hy300/hy300-rk3566/android/bootlog/Android.bp`), em duas versões: a **nativa em C++**
(`native/`, `/system_ext/bin/hy300-bootlog-native`: libgui + FreeType + libpng, logcat por
`popen`, desenha assim que o SurfaceFlinger sobe, sem ART; o estado fica em `bootlog_model`,
testado no host com gtest, `hy300-bootlog-model-test`) e a **Java** de antes (mesmo `Main.java`).
O `lineage/bootlog.sh` tenta a nativa; se ela não desenhar o primeiro quadro em 5 s, cai na Java
com o `bootanimation` mostrando o logo. Nenhuma das duas foi vista rodando ainda.

- tudo no `/product`: `framework/hy300-bootlog.jar` (o dex compilado pelo build, `java_library`),
  `media/bootlog/{bootlog.sh,logo.png}`, `etc/init/hy300-bootlog.rc` e
  `media/hy300-bootlog.zip`;
- o rc redefine o serviço `bootanim` com `override` (o `/product` é lido depois do `/system`);
- o zip de 1 quadro (o logo, 300x297, centralizado) é gerado no build (`genrule` com
  `soong_zip -L 0`) e escolhido por `ro.product.bootanim.file`, sem mexer no
  `bootanimation.zip` do Lineage (que fica no `/product/media` como fallback);
- diferenças do Android 17: caminho do ART `lib64` (só 64 bits), `classpath` do
  `derive_classpath` no mesmo `/data/system/environ/classpath`; o tamanho vem do modo do conector
  DRM ligado (`/sys/class/drm/card*-*/modes`, 1024x600 no HY300), não mais 1280x720 fixo.

Segue valendo: sai em `boot_progress_enable_screen` ou na transição 0→1 de
`service.bootanim.exit`, limite de 180 s pelo relógio monotônico (as duas versões), e se nada
desenhar fica o `bootanimation`. Com a Java o log só aparece quando o ART sobe (~20 s). A
cmdline não ganhou `console=tty0`/fbcon: o que se quer ver é a animação.

### Artefatos (build de 23/11/2026, `lineage_hy300-cp2a-userdebug`)

Cópia estável em `~/hy300-work/lineage-artifacts/` (o `out/` muda a cada build), com
`SHA256SUMS` e o `kernel-VERSION` do prebuilt:

| Arquivo | Tamanho | sha256 | Vai para |
|---|---|---|---|
| `boot.img` | 19,0 MiB | `c395bf147e6dec10454377ef945a22758d621b313294689aaf7baef228b7bebf` | partição `recovery` (o Alpine fica na `boot`) |
| `recovery.img` | 31,1 MiB | `5d4210d5d093372d8116ae07a4746a50c8b84381d66e3fa4e7c54c6f7609e589` | ainda não usar (recovery do Lineage; não há slot livre para ela agora) |
| `super.img` (sparse) | 1246 MiB | `e66db0528539ff7ee445ad49529e90834c5a26ae7c7f0681d7acc3928117fee2` | origem do `super.raw` |
| `super.raw` | 3.263.168.512 bytes (exato) | `b2885fefcecf90b4257678842deea75794d43aa6251b2aaab1a34ce96f514d12` | partição `super` |

- `boot.img` e `recovery.img` passam no `tools/lineage_prebuilt.py verify-boot` contra o
  `boot.img` de fábrica (header v2, endereços, página, ID do U-Boot, resource de fábrica, kernel
  igual ao `Image.gz`). Cmdline: `console=ttyFIQ0 firmware_class.path=/vendor/etc/firmware
  init=/init rootwait ro loop.max_part=7 printk.devkmsg=on androidboot.console=ttyFIQ0
  androidboot.hardware=rk3566 androidboot.boot_devices=fe310000.sdhci androidboot.selinux=permissive
  panic=5 androidboot.init_fatal_panic=true`. Ramdisk com o `init` do primeiro estágio e o
  `fstab.rk3566`.
- Kernel: `hy300-ack-6.1` em `9358ce442f3e` (`Image.gz` sha256 `42c2041a…2f2710`).
- `super`: metadado 10.0, 2 slots, grupo `rockchip_dynamic_partitions` (3.258.974.208 bytes),
  system 750 MiB, system_ext 151 MiB, product 289 MiB, vendor 60 MiB, odm 1 MiB (1,25 GB de 3,1).
- Conferido na imagem: Mesa (`libEGL_mesa`, `libGLESv2_mesa`, `libgallium_dri` 20 MB), hwc3,
  minigbm, Codec2 (`android.hardware.media.c2@1.1-service`, `libcodec2_rk_component`, `libmpp`,
  `librga`), `media_codecs*.xml`, `panfrost.ko` + `modules.load`, KeyMint, APEX do Gatekeeper,
  `HY300Settings` (priv-app) + privapp-permissions, bootlog (nativo, jar, script, zip, rc),
  `hy300-clear-bcb.sh`, `watchdogd` no `init.rk3566.rc`.

### Rodada 2: primeiro boot fechado, sem rede (23/11/2026)

O Lineage ainda não tem Wi-Fi: o primeiro boot é um ciclo fechado Alpine → Lineage gravando logs →
Alpine, sem ninguém olhando.

- **`hy300-diag`** (`configs/init/hy300-diag.sh` da árvore, testes em `tools/tests/test_diag.py`):
  só no userdebug (`ro.debuggable=1`), ligado por `androidboot.hy300.diag=1` na cmdline desta
  imagem (ou por `/metadata/hy300-diag/ativo`; o arquivo pode faltar). Começa no `post-fs` e
  grava em `/metadata/hy300-diag/<n>/` (`n` no arquivo `contador`; ficam as 3 últimas coletas,
  o metadata tem 16 MiB):
  - a cada 20 s: `dmesg.txt`, `logcat.txt` (`logcat -b all -d -v threadtime`), `getprop.txt`,
    cada um gravado num `.tmp` e renomeado, com `sync` depois;
  - depois do `boot_completed`, uma vez: `surfaceflinger.txt`, `media.txt` (`dumpsys
    media.player`), `hal.txt` (`lshal`), `meminfo.txt`, `freq.txt` (cpufreq, devfreq da GPU e da
    DDR, temperaturas), `lsmod.txt`, `ps.txt`;
  - `diag.txt`: linha do tempo (início, boot_completed, marca, reinício);
  - `wifi.txt`: teste do AIC8800 em segundo plano (abaixo).
  - Aos **480 s de uptime**, com ou sem `boot_completed`: grava a **marca de ficar do Alpine** na
    `misc` (0x10000, `hy300-ficar\0` + versão 1, o mesmo do `scripts/reboot-to-alpine.sh`; só
    se a área estiver zerada ou já marcada; o contador em 0x10010 não é tocado), `sync` e
    `setprop sys.powerctl reboot`. Reboot sem alvo: o init só grava BCB para `recovery`,
    `bootloader`, `quiescent`, `sideload` e `fastboot` (`system/core/init/reboot.cpp`), então o
    U-Boot sobe a `boot` (o Alpine), que fica no ar por causa da marca.
  - Se o boot travar antes do serviço: pré-timeout do watchdog e `panic=5` reiniciam, e o
    Alpine assume (sem a marca, ele segue o autoboot normal).
- **Wi-Fi AIC8800 sem HAL**: `aic8800_bsp`/`aic8800_fdrv` do mesmo `hy300-ack-6.1`
  (`9358ce442f3e`, que já tem o polling e os tempos da carga do firmware do `f1fdbdc`; o
  religamento do WL_REG_ON é do lado do usuário, `recover_wifi_chip` do `hy300-wifi.sh`), em
  `/vendor/lib/modules` (não carregam sozinhos: o ueventd não trata modalias). O firmware vai
  para `/vendor/etc/firmware/aic8800` **só no build local** (`prebuilt/firmware`, extraído do
  `vendor.img` de fábrica pelo `wifi_payload.py firmware`). O `hy300-diag` usa as funções do
  `kernel/initramfs-test/hy300-wifi.sh` (instalado em `/vendor/etc/hy300/` pelo `Android.bp` de
  lá): carrega os módulos, espera a interface 20 s, e se ela não vier grava o estado do SDIO,
  religa o chip e tenta de novo; sobe a interface e faz `iw dev <if> scan` com `timeout 60`. Do
  scan fica só a **contagem** de redes (nomes e endereços dos vizinhos não são gravados), mais os
  erros e as linhas `aic`/`rwnx`/`sdio`/`mmc1` do dmesg. Sem `wpa_supplicant`.

Artefatos da rodada 2 em `~/hy300-work/lineage-artifacts/` (a rodada 1 foi para `r1/`), com
`SHA256SUMS` e `kernel-VERSION`; `verify-boot` passa no `boot.img` e no `recovery.img`:

| Arquivo | Tamanho | sha256 |
|---|---|---|
| `boot.img` (vai na `recovery`) | 19.888.128 | `19989a453ed0a34954ae8de5a5db680c30a29a066f187dde2e691b8052aac803` |
| `recovery.img` | 32.614.400 | `79192bbea0c977b7ae9e2d6c927533e561da368379d21c7990b5384ba483d90a` |
| `super.img` (sparse) | 1.307.981.732 | `e04937eca1ceeae7984e33070f89f2c9206c48746da1499bc69ce2c8fd88c96e` |
| `super.raw` (vai na `super`) | 3.263.168.512 | `309713cfcf21655462784d0dff91b25fdbe529773d35a20d844a7a69f6628b81` |

Ler os logs no Alpine (o metadata é ext4 sem criptografia; `noload` não deixa o ext4 reproduzir o
journal e escrever na partição):

```sh
mkdir -p /mnt/metadata
mount -t ext4 -o ro,noload /dev/block/by-name/metadata /mnt/metadata
cat /mnt/metadata/hy300-diag/contador
ls /mnt/metadata/hy300-diag/$(cat /mnt/metadata/hy300-diag/contador)/
umount /mnt/metadata
```

Do PC: `ssh root@<IP> 'mount -t ext4 -o ro,noload /dev/block/by-name/metadata /mnt/metadata &&
tar -C /mnt/metadata -cf - hy300-diag; umount /mnt/metadata' > hy300-diag.tar`. A marca de ficar
é apagada pelo estágio 1 do Alpine no boot seguinte, como sempre. Para tirar o diag, basta gravar
um `boot.img` sem `androidboot.hy300.diag=1` (o `BoardConfig.mk` diz onde).

### Rodada 3: o que o primeiro boot mostrou (23/11/2026)

Logs em `~/hy300-work/lineage-artifacts/boot1/pstore.txt`. Funcionou: U-Boot com `Image.gz` na
`recovery`, kernel ACK, `super` e partições, bootlog nativo na tela, probe do Panfrost
(`mali-g52 id 0x7402`, 594 MHz). Falhou:

- **A, system_server**: `HintManagerService` sem `IPower`. `HintManagerService.java:323-334`:
  `mPowerHal = injector.createIPower()` (nulo sem HAL declarado), o `if (mPowerHal != null)`
  protege só a leitura, e a linha 334 faz `mSupportInfo.headroom.isCpuSupported` com
  `mSupportInfo` nulo. Corrigido com `android.hardware.power-service.example` (AOSP, IPower v7
  com `getSupportInfo`). Ver a tabela de HALs abaixo.
- **B, GPU**: aos 16,6 s `gpu sched timeout, js=1, config=0x7b00, status=0x8, head=tail` (o
  primeiro job nem andou), depois `js=0`. A thread `irq/73-panfrost` (MMU) prende a CPU0 em
  `panfrost_mmu_irq_handler_thread` → `shmem_read_mapping_page_gfp` (rcu stall aos 38 s, RT
  throttling), e aos 65,8 s o pré-timeout do watchdog dá panic com a thread `irq/74-panfrost` em
  `__pm_runtime_suspend`. Uma única interrupção de MMU no `/proc/interrupts`: a thread não sai
  do laço `while (status)` porque o registrador volta lixo/fica preso com a GPU sendo suspensa.
  Hipóteses, na ordem pedida:
  1. **OPP/tensão: descartada.** O DT de fábrica (`rk-kernel.dtb` do resource) tem a GPU no
     `vdd_fixed` (1,0 V fixo, `mali-supply`) e OPPs de 400 a 800 MHz com no máximo 1,0 V; 594 MHz
     a 1,0 V está dentro.
  2. **Nó da GPU: igual.** Interrupções SPI 39/41/40 = gpu/mmu/job (fábrica: `"GPU", "MMU",
     "JOB"` na mesma ordem; mainline: mesma atribuição), `clocks = <&scmi_clk 1>, <&cru CLK_GPU>`
     com `"gpu", "bus"` como no mainline, `power-domains` iguais. O que sobra do lado do kernel é o
     **runtime PM**: o panfrost do 6.1 não sincroniza nem desliga as IRQs antes de desligar a GPU
     (corrigido no upstream em "drm/panfrost: Synchronize and disable interrupts before powering
     off", 6.5). Isso casa com o trace (MMU girando enquanto o job suspende). **Para o worker do
     kernel**: backport desse commit (e dos que ele traz) no `hy300-ack-6.1`. Mitigação na
     árvore, sem mexer no kernel: `power/control=on` na GPU logo depois do `modprobe`.
  3. **Mesa 26.1 contra a UAPI 1.2**: o `panfrost_kmod.c` exige só 1.1 e trata os parâmetros que
     o kernel não tem (`SYSTEM_TIMESTAMP_FREQUENCY`, prioridades de contexto, coerência só ≥ 1.6).
     Não descartado, mas sem sinal no log.
  Teste barato que separa kernel de Mesa: `hy300-gpu-test` no Alpine (kmscube com o Mesa do
  Alpine no kernel BSP). Se travar igual, é kernel/DT; se rodar, olhar ACK e Mesa.
- **Chave de reserva da GPU**: `androidboot.hy300.gpu=sw|panfrost` na cmdline, decidida no
  `init.rk3566.rc` (`ro.hardware.egl`, `ro.hardware.vulkan` e `drm.gpu.vendor_name` saíram dos
  build.prop). `sw`: sem `panfrost.ko`, GLES pelo **ANGLE do sistema sobre o SwiftShader**
  (`vulkan.pastel`); `panfrost`: módulo + Mesa + GPU sempre ligada. O `boot.img` desta rodada sai
  com **`sw`**; o `boot-panfrost.img` é o mesmo com `panfrost` (`tools/lineage_prebuilt.py
  variant`, que refaz o ID). O Alpine também troca sem regravar: `hy300-kexec` com a cmdline
  alterada.
- **C, diag sem rastro**: o gatilho era `on post-fs && property:ro.debuggable=1`, e o LineageOS
  sai do userdebug com **`ro.debuggable=0`** (`vendor/lineage/config/common.mk`:
  `PRODUCT_NOT_DEBUGGABLE_IN_USERDEBUG := true`; `system/build.prop` da imagem tem
  `ro.debuggable=0`). O `post-fs` do `init.rk3566.rc` nem aparece no log. Agora
  `property:ro.build.type=userdebug` no `.rc` e no script. Novo teste do `.rc`
  (`tools/tests/test_init_rc.py`): todo `start` aponta para serviço definido, o diag começa num
  evento cedo, e **cada condição `ro.*` dos gatilhos é conferida contra os build.prop da imagem
  montada** (pegaria este erro) e as `ro.boot.hy300.*` contra a cmdline do `BoardConfig.mk`.
- **D, tela preta a quente**: sem log; provavelmente a mesma GPU. Com `sw` o próximo boot não
  passa pelo Panfrost.

Artefatos da rodada 3 em `~/hy300-work/lineage-artifacts/` (a rodada 2 foi para `r2/`), com
`SHA256SUMS`; `verify-boot` passa nos três boot.img:

| Arquivo | Tamanho | sha256 |
|---|---|---|
| `boot.img` (`gpu=sw`, vai na `recovery`) | 19.888.128 | `4960e653f1a4661eefcacf54c04b85234ddbc867d992b342e4baab69bb9c8a69` |
| `boot-panfrost.img` (`gpu=panfrost`) | 19.888.128 | `cf2b9c47a231d106e7a8d0c6d82574f8973d361e2057bb714a323ba51a67a333` |
| `recovery.img` | 32.614.400 | `7743e210c63d16966b8a1866e6b2227cf375eef00872dce34b67c18342187a69` |
| `super.img` (sparse) | 1.407.666.140 | `ca0de53289bd9c420a877de4ff7178de6b15dd87548a6bfbe4f0808e3fb79893` |
| `super.raw` (vai na `super`) | 3.263.168.512 | `f04c5b8cb8cda9f5facb6ec60e0e4a9128ef0a0a28bb7532ffe9216cd904e12a` |

#### HALs: o que o VINTF declara, a fábrica, o Lineage-Rockchip e o system_server

Fábrica: manifestos do `vendor.img` (Android 12). Lineage-Rockchip:
`android_device_rockchip_rk35xx-common` (lineage-23.2, blobs). "Procurado": linhas `Could not find
... in the VINTF manifest` do `pstore.txt` (o boot morreu no `HintManagerService`, então serviços
mais adiante não chegaram a procurar; os que procuram depois estão na tabela pelo código).

| HAL | Fábrica | Lineage-Rockchip | Procurado no boot | Decisão | Por quê (código do Lineage 24) |
|---|---|---|---|---|---|
| power `IPower` | sim | `power-service.rockchip` | system_server | **implementar**: `android.hardware.power-service.example` | `HintManagerService.java:323-334` (acima) |
| audio.core `IModule`/`IConfig`, audio.effect `IFactory` | HIDL 7.0 | HIDL | audioserver | **implementar**: APEX `com.android.hardware.audio` (exemplo AOSP, ALSA no card 0) | sem módulo primário o audioserver fica sem saída; o `audioserver.rc` tenta `vendor.audio-hal-aidl` e falha |
| power.stats | não | não | system_server | tolera | `PowerStatsHALWrapper.java:351-352`: `if (binder != null)` |
| memtrack | não | `memtrack-service.rockchip` | system_server | tolera | `MemtrackProxy.cpp:44-49`: sem declaração devolve `nullptr` |
| light | sim | `lights-service.rockchip` | system_server | tolera | `LightsService.java:995-997`: `if (binder != null)` |
| sensors | sim | não | system_server | tolera | `SensorDevice.cpp:72-75`: `if (!connectHalService()) return;` |
| thermal | não | `thermal-service.rockchip` | (depois) | tolera | `ThermalManagerService.java:1517-1520`: `waitForDeclaredService` + `return mInstance != null` |
| usb, usb.gadget | não | blobs | usbd | tolera | `usbd.cpp:69` (`isDeclared`), `UsbPortAidl.java:199-201` e `UsbGadgetAidl.java:94-96` (`isServicePresent` = `isDeclared`) |
| boot `IBootControl` | não | só recovery | vold | tolera (sem A/B) | `Checkpoint.cpp:143-144` (`if (module)`), `RecoverySystemService.java:325-326` (`isDeclared`) |
| net.nlinterceptor | não | não | wificond | tolera | `libnlinterceptor.cpp:77-79`: sem declaração, `return false` |
| vibrator | não | não | (depois) | tolera | `VintfHalVibratorManager.java:57`: `isDeclared` |
| weaver, authsecret, oemlock, secretkeeper, rebootescrow | weaver sim | não | (depois) | tolera | `SyntheticPasswordManager.java:629-632`, `LockSettingsService.java:1027-1030`, `VendorLockAidl.java:34`, `RecoverySystemService.java:579-582`, `RebootEscrowProviderHalImpl.java:45-47` |
| tv.input | não | HIDL 1.0 | (depois) | tolera | `JTvInputHal.cpp:48-55` devolve `nullptr`; `TvInputHal.java:94-165` confere `mPtr == 0` |
| hdmi.cec, hdmi.earc, hdmi.connection | não | não | (depois) | tolera | `HdmiCecController.java:953-956` e `966-969`, `HdmiEarcController.java:66-68` |
| wifi, supplicant, hostapd | sim (32 bits) | só libs | — | ausente (Wi-Fi ainda não) | `SystemServer.java:2257`: o WifiService só sobe com `FEATURE_WIFI`, que a imagem não declara |
| bluetooth | sim | sim | — | ausente | `SystemServer.java:1803-1805`: sem `FEATURE_BLUETOOTH` não sobe o serviço (o stack faria `assert` em `hci_hal_impl_android.cc:220` sem HAL) |
| camera.provider | sim | HIDL | — | ausente | entrada HDMI fica para depois |
| drm (Widevine/ClearKey) | sim | ClearKey | — | ausente | Widevine é blob (seção DRM) |
| health, keymint, secureclock, sharedsecret, gatekeeper, allocator, composer3, mapper, media.c2 | sim | sim | — | **presentes** | — |

Conferência no host antes de cada boot: `device/txcz/hy300/tools/check_vintf_hals.py
out/target/product/hy300` lê os manifestos do vendor, do odm e dos APEX de vendor (extraídos pelo
check_vintf do build) e falha se faltar algum de `configs/vintf/required_hals.txt` (power, audio
core/config/effect, health, keymint, allocator, composer3, gatekeeper, media.c2). Na imagem da
rodada 2 ele acusa exatamente power e áudio.

### Gravar pelo Alpine

O Alpine de recuperação fica na `boot`; o Android vai na `recovery` e o Alpine entra nele com
`hy300-android` (`reboot(RESTART2, "recovery")`). Então o `boot.img` do Lineage vai na
**`recovery`**, e a `boot` (Alpine) não muda. No PC, com o IP do Alpine:

```sh
cd ~/hy300-handoff/hy300-alpine
A=~/hy300-work/lineage-artifacts
(cd $A && sha256sum -c SHA256SUMS)
# 0) backup do que vai mudar (o de fábrica já está em ~/hy300-backup)
scripts/hy300-backup.sh <IP> ~/hy300-backup/antes-lineage-$(date +%F) super recovery misc metadata cache
# 1) super crua (já convertida com simg2img; 3.263.168.512 bytes, o tamanho da partição)
scripts/hy300-flash-partition.sh <IP> super $A/super.raw
# 2) boot.img do Lineage na recovery
scripts/hy300-flash-partition.sh <IP> recovery $A/boot.img
```

No aparelho (SSH no Alpine), metadata e userdata limpos (autorizado: o `/data` do Android 12 tem
FBE v1 e não serve):

```sh
dd if=/dev/zero of=/dev/block/by-name/metadata bs=1M          # 16 MiB, inteira
dd if=/dev/zero of=/dev/block/by-name/userdata bs=1M count=64  # some o superbloco
sync
hy300-android                                                   # reboot para a recovery = Lineage
```

O `fstab.rk3566` marca `/metadata` e `/data` como `formattable`: com o superbloco zerado, o
primeiro estágio formata o `/metadata` (ext4) e o `mount_all` formata o `/data` (ext4, liga
`encrypt` e `quota` sozinho pelo `tune2fs`, FBE v2 `aes-256-xts:aes-256-cts:v2`,
`reservedsize=128M`, `checkpoint=block`, sem casefold/projid). Se preferir formatar pelo Alpine:

```sh
mkfs.ext4 -F -L metadata -b 4096 /dev/block/by-name/metadata
mkfs.ext4 -F -L userdata -b 4096 -O encrypt,quota /dev/block/by-name/userdata
```

Não é f2fs: o fstab do Lineage usa ext4 nas duas, como a fábrica. A `cache` (ext4 de fábrica)
fica como está.

Voltar ao Android 12: gravar `~/hy300-backup/super.img` (descomprimido) na `super`, o
`~/hy300-backup/recovery.img` na `recovery` e zerar `metadata`/`userdata` do mesmo jeito.

### Contra bootloop (primeiro boot sem ninguém olhando)

- **BCB**: `hy300-clear-bcb` (o mesmo script do `android/clear-bcb` do hy300-alpine, com o teste
  portado para `tools/tests/test_clear_bcb.py` da árvore) roda no `post-fs-data` e no
  `sys.boot_completed=1` e apaga só um `boot-recovery` nos 2048 bytes do `bootloader_message`.
  Assim um "reboot recovery" ou "redefinir para a fábrica" no Lineage não prende o aparelho no
  slot `recovery`: o próximo boot volta ao Alpine. Vale a partir do `post-fs-data`; se o Lineage
  morrer antes disso com o BCB gravado, o U-Boot sobe a `recovery` de novo (ver panic abaixo).
- **cmdline**: `panic=5 androidboot.init_fatal_panic=true` (mais `CONFIG_PANIC_TIMEOUT=5`,
  `PANIC_ON_OOPS`, softlockup e hung task em panic no kernel). Erro fatal do init vira panic e
  reboot normal em 5 s, e o U-Boot sobe a `boot` (o Alpine). O `init_fatal_reboot_target` não é
  usado (bug de `sizeof` no init).
- **Watchdog**: o kernel é o `hy300-ack-6.1` em `9358ce442f3e` (topo do branch quando o prebuilt
  foi gerado), com `HY300_WDT_REBOOT`/`HY300_EARLY_BEACON` (CRU_GLB_RST_CON bits 1 e 4: o reset
  do watchdog reinicia e não reseta o PMU), `DW_WATCHDOG` com pré-timeout em panic e
  `WATCHDOG_HANDLE_BOOT_ENABLED` (o kernel alimenta até alguém abrir o `/dev/watchdog`). No
  Lineage o `watchdogd` do AOSP (`/system/bin/watchdogd 10 20`, `oom_score_adjust -1000`,
  classe `core`) passa a alimentar a cada 10 s com timeout de 30 s.
- **misc 0x10000/0x10010** (marca de ficar e contador do Alpine): nada do Lineage escreve lá. O
  layout do AOSP (`bootloader_message_core.h`) usa só os primeiros 64 KiB: BCB em 0–2 KiB,
  vendor em 2–16 KiB, wipe package em 16–32 KiB, "system space" em 32–64 KiB (termina em
  0x10000, exclusivo), e a árvore não muda `BOARD_RECOVERY_BLDRMSG_OFFSET`. Não há
  `misc_writer` nem HAL de boot que use a `misc`.
- Um laço ainda possível: se o Lineage der panic sempre no mesmo ponto, o ciclo é Alpine →
  contagem → Lineage → panic → Alpine. O contador de falhas do Alpine só conta o próprio Alpine;
  para parar no Alpine, `hy300-ficar`.

### Riscos do primeiro boot

| Risco | Sinal | O que fazer |
|---|---|---|
| U-Boot não descomprime o `Image.gz` de um boot.img Android | logo parado, ventoinha não liga | o Alpine já provou `Image.gz` na `boot`; se falhar na `recovery`, gerar boot.img com a `Image` crua (cabe nos 108 MiB da `recovery`) |
| Primeiro estágio não acha a `super` | reboot para o U-Boot/Alpine pelo contador de boots falhos | conferir `androidboot.boot_devices=fe310000.sdhci` contra `/sys/devices/platform` no Alpine |
| Panfrost/Mesa não sobe | SurfaceFlinger reiniciando, tela preta depois do logo | `adb logcat` por cabo de rede (`adb connect`); plano B: `ro.hardware.egl` vazio e renderização por software só para diagnosticar |
| drm_hwcomposer no VOP2 do BSP | tela preta com SurfaceFlinger vivo | `dumpsys SurfaceFlinger`, `modetest` no Alpine |
| KeyMint por software + FBE | vold falha, volta para a recovery do Lineage pedindo para formatar | formatar `/data` de novo; conferir o serviço KeyMint no logcat |
| Codec2 em buffer mode | vídeo verde/borrado ou cai para `c2.android.*` | `dumpsys media.player`, logcat `C2RKMpiDec`; desligar com `media_codecs` vazio |
| 1,5 GB de RAM | launcher recarregando | ajustar lmkd/zram depois de medir |
| Seccomp do Codec2 (política do Android 14 no 17) | serviço c2 morre ao iniciar | logcat `minijail`; ajustar a política |

### O que falta

- **Wi-Fi**: depende do driver AIC8800 no kernel Android (outro trabalho). Quando funcionar: módulos
  em `prebuilt/modules`, firmware (blob, só local), `wpa_supplicant` e HAL Wi-Fi (`BOARD_WLAN_DEVICE`).
- **Áudio**: HAL AIDL de referência com tinyalsa no card 0. Sem ele não há som.
- **Widevine** (acima), Bluetooth, sensores (SC7A20), IR (keylayout já existe).
- **Vídeo 10 bits e encoders** no caminho do minigbm; Codec2 sem cópia (importar os buffers do
  minigbm direto no MPP) depois de medir.
- **sepolicy** própria e SELinux enforcing.
- **Keystone** no SurfaceFlinger, app de configurações como app de plataforma, entrada HDMI.
- **bootlog nativo** (C++), recovery do Lineage, OTA.

## Resumo das decisões

| Tema | Decisão | Por quê |
|---|---|---|
| Produto | **LineageOS para TV** (`atv_base.mk` + `common_full_tv.mk`) | existe no lineage-24.0 (ver "Produto") e traz as Configurações do Android TV |
| ABI | só 64 bits (`core_64_bit_only.mk`) | um zygote só; o kernel já é arm64. Apps só armeabi-v7a deixam de rodar |
| RAM | `atv_lowram_defaults.mk` (low_ram, perfis de boot de TV, speed-profile) + zram 75 % | 1,5 GB; a fábrica já era Android Go (`ro.config.low_ram=true`, `gmsversion 12_202201.go`) |
| Kernel | 6.1, com **FCM nível 8** no manifesto | no Android 17 o 6.1 só é aceito pela matriz de nível 8 |
| Base do kernel | **feito (22/11): branch `hy300-ack-6.1`**, patches do HY300 sobre o kernel Rockchip Android (ACK `android14-6.1` + BSP) 6.1.172 do Lineage-Rockchip, clang 20 | o nosso `develop-6.1` é o BSP Linux, sem ashmem, dm-default-key, cpufreq_times, uid_sys_stats e xt_quota2. O `.config` novo não tem diferença contra o `u/android-6.1` |
| Boot | boot.img **header v2**, sem `vendor_boot`, resource.img de fábrica na seção `second`, kernel comprimido | é o que o U-Boot de fábrica já boota; a `Image` crua não cabe nos 40 MiB da `boot` |
| Gráficos | **Mesa Panfrost + drm_hwcomposer + minigbm** (sem blobs) | repositório público; os blobs Mali G52 de 64 bits existem, mas não podem ir para o repo |
| Keystone | reimplementar no **SurfaceFlinger/RenderEngine** com a mesma API de props `persist.sys.keystone.*` | o app de configurações continua igual; Skia aplica a homografia dos 4 cantos |
| Vídeo | primeiro só codecs de software; depois MPP + Codec2 da Rockchip (código aberto) | MPP e Codec2 têm fonte pública; exigem adaptar ao minigbm |
| Teste sem tocar na `super` | Lineage no slot `recovery` com a `super` e o `/data` **num pendrive** na porta USB-A | nada no eMMC muda além da `recovery` |

## Produto: Lineage TV existe no 24.0

Evidência no checkout (`~/android/lineage/.repo/manifests`, branch `lineage-24.0`, commit
`913c6ba` de 14/11/2026):

- `snippets/lineage.xml`: `device/lineage/atv` (LineageOS/android_device_lineage_atv),
  `packages/apps/Catapult` (launcher de TV do Lineage), `packages/apps/LineageCustomizer`;
- `default.xml`: `device/google/atv` (LineageOS/android_device_google_atv),
  `packages/apps/TvSettings` (LineageOS/android_packages_apps_TvSettings),
  `packages/inputmethods/LeanbackIME`;
- `device/lineage/atv` já baixado (commit `dbea85e`, 07/11/2026): `lineage_atv.mk` instala o
  `TvSettingsTwoPanel`, keylayouts de controles e overlays;
- `vendor/lineage` (GitHub, branch lineage-24.0): `config/common_full_tv.mk` →
  `common_tv.mk` → `common.mk` + `device/lineage/atv/lineage_atv.mk` + LeanbackIME,
  Catapult, LineageCustomizer, overlay `vendor/lineage/overlay/tv`;
- `device/google/atv/products/atv_lowram_defaults.mk`: o perfil de TV com pouca RAM.

Exemplo de aparelho Rockchip de TV no Lineage (lineage-23.2, organização Lineage-Rockchip
no GitHub): `android_device_h96_v58/lineage_v58.mk` faz exatamente `PRODUCT_IS_ATV := true`,
`atv_base.mk` e `common_full_tv.mk`. O `lineage_hy300.mk` segue esse modelo. O plano B
(Lineage comum com launcher de TV) não foi preciso.

As "Configurações do Android" do Lineage TV são o TvSettings TwoPanel, o mesmo sabor que hoje
é forçado por overlay no Android 12 (`android/hy300-settings/README.md`).

## Inventário: partições

GPT de `~/hy300-backup/gpt_head.bin` (eMMC de 15.269.888 setores, ~7,3 GiB):

| # | Partição | Início (setor) | Tamanho | No Lineage |
|---|---|---|---|---|
| 1 | security | 8192 | 4 MiB | intocada |
| 2 | uboot | 16384 | 4 MiB | intocada (U-Boot 2017.09 #txcz) |
| 3 | trust | 24576 | 4 MiB | intocada |
| 4 | misc | 32768 | 4 MiB | BCB da recovery (o Lineage usa `/misc` como a fábrica) |
| 5 | dtbo | 40960 | 4 MiB | intocada (o U-Boot aplica no DT de fábrica) |
| 6 | vbmeta | 49152 | 1 MiB | intocada (sem AVB) |
| 7 | boot | 51200 | 40 MiB | boot.img v2 do Lineage |
| 8 | recovery | 133120 | 108 MiB | slot de teste; depois a recovery do Lineage |
| 9 | backup | 354304 | 372 MiB | intocada |
| 10 | cache | 1116160 | 384 MiB | `/cache` |
| 11 | metadata | 1902592 | 16 MiB | `/metadata` |
| 12 | baseparameter | 1935360 | 1 MiB | intocada (parâmetros de display da Rockchip) |
| 13 | cust | 1937408 | 64 MiB | intocada, não montada |
| 14 | super | 2068480 | 3112 MiB (3.263.168.512 bytes) | partições dinâmicas |
| 15 | userdata | 8441856 | 3334 MiB | `/data` |

`super` (lpdump do primeiro 2 MiB de `super.img.gz`, sem descompactar o resto): metadado v10.0,
2 slots de metadado, **sem A/B** (nomes sem sufixo), grupo `rockchip_dynamic_partitions` com
3.258.974.208 bytes:

| Partição | Setores | Tamanho |
|---|---|---|
| system | 1.515.296 | 740 MiB |
| system_ext | 150.592 | 74 MiB |
| vendor | 703.512 | 344 MiB |
| vendor_dlkm | 41.752 | 20 MiB |
| odm | 587.848 | 287 MiB |
| odm_dlkm | 512 | 0,25 MiB |
| product | 790.320 | 386 MiB |

Ocupado: 1850 MiB; livre no grupo: ~1257 MiB.

fstab de fábrica (`/vendor/etc/fstab.rk30board`, extraído do `vendor.img` com `debugfs`):

- system, vendor, odm, system_ext, vendor_dlkm, odm_dlkm, product: `ext4 ro`, `logical,first_stage_mount`;
- `/metadata` ext4 `formattable,first_stage_mount`; `/cache` ext4; `/misc` emmc; `/cust` ext4;
- `/data` **ext4** com `fileencryption=software` (FBE v1), `quota`, `reservedsize=128M`,
  `checkpoint=block`; **sem** criptografia de metadado (a linha f2fs com `metadata_encryption`
  está comentada). `ro.crypto.type=file`, `ro.crypto.uses_fs_ioc_add_encryption_key=true`;
- zram `zramsize=75%,zram_backingdev_size=256M`.

O que se reaproveita sem reparticionar: tudo. `boot`, `recovery`, `cache`, `metadata`,
`userdata` e a `super` têm o tamanho certo para o Lineage TV. A `super` tem 3,1 GB; um Lineage TV
de 64 bits cabe com folga (tamanho real só depois do primeiro build). O `/data` precisa ser
formatado na troca (FBE v1 → v2).

## Inventário: hardware e como a fábrica fala com ele

| Bloco | Fábrica (Android 12, vendor 32 bits) | Evidência | No Lineage |
|---|---|---|---|
| Display | painel LVDS 1024x600; a ROM renderiza 1280x720 e o HWC escala. HWC `hwcomposer.rk30board.so` (HIDL composer 2.1), gralloc 4.0 da Rockchip | `vendor/etc/vintf/manifest.xml`, `persist.vendor.framebuffer.main=1280x720@60` | drm_hwcomposer (`android.hardware.composer.hwc3-service.drm`) no `card0-LVDS-1`, **1024x600 nativo**, densidade 170 |
| Keystone | SurfaceFlinger com patch RK + `/system/lib/librkgfx_dc.so` (fechada, 32 bits), props `persist.sys.keystone.*` | `reverse-engineering/display/README.md` | patch no SurfaceFlinger (ver "Keystone") |
| GPU | Mali-G52 com `libmali` (blob), `ro.hardware.egl=mali`, módulo `bifrost_kbase` | `vendor/etc/init.insmod.cfg`, props | Panfrost (kernel `drivers/gpu/drm/panfrost` existe no 6.1 e aceita `arm,mali-bifrost`) + Mesa |
| Gralloc | `android.hardware.graphics.allocator@4.0` da RK | manifesto VINTF | minigbm (`android.hardware.graphics.allocator-service.minigbm`, `mapper.minigbm`) |
| Vídeo | Codec2 `c2.rk.*` (avc, hevc, vp9, vp8, mpeg2, m4v, h263 dec; avc, hevc enc) em `libcodec2_rk_component.so` + `libmpp.so`, kernel `mpp_service` | `vendor/etc/media_codecs_c2_base.xml`, `vendor/lib` | software primeiro; depois MPP + Codec2 de fonte aberta |
| Áudio | HAL `audio.primary.rk30board.so` (HIDL 7.0). Card 0 I2S1 (codec mudo, alto-falante), card 1 I2S3 captura do RK628 | `docs/hdmi-audio.md`, `audio_policy_configuration.xml` | HAL AIDL de referência do AOSP com tinyalsa no card 0; captura HDMI pelo TV input |
| Wi-Fi | AIC8800D80 por SDIO, `aic8800_bsp.ko` + fdrv, `libwifi-hal-aic.so` (fechada) | dmesg `aicbsp_sdio_probe ... USE AIC8800D80`, `vendor/lib` | driver aberto (porte em andamento por outro trabalho), nl80211, wpa_supplicant do AOSP |
| Bluetooth | AIC8800 por **UART1 (`/dev/ttyS1`) a 1,5 Mbaud**; o patch do BT é carregado pelo `aic8800_bsp` pelo SDIO; `libbt-vendor_aic.so` (fechada) ajusta baud e sono; HIDL bluetooth 1.0 | `vendor/etc/bluetooth/bt_vendor.conf`, dmesg `aicbt_patch_table_load ... uart_baud 1500000` | `hci_uart` (H4) do kernel + HAL AIDL padrão do AOSP. A conferir: o que o `libbt-vendor_aic` faz além do baud |
| Controle IR | `remotectl-pwm` no PWM3, tabelas no DT, `/vendor/usr/keylayout/fdd70030_pwm.kl` | `vendor/usr/keylayout` | mesmo driver no 6.1; keylayout próprio na árvore |
| Teclas do painel | `adc-keys` (SARADC canal 1) e `gpio-keys` (energia) | DT | `Generic.kl` resolve (BACK, DPAD, ENTER, POWER) |
| Motor de foco | driver fechado da TXCZ (`usb-cam-gpio`), `/sys/class/motor_cc/motor_cc/{motor,hd_camera_on}`; o controle IR mexe no motor dentro do kernel | `reverse-engineering/libfocus/README.md` | driver novo no kernel com a mesma interface sysfs (pendente) |
| LEDs/ventoinha | `gpio-leds`: `green`, `red`, `Fan_h`, `Lcd_power` | `docs/kernel-6.1.md` | iguais no 6.1; permissões no `init.rk3566.rc` |
| Acelerômetro | SC7A20 no I2C0 pelo framework `gsensor` da Rockchip + `sensors@1.0` da RK (fechado) | dmesg, manifesto | driver `sc7a20` existe no 6.1; falta um HAL de sensores (AIDL) |
| Entrada HDMI | RK628 → MIPI-CSI → rkisp; app `com.android.rockchip.camera2` (rkCamera3) + camera provider 2.4 legado | `docs/hardware.md` | driver RK628 existe no 6.1 (desligado); TV input HAL próprio ou câmera externa do AOSP; app aberto |
| Vendor storage | `/dev/vendor_storage` (ioctl); id 50 = modo de instalação, lido pelo U-Boot para girar o logo | `reverse-engineering/MAP.md` | `rk_vendor_storage` existe no 6.1; nó 0660 system no ueventd |
| Segurança | KeyMint, Gatekeeper e Weaver no OP-TEE (TA fechada) | manifesto VINTF | KeyMint/Gatekeeper por software no começo |
| PQ | `libpq.so`/`librkswpq.so` (fechadas) | `reverse-engineering/display/README.md` | sem PQ; brilho/contraste/saturação pela matriz de cor do SurfaceFlinger |

Props da TXCZ que o app `io.github.hy300.settings` usa, e quem passa a ler cada uma:

| Prop | Hoje quem lê | No Lineage |
|---|---|---|
| `persist.sys.keystone.{lt,lb,rt,rb,update}` | SurfaceFlinger + librkgfx_dc | o patch de keystone no SurfaceFlinger, mesmo formato ("x,y" em px de 1280x720) |
| `persist.sys.keystone.*.init.xy`, `persist.txcz.install.model`, `persist.txcz.trapezoid.*`, `persist.txcz.screen.*` | só o app | só o app (estado dele) |
| `persist.txcz.source`, `persist.txcz.boot.app` | `services.jar` da TXCZ | o próprio app (BootReceiver abre o app escolhido) |
| `persist.vendor.{brightness,contrast,saturation,hue}.main` + `vendor.display.timeline` | HWC da Rockchip | não existe no drm_hwcomposer; trocar pela matriz de cor do SurfaceFlinger |
| `persist.bluetooth.rka2dpsink` | pilha BT da Rockchip | A2DP sink do AOSP (`bluetooth.profile.a2dp.sink.enabled`), a conferir |
| vendor storage id 50 | U-Boot | o app grava pelo `/dev/vendor_storage` (precisa de um auxiliar nativo) |

O app hoje grava props com `setprop` porque o SELinux está permissive. No Lineage ele vira
**app de plataforma** (`android_app_import` com `certificate: "platform"`), com
`property_contexts` próprios para `persist.sys.keystone.` e `persist.txcz.`, e com acesso aos
sysfs do motor e dos LEDs pela sepolicy. Assim funciona com o SELinux enforcing.

## Kernel

### O que o Android 17 aceita

`android-17.0.0_r1`, `hardware/interfaces/compatibility_matrices/Android.bp`: o framework
aceita aparelhos com FCM 7, 8, 202404, 202504 e 202604. Os kernels de cada nível:

| FCM | Kernels |
|---|---|
| 7 (Android 13) | 5.10, 5.15 |
| 8 (Android 14) | 5.15, **6.1** |
| 202404 (15) | 6.6 |
| 202504 (16) | 6.12 |
| 202604 (17) | 6.18 |

Logo o manifesto do HY300 declara `target-level="8"`. Os requisitos de config estão em
`kernel/configs/u/android-6.1/` (LineageOS/android_kernel_configs, branch lineage-24.0):
`android-base.config` + `android-base-conditional.xml`, `minlts="6.1.0"`.

### O nosso 6.1 contra esses requisitos

Ferramenta nova: `tools/kconfig_check.py` (testes em `tests/test_kconfig_check.py`).

```sh
python3 -I tools/kconfig_check.py <kernel_configs>/u/android-6.1 <build>/.config --kernel-version 6.1.172
```

Com o `.config` do marco 1 (`rockchip_linux_defconfig` + `rk3566.config` + `rk3566_hy300.config`):
**170 diferenças**, versão ok (6.1.172 >= 6.1.0). Quase tudo é config de um kernel Linux comum:
binder/binderfs, SELinux e audit, BPF e cgroup BPF, netfilter e xt_*, fscrypt e fs-verity,
dm-verity/dm-snapshot, PSI, taskstats, `CPU_FREQ`, `PREEMPT`, `MODVERSIONS`, `SHADOW_CALL_STACK`,
e o que é proibido (`DEVMEM`, `FHANDLE`, `FW_CACHE`, `MODULE_FORCE_UNLOAD`, `NFS_FS`, `SYSVIPC`).
Três exigem **clang/LLVM** (`CC_IS_CLANG`, `LD_IS_LLD`, `AS_IS_LLVM`): o build atual é GCC.

Oito símbolos exigidos **não existem** na árvore `hy300-6.1` (são do Android Common Kernel):
`ASHMEM`, `DM_DEFAULT_KEY`, `CPU_FREQ_TIMES`, `UID_SYS_STATS`, `NETFILTER_XT_MATCH_QUOTA2`,
`NETFILTER_XT_MATCH_QUOTA2_LOG`, `USB_CONFIGFS_F_ACC`, `USB_CONFIGFS_F_AUDIO_SRC`. Os cinco
primeiros continuam exigidos nos requisitos do 6.6 e do 6.12, então o Android ainda conta com
eles. O branch `develop-6.1` da Rockchip é o BSP Linux: sem vendor hooks, sem incfs, sem
fuse-bpf.

### Duas saídas

1. **Portar os drivers do ACK para o nosso BSP Linux** (ashmem, dm-default-key,
   cpufreq_times, uid_sys_stats, xt_quota2; os dois de gadget USB não fazem falta, não há porta
   de dispositivo) e escrever um fragmento Android. Trabalho contido, mas fica um kernel que
   ninguém mais usa com Android.
2. **Levar os patches do HY300 para o kernel Rockchip Android 6.1** (ACK + BSP Rockchip)
   que a organização Lineage-Rockchip publica em `github.com/Lineage-Rockchip/android_kernel_rockchip_kernel-6.1`
   (branch `lineage-23.2`, origem Khadas). Conferido pela API do GitHub: `SUBLEVEL = 172` (o
   mesmo 6.1.172 do nosso), tem `drivers/staging/android/ashmem.c`, `drivers/md/dm-default-key.c`,
   `fs/incfs`, `drivers/android/vendor_hooks.c`, `gki_defconfig` + `rockchip_gki.config`, e os
   arquivos que o nosso DTS inclui (`rk3566-box-demo-v10.dtsi`, `rk3568-android.dtsi`), além de
   `panfrost`, `rk_vendor_storage` e `rockchip_pwm_remotectl`. Não tem o AIC8800.

**Recomendação: a saída 2.** Os patches do HY300 são poucos (DTS, sequência SPI do painel no
`panel-simple`, DT embutido, sinal de vida, AIC8800) e a base passa a ser a mesma que outros
aparelhos Rockchip usam no Lineage. Decisão do usuário, porque muda o branch em que o outro
trabalho (Wi-Fi) está.

**Feito em 22/11 (aprovado pelo usuário): branch `hy300-ack-6.1`** do `kernel-hy300-rk3566`,
sobre o `lineage-23.2` do Lineage-Rockchip (`f4f8107cf7cf`). Esse branch é o ACK
`android14-6.1` com o `develop-6.1` mesclado até o mesmo `77168c8d5ab8` do nosso `hy300-6.1`,
então os patches entraram por cherry-pick. Resultado:

- `rockchip_defconfig` + `android-14.config` + `rk3566_hy300.config`, clang 20
  (`clang-r547379` dos prebuilts do Lineage): `kconfig_check.py` contra `u/android-6.1` dá **0
  diferenças** (antes, 170). Os oito símbolos que não existiam (`ASHMEM`, `DM_DEFAULT_KEY`,
  `CPU_FREQ_TIMES`, `UID_SYS_STATS`, `NETFILTER_XT_MATCH_QUOTA2(_LOG)`,
  `USB_CONFIGFS_F_ACC`, `USB_CONFIGFS_F_AUDIO_SRC`) estão ligados;
- o DVFS continua desligado sem violar o requisito: núcleo do cpufreq ligado, nenhum driver;
- `kernel/build-marco1.sh` com `KBASE=ack` (padrão) gera a mesma imagem de teste do slot
  `recovery`, com o modo Wi-Fi; o smoke no QEMU passa;
- no aparelho ainda não foi testado. Detalhes, commits e riscos em `docs/kernel-6.1.md`, "Base
  Android".

Mais pontos do kernel:

- **Panfrost no DT**: o nó `gpu@fde60000` do BSP tem `clock-names = "clk_mali", "clk_gpu"`. O
  Panfrost pega o primeiro clock sem nome e o de barramento pelo nome `"bus"`; com os nomes do
  BSP o `CLK_GPU` não seria ligado. No DT do HY300: `clock-names = "gpu", "bus"` (como no
  mainline) quando trocar `MALI_BIFROST` por `DRM_PANFROST`.
- **VPU duplicada no DT**: `video-codec@fdea0400` (hantro, V4L2) e `vdpu@fdea0400` (MPP) usam
  os mesmos registradores. Ligar um só: MPP (cobre o rkvdec com HEVC/VP9 4K) ou hantro (só
  H.264/VP8/MPEG-2 até 1080p, mas V4L2 padrão).
- **Tamanho**: a `Image` do marco 1 tem 38,8 MiB; com `gzip -9`, 14,5 MB. O defconfig Linux do
  BSP liga muita coisa que o HY300 não tem; um defconfig Android com módulos diminui mais. Na
  base Android (`hy300-ack-6.1`, quase tudo embutido): 34,9 MiB, 15,2 MB com `gzip -9`.
- `kernel/configs` do checkout local ainda não estava baixado; os arquivos foram lidos do
  GitHub do LineageOS (mesmo branch).

## Boot

- **Header v2 continua valendo no Lineage 24.** `build/make` (lineage-24.0,
  `core/board_config.mk`): `vendor_boot` só é gerado com `BOARD_BOOT_HEADER_VERSION >= 3`.
  Com v2 o ramdisk do boot é o do primeiro estágio, e o fstab vai nele.
- **resource.img**: `TARGET_BOOTLOADER_IS_2ND := true` faz o `core/Makefile` passar
  `--second $(PRODUCT_OUT)/2ndbootloader` ao mkbootimg (boot e recovery). A árvore copia
  para lá o resource do próprio aparelho (logo da capivara + `rk-kernel.dtb` de fábrica). O
  U-Boot continua com o DT de fábrica e o kernel usa o embutido, como no marco 1. Os
  `device/*/*/build/tasks/*.mk` entram no build (`core/Makefile`, linha ~8112).
- **ID do header**: o U-Boot de fábrica confere o SHA-1 do header. O mkbootimg do Lineage
  calcula com 4 bytes a mais (patch do `--dt`); a árvore Lineage-Rockchip documenta o mesmo
  erro ("Hash from header ... Failed to load android image"). `tools/mkbootimg_hy300.py` da
  árvore (`BOARD_CUSTOM_MKBOOTIMG`) regrava o ID; o teste confere contra o `boot.img` de
  fábrica.
- **Tamanho da `boot`**: 40 MiB. A `Image` crua do 6.1 (38,8 MiB no BSP, 34,9 MiB na base
  Android) + ramdisk + resource (2,9 MB) não cabe com folga. `Image.gz` (14,5 a 15,2 MB) cabe. O U-Boot tem gzip, lz4, "Uncompressing %s" e
  "Can't get image compression!" no caminho do `bootm` (strings do `uboot.img`); só o teste
  no slot `recovery` confirma que ele descomprime uma imagem Android. Se não descomprimir: kernel
  menor com módulos (ainda cabe só se a `Image` ficar abaixo de ~36 MB).
- **cmdline**: vem toda do boot.img (a de fábrica está no header; o U-Boot só acrescenta
  `storagemedia`, `androidboot.mode`, `serialno`, `verifiedbootstate`, `dtb_idx` e `earlycon`).
  `androidboot.hardware=rk3566`. **`androidboot.boot_devices=fe310000.sdhci`**: no kernel
  Android (`hy300-ack-6.1`) o eMMC é `sdhci@fe310000`, como na fábrica. No BSP Linux
  (`hy300-6.1`) era `mmc@fe310000`; o nome errado deixa o `/dev/block/by-name` vazio.
- Endereços (base `0x10000000`, kernel `+0x8000`, ramdisk `+0x1000000`, second `+0xf00000`,
  tags `+0x100`, dtb `+0x1f00000`) iguais aos do boot.img de fábrica.

## Gráficos

O que o Android 17 traz (`android-17.0.0_r1`):

- `external/drm_hwcomposer`: tem `hwc3/` e o módulo `android.hardware.composer.hwc3-service.drm`;
- `external/minigbm`: `cros_gralloc/aidl` (`android.hardware.graphics.allocator-service.minigbm`),
  `mapper_stablec` (`mapper.minigbm`), `rockchip.c` (só compila com `DRV_ROCKCHIP`, que o
  `Android.bp` não oferece; `minigbm.platform=generic` usa dma-heap + dumb buffers);
- `external/mesa3d` (26.1.0-devel): o `Android.bp` gerado pelo meson2hermetic compila **só o
  gfxstream** (emulador/virtio). O Panfrost está no fonte, mas sem regra de build.

Logo o Mesa com Panfrost entra como no GloDroid: `GloDroid/aospext` (Apache-2.0, makefiles que
rodam meson dentro do build do AOSP) + Mesa upstream, por `local_manifest`. Os blobs Mali G52 de
64 bits existem (`Lineage-Rockchip/proprietary_vendor_rockchip_gpu/MaliG52`), mas são da
Rockchip, não podem ir para o nosso repositório e amarram a ABI ao Android em que foram feitos.
Ficam só como plano B local.

### Keystone

A correção de 4 cantos é uma homografia aplicada na composição final. Proposta: patch em
`frameworks/native` (SurfaceFlinger/RenderEngine Skia):

1. ler `persist.sys.keystone.{lt,lb,rt,rb}` quando `persist.sys.keystone.update` for 1 (e
   voltar para 0), com o mesmo significado de hoje: deslocamento "x,y" de cada canto em px de
   1280x720, x para a direita, y para cima;
2. converter para o painel 1024x600 (fator 0,8 em x, 0,833 em y) e montar a matriz 3x3;
3. com keystone diferente de zero, forçar composição pelo cliente (GPU) e aplicar a matriz
   (`SkMatrix` com perspectiva) no canvas do display; fora do quadrilátero fica preto.

Assim o app de configurações não muda nada. Custo: uma passada de GPU por quadro, como na
fábrica. Alternativa sem mexer no framework (passada GLES dentro do drm_hwcomposer) é mais
trabalho e o drm_hwcomposer não tem compositor GPU. A conferir no código quando o
`frameworks/native` do checkout chegar.

## Vídeo

- Kernel: `mpp_service` (MPP) e `hantro`/`rkvdec` (V4L2) existem no 6.1.
- Userspace: MPP (`rockchip-linux/mpp`) e Codec2 da Rockchip têm fonte pública
  (`rockchip-toybrick/rk_platform_vendor_rockchip_codec2`, Apache-2.0;
  `Lineage-Rockchip/android_hardware_rockchip_codec2`, lineage-23.2). Não verificado: se o
  Codec2 da Rockchip depende de metadado do gralloc da Rockchip (aí precisa adaptar ao minigbm).
- Primeiro marco com os codecs de software do AOSP (`c2.android.*`): 720p em H.264 deve
  servir; HEVC/VP9 1080p não.

## Testar sem regravar a `super`

O sistema novo tem de bootar antes de a `super` ser regravada. Proposta:

1. boot.img do Lineage gravado na `recovery` (o `scripts/reboot-to-test-slot.sh` já entra nela
   sem tocar na `misc`). O ramdisk do boot não tem `/system/bin/recovery`, então o init sobe o
   Android normal;
2. um pendrive na USB-A com GPT e três partições com nome: `super` do Lineage, `metadata` e
   `userdata`;
3. cmdline do teste com `androidboot.boot_devices=fe310000.mmc,<caminho do xHCI>`,
   `androidboot.super_partition=<nome no pendrive>` e `androidboot.fstab_suffix=usbtest`
   (um `fstab.usbtest` que monta `/metadata` e `/data` do pendrive). O eMMC só é lido.

A conferir no aparelho/código: o caminho de plataforma do xHCI do dwc3 (`usbdrd` →
`usb@fcc00000` → `xhci-hcd.*.auto`) que o ueventd usa para criar o `by-name`, e o suporte a
`fstab_suffix` e `super_partition` no init do Android 17. Plano B: criar `system_b`,
`vendor_b` etc. nos ~1257 MiB livres da `super` (só cabe com EROFS) e bootar com
`androidboot.slot_suffix=_b` e `slotselect` no fstab de teste.

## Riscos

| Risco | Efeito | Mitigação |
|---|---|---|
| U-Boot não descomprime `Image.gz` de boot.img Android | Lineage não cabe na `boot` | testar no slot `recovery` primeiro; kernel com módulos |
| Kernel sem os requisitos do FCM 8 | falhas em netd/vold/memória compartilhada; pode aparecer o aviso de "problema interno" no boot | resolvido no build: `hy300-ack-6.1` zera o `kconfig_check.py`; o `build-marco1.sh` para se voltar a ter diferença |
| Panfrost + drm_hwcomposer no VOP2 do BSP | tela preta, composição lenta | marco só de gráficos com `modetest`/`kmscube` antes do Android; plano B blob local |
| 1,5 GB de RAM com Android 17 de 64 bits | lmkd mata apps, launcher recarrega | low_ram, zram 75 %, sem GMS, medir no marco de primeiro boot |
| Apps só de 32 bits | não instalam | aceitar (VLC e AirScreen têm arm64) ou rever a decisão de ABI |
| Keystone no SurfaceFlinger | patch grande no framework | manter o patch pequeno e isolado; testar no marco próprio |
| Gravar a `super` de dentro do aparelho | sem fastboot por USB, erro deixa sem sistema | só depois de bootar pelo pendrive; backup da `super` já existe; MaskROM como último recurso |
| Bluetooth do AIC8800 sem a `libbt-vendor` | sem BT | conferir se o `aic8800_bsp` deixa o chip pronto; senão escrever o equivalente aberto |
| Entrada HDMI (RK628) | sem HDMI-in no começo | marco próprio, depois do resto |

## Ordem de trabalho (marcos)

1. **Kernel Android**: escolher a base (recomendado: Rockchip ACK 6.1.172), aplicar os
   patches do HY300, config Android até o `kconfig_check.py` zerar (ou só sobrarem os
   símbolos sem uso), build com clang. Boot pelo slot `recovery` com o initramfs de teste.
   **22/11: feito até o build** (`hy300-ack-6.1`, 0 diferenças, clang 20, smoke no QEMU nos
   três modos, imagem `~/hy300-work/marco1-ack/recovery-marco1.img`). Falta o boot no aparelho.
2. **Boot comprimido**: `Image.gz` dentro de um boot.img v2 feito com o
   `mkbootimg_hy300.py`, no slot `recovery`. Confirma o tamanho e o ID.
3. **Gráficos fora do Android**: Panfrost + `modetest`/`kmscube` no initramfs de teste.
4. **Primeiro build do Lineage TV** e boot pelo pendrive (SELinux permissive, só software).
5. Áudio, Wi-Fi (driver do outro trabalho), Bluetooth, IR, KeyMint por software.
6. **Keystone no SurfaceFlinger** e o app de configurações como app de plataforma.
7. Motor de foco (driver novo com `/sys/class/motor_cc`), acelerômetro e HAL de sensores.
8. Vídeo com MPP + Codec2.
9. sepolicy e SELinux enforcing.
10. Gravar a `super`, a `boot` e a recovery do Lineage no eMMC (backup antes).
11. Entrada HDMI (RK628) e áudio da entrada.

## O que depende do usuário

- Decidir a base do kernel (saída 1 ou 2) e se o branch muda agora ou depois do Wi-Fi.
- Pendrive dedicado ao teste (vai ser apagado) e estar presente nos boots de teste (controle).
- Aceitar perder apps só de 32 bits, ou pedir a troca para 64/32.
- Onde publicar a árvore (`~/android/device-hy300`, git local sem remoto).
- Mais tarde: autorizar a gravação da `super`.

## O que não foi verificado

- A árvore não foi compilada. O kernel com config Android foi (22/11, `hy300-ack-6.1`), mas
  ainda não bootou no aparelho.
- `kernel/configs`, `vendor/lineage`, `external/mesa3d`, `external/minigbm`,
  `external/drm_hwcomposer` e `hardware/interfaces` foram lidos fora do checkout (GitHub do
  LineageOS e googlesource na tag `android-17.0.0_r1`); o `build/make` e o `device/lineage/atv`
  foram lidos do checkout (objetos do `repo`, só leitura).
- Se o U-Boot descomprime o kernel de um boot.img Android (só as strings indicam).
- O caminho do xHCI no `by-name`, `fstab_suffix` e `super_partition` no Android 17.
- Se o Codec2 da Rockchip funciona com o minigbm.
- Se o `aic8800_bsp` sozinho deixa o Bluetooth pronto para o `hci_uart`.
- Tamanho real das imagens do Lineage TV.
- Densidade 170 na projeção.
