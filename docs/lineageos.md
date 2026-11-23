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
4. `codec2/0004` (rodada 6): **encoders com o minigbm**. O `C2RKMpiEnc` pedia
   `RK_GRALLOC_USAGE_WITHIN_4G` e `RK_GRALLOC_USAGE_STRIDE_ALIGN_16` para os buffers de entrada e
   alocava o buffer temporário da RGA no NV12 da Rockchip. Agora: entrada sem bits privados (toda
   a RAM do HY300 fica abaixo de 4 GiB, então o limite de 4 GiB da RGA2 nunca morde), buffer
   temporário `YCBCR_420_888` com uso de encoder, e quadro com stride não múltiplo de 16 passa
   pela RGA para o buffer alinhado (o que o gralloc da Rockchip fazia na alocação). A tela que o
   SurfaceFlinger desenha para gravação/espelhamento chega em RGBA (o minigbm resolve
   `IMPLEMENTATION_DEFINED` para XBGR8888) e o VEPU540 lê RGBA direto.
5. `frameworks/av/0001` (rodada 6): `CCodec::createInputSurface` falha com
   `onInputSurfaceCreationFailed` em vez de derrubar o processo quando não há de onde tirar a
   superfície (ver "Entrada por Surface" abaixo).

`media_codecs.xml` / `media_codecs_c2_rk.xml` (vendor): decoders `c2.rk.{avc,hevc,vp9,vp8,mpeg2,
m4v,h263}` até **1920x1088** a 60 fps. O RK3566 faz H.264/HEVC/VP9 até 4K60, mas o painel é
1024x600 e os buffers de 4K não cabem bem em 1,5 GB; limitar faz o Netflix e o Crunchyroll pedirem
no máximo 1080p. Os codecs de software (`c2.android.*`) seguem disponíveis pelo APEX swcodec.

`/dev/mpp_service` e `/dev/rga` ficam `0660 system system` (o serviço roda como `mediacodec` com
grupo `system`). No kernel, o `rk3566-box-demo-v10.dtsi` liga rkvdec, vdpu, iep, jpegd e RGA.

Encoders (rodada 6): `c2.rk.avc.encoder` e `c2.rk.hevc.encoder`, VEPU540, até 1920x1088 a
60 fps, CBR/VBR, duas instâncias. Sem `media_codecs_performance.xml`: os `measured-frame-rate`
precisam de medição no aparelho; o ponto de desempenho declarado é o do datasheet (1080p60). O
serviço roda com seccomp, e o encoder faz chamadas que o decoder em buffer mode nunca fez
(`mpp_buffer_import` duplica o fd com `fcntl`): a árvore instala
`android.hardware.media.c2@1.1-extended-seccomp-policy` com `fcntl`, `dup3`, `timerfd_*`,
`epoll_*`, `sched_getaffinity` e `uname`.

**Entrada por Surface** (gravação de tela, espelhamento, scrcpy). O `CCodec` procura a superfície
em três lugares: o InputSurface do HAL do Codec2, o OMX e, com `debug.stagefright.c2inputsurface=-1`,
um `GraphicBufferSource` no próprio processo. O HAL da Rockchip é HIDL 1.1 e não cria InputSurface,
e o OMX está desligado (`TARGET_SUPPORTS_OMX_SERVICE := false`): sem a prop,
`createCompatibleInputSurface()` devolvia nulo e `createInputSurface()` chamava `getType()` nele
(SIGSEGV em `libsfplugin_ccodec.so`, `CCodec::createInputSurface()+164`, visto com o scrcpy). A
correção é a prop no vendor (`device.mk`), a mesma que o emulador usa; o patch `frameworks/av/0001`
troca o crash por erro se ela faltar.

Fica de fora por enquanto: **10 bits** (HEVC Main10, VP9 perfil 2): o caminho de P010 depende dos
bits de uso do gralloc da Rockchip. AV1 não existe no RK3566.

### DRM (Netflix, Crunchyroll)

Netflix e Crunchyroll exigem **Widevine**. O HAL do Widevine (`android.hardware.drm-service.widevine`,
`libwvhidl`/`liboemcrypto`) é binário do Google, não existe no AOSP/Lineage e **não vai para os
nossos repositórios**. Sem ele os dois apps não tocam vídeo protegido. Com o Widevine num Lineage
não certificado o nível é **L3** (software) e o Netflix limita L3 a **SD** (até 480p);
Crunchyroll costuma aceitar mais. Não há como subir de nível sem certificação, e não se tenta
contornar. O Widevine de fábrica é de 32 bits (Android 12, vendor 32 bits) e não roda neste
Lineage só de 64 bits; um Widevine de 64 bits para Android 15/16 existe nos blobs do
Lineage-Rockchip (`proprietary_vendor_rockchip_rk35xx-common`), só como opção local do usuário.

Os GApps (rodada 6) **não trazem DRM**: o Widevine continua separado e continua faltando. Com
GApps e sem Widevine, Netflix e Crunchyroll instalam pela loja e não tocam vídeo protegido.

**ClearKey** (rodada 12): o `android.hardware.drm-service-lazy.clearkey` do AOSP é o único HAL de
DRM da imagem e existe para o `MediaDrm` responder "não suportado" em vez de lançar exceção
(detalhes na rodada 12). Ele continua quando o Widevine entrar: os dois convivem
(`IDrmFactory/clearkey` e `IDrmFactory/widevine`).

**Widevine L3** (para a rodada 13; até lá o coordenador instala por `adb remount`): binário do
Google, **só no build local**, nunca em repositório público.

| | |
|---|---|
| Origem | imagem oficial do emulador Android TV 16 arm64 do SDK do Google, `system-images;android-36;android-tv;arm64-v8a` revisão 4 (`arm64-v8a-36_r04.zip`) |
| SHA-256 do zip | `7398e2f00e5df28332027d5a131fcbefb8d5823bc7103a65a035575d271ffcca` (SHA-1 publicado no XML do SDK conferido: `ceb1dfcc6a28dbd9dbade780428cf7bafb1c65ef`) |
| CDM | 19.5.0, HAL AIDL v1, sob demanda (`android.hardware.drm-service-lazy.widevine`) |
| Fingerprint do vendor de origem | `google/sdk_google_atv64_arm64/emu64a:16/BT2A.260319.001/15058170:user/dev-keys` |
| No checkout | `vendor/hy300-widevine/` (cópia de `~/hy300-work/widevine/vendor-widevine/`), ligado no `device.mk` só se o diretório existir; variante `classico` (a `apex`, do Android 17 `google_apis_playstore`, fica desligada) |
| Pacote para adb | `~/hy300-work/widevine/pacote/` (`instalar-por-adb.sh`, `SHA256SUMS`, `LEIAME.md`) |

Em Lineage não certificado o nível é L3: o Netflix limita a SD; YouTube e Crunchyroll costumam
tocar.

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

  **Causa provável, achada depois (23/11): o DT, não o Panfrost.** O `/proc/interrupts` do panic
  tem `71: 16528046 ... rockchip_gpio_irq 8 Edge GPIO Key Home`, tudo na CPU0 (~270 mil/s desde
  o probe do `gpio-keys`). Os relatórios do marco 1 (BSP, Alpine) já mostravam 2,7 a 3,2 milhões
  aos 17-18 s. A fábrica declara a tecla como `interrupts = <0x0 0x8>` no gpio1 (pino 0 =
  GPIO1_A0, `IRQ_TYPE_LEVEL_LOW`; o `/proc/interrupts` de fábrica mostra `gpio1 0 Level` com 0); o
  porte leu ao contrário, `<RK_PB0 IRQ_TYPE_NONE>`, e caiu no GPIO1_B0, o LED "green" (saída em
  0). Sem tipo, o GPIO fica em nível baixo e dispara sem parar. Com a CPU0 quase toda em hardirq
  (o `IRQ_TIME_ACCOUNTING` não cobra isso da thread, então o RT throttling quase não age), as
  threads do Panfrost, que herdam a afinidade da CPU0, andam a conta-gotas: timeout de 500 ms do
  job, a thread da MMU dezenas de segundos em `shmem_read_mapping_page_gfp`, `ksoftirqd/0` sem
  CPU (rcu stall com `softirq=1048/1048`) e a CPU3 num spinlock (provavelmente o `job_lock`, que a CPU0 segura) até o
  pré-timeout. Correção no `hy300-ack-6.1` (`c16531517b74`): a tecla vira `gpios = <&gpio1
  RK_PA0 GPIO_ACTIVE_LOW>`. O `build-lineage-kernel.sh` agora para se uma tecla do `gpio-keys`
  estiver sem tipo, num pino de LED ou fora do pino de fábrica (`tools/dt_gpio_irq.py`, testes
  em `tests/test_dt_gpio_irq.py`). O branch `hy300-6.1` (Alpine) tem o mesmo erro.

  No mesmo prebuilt, endurecimento do Panfrost (commits sobre o `c16531517b74`): backport de
  "Add gpu_irq, mmu_irq" + "Synchronize and disable interrupts before powering off" (6.8, não 6.5),
  "Sync IRQ by job's timeout handler" (6.6), "Check sgt to know whether pages are already mapped"
  + "Fix the error path in panfrost_mmu_map_fault_addr()", e um limite local: 32 respostas "já
  mapeado" seguidas no mesmo bloco do heap viram falha terminal em vez de laço eterno. Prebuilt
  `hy300-ack-6.1` `1ee24ab83ac1`: `Image.gz`
  `a9d844f1311b89ea859b8a2ebe1235d22264bc498d90048b75d4db635d32d93a`, `panfrost.ko`
  `dd2f37d9404ad900c03a4ea24e14d0f43a42b1cb240d73d758e19f8a5dc5d71a`; `gpu-sched.ko` e
  `drm_shmem_helper.ko` saem iguais aos de `9358ce442f3e`.
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

### Rodada 4: o que o boot 2 mostrou (23/11/2026)

Boot 2 (imagem da rodada 3, `gpu=sw`): o ciclo fechou (diag, marca de ficar, volta ao Alpine).
Logs em `~/hy300-work/lineage-artifacts/boot2/`.

- **Travadas**: tempestade de IRQ na CPU0 pela "GPIO Key Home" com as células do DT trocadas
  (achado do worker do kernel; 16,5 milhões de IRQs no boot 1). Kernel novo `hy300-ack-6.1`
  `1ee24ab83ac1` (DT corrigido e backports do Panfrost) no `prebuilt/`. O diag agora grava
  `interrupts.txt` (`/proc/interrupts`) a cada 20 s: a linha "GPIO Key Home" tem de ficar perto
  de 0. O boot padrão volta a ser **`gpu=panfrost`**; `boot-sw.img` é a reserva.
- **system_server sem `activity`**: o `Watchdog` matou o system_server ("Blocked in handler on
  main thread (main) for 69s"), preso em `AudioService.<init>` → `AudioSystem.isCallScreeningModeSupported`
  esperando o audioserver, que reiniciava em laço. Causa: o serviço de efeitos do APEX de áudio
  sai ("config file audio_effects_config.xml not found"; o APEX de exemplo não traz o arquivo e o
  `EffectMain.cpp` procura no APEX e depois com `audio_find_readable_configuration_file` no
  `/vendor/etc`), e o `onrestart restart audioserver` do `.rc` dele derruba o audioserver a cada
  vez. Correção: `hardware_interfaces_audio.use_default_audio_effects_config=true` e
  `audio_effects_config.xml` no `/vendor/etc` (o mesmo arquivo do exemplo do AOSP). Os
  "No service published for: jobscheduler/trust" eram consequência do system_server reiniciando.
- **SIGSEGV do `hy300-bootlog-native`**: ao sair (deadline de 180 s), a thread do logcat, desligada,
  chamava `addLine` num `BootModel` da pilha do `main` já destruído. Agora `startLogReader`
  (`bootlog_model`) dá à thread uma referência própria ao modelo (teste no host:
  `LogReader.keepsModelAliveAfterOwnerDropsIt`) e o `main` sai por `_exit`. O fallback para o Java
  não foi exercitado: o nativo desenhou em ~1 s e só caiu na saída.
- **diag**: "logcat/ip: inaccessible or not found" porque o `sh` do vendor força
  `PATH=/vendor/bin:/vendor/xbin` (`MKSH_DEFPATH_OVERRIDE` do `sh_vendor`, `external/mksh/Android.bp`).
  O diag roda com `/system/bin/sh` e exporta `PATH` com `/system/bin` primeiro; os testes cobrem
  os dois (`test_init_rc.py`, `test_diag.py`). O Wi-Fi já deu sinal de vida no ACK: módulos com
  rc=0 e `wlan0` aos 43 s; com o `ip` e o `iw` alcançáveis o scan deve rodar.
- **Shutdown**: o diag pediu o reboot aos 482 s e o aparelho só reiniciou aos 711 s, pelo panic do
  pré-timeout (shutdown travado pela tempestade). Conferir no próximo pstore.

Artefatos da rodada 4 em `~/hy300-work/lineage-artifacts/` (rodada 3 em `r3/`), kernel
`1ee24ab83ac1`; `verify-boot` passa nos três boot.img e o `check_vintf_hals.py` dá "10 HALs
obrigatórios declarados":

| Arquivo | Tamanho | sha256 |
|---|---|---|
| `boot.img` (`gpu=panfrost`, vai na `recovery`) | 19.888.128 | `a122e5154d4249ba2c7facebb4ed0f14e10ed8899f55d3a1c779aa4e45105735` |
| `boot-sw.img` (`gpu=sw`, reserva) | 19.888.128 | `084c78c5ff184f2538509700afa46b19da7d05aca545786616e44c7a3e7a9d0d` |
| `recovery.img` | 32.614.400 | `2a14415f0f383fa3a3d5dcfa94106bd8f99226e0f94129a215b816bd821fd88f` |
| `super.img` (sparse) | 1.407.674.332 | `6bbfecae478458803115029f955255017399d074b7a8d04bcf79492fc1189fe0` |
| `super.raw` (vai na `super`) | 3.263.168.512 | `ae71da3fee397fa82c14da5faa37c7c3da0a42cd352c848c4d63f9aac81dbdf8` |

### Rodada 5: áudio, Wi-Fi do Android e adb pela rede (23/11/2026)

Boot 3 (rodada 4, `gpu=panfrost`): sem tempestade de IRQ ("GPIO Key Home" = 0), Panfrost sem
timeout (373 IRQs de job), shutdown rápido (pedido aos 489 s, Alpine de volta em 544 s), Wi-Fi
AIC8800 no ACK com scan de 13 redes, bootlog inteiro. Sobrou o system_server morto 2 vezes pelo
Watchdog em `AudioSystem.setLowRamDevice` ← `AudioService.<init>`.

- **Áudio**: o processo do HAL (`vendor.audio-hal-aidl`) rodava, mas o `main.cpp` do exemplo do
  AOSP registra um `IModule` para cada módulo do `audio_policy_configuration.xml`
  (`AudioPolicyConfigXmlConverter`, "primary" vira "default"), e o arquivo não existia: só o
  `IConfig` subia, e o audioserver esperou o `IModule/default` para sempre. Além disso nenhum `.rc`
  declarava `interface aidl ...IModule/default`, e o init não sabia a quem pedir o serviço
  (`ctl.interface_start`). Correções:
  - `configs/audio/audio_policy_configuration.xml` + `hy300_primary_audio_policy_configuration.xml`
    (só o alto-falante, 48 kHz estéreo) no `/vendor/etc`, com o `r_submix`, os volumes e o
    surround do AOSP (`aosp_*.xml`);
  - patch `hardware/interfaces/0001`: `interface aidl` nos `.rc` de áudio (core: `IConfig`,
    `IModule/default`, `IModule/r_submix`; efeitos: `IFactory`), gatekeeper, health, keymint e
    power; o APEX de áudio deixa de declarar o módulo `bluetooth` e o provedor de áudio Bluetooth
    (sem Bluetooth, ninguém os registraria). Patches `external/minigbm/0001` (allocator) e
    `hardware/rockchip/codec2/0003` (Codec2, HIDL) com o mesmo.
- **Checagem nova** (`tools/check_vintf_hals.py`): todo HAL AIDL/HIDL declarado no VINTF (vendor,
  odm, APEX de vendor) precisa de um `.rc` com a `interface` correspondente. Na imagem da rodada 4
  ela acusa 16 instâncias, entre elas `IModule/default`; nesta passa. Um teste novo também confere
  que todo patch da árvore é um diff de verdade (o da librga tinha sido gravado com o resumo de um
  wrapper do git no lugar do diff; regravado).
- **Wi-Fi do Android**: `android.hardware.wifi.xml` (FEATURE_WIFI), `wpa_supplicant` AIDL do AOSP
  (nl80211) com `/vendor/etc/wifi/wpa_supplicant.conf`, `wificond` do sistema e
  `wifi.interface=wlan0`. **Sem HAL Wi-Fi do fabricante**: o framework funciona sem ela
  (`WifiNative.java`: `handleIfaceCreationWhenVendorHalNotSupported` devolve `wifi.interface`
  quando `isVendorHalSupported()` é falso), e o HAL AIDL padrão do AOSP só sobe com uma
  `libwifi-hal` de fabricante (a `libwifi-hal-fallback` devolve `WIFI_ERROR_NOT_SUPPORTED`). Os
  módulos sobem no `boot` pelo `hy300-wifi-modules` (em segundo plano, ~40 s), com as funções do
  `kernel/initramfs-test/hy300-wifi.sh`; firmware só no build local. O diag não faz mais scan
  próprio (brigaria com o supplicant): só registra o estado, e carrega os módulos ele mesmo se a
  interface não aparecer em 60 s.
- **Rede e adb pela rede** (`configs/init/hy300-net.sh`, só userdebug, depois do
  `boot_completed`): instala a chave do PC em `/data/misc/adb/adb_keys` (sem duplicar,
  `system:shell 0640`), liga `adb_enabled`, `service.adb.tcp.port=5555` e reinicia o adbd (a
  autenticação continua ligada), liga o Wi-Fi e conecta com `cmd wifi connect-network` (salva a
  rede), e apaga o `wifi.conf`. IP por **DHCP** (o `cmd wifi` não tem IP fixo; para um IP fixo,
  reserva no roteador). Log em `/metadata/hy300-diag/net.txt`, sem a senha.
- **Retorno ao Alpine**: aos 480 s o diag só reinicia se o adb pela rede **não** estiver de pé
  (`init.svc.adbd=running`, `service.adb.tcp.port=5555` e IPv4 no `wlan0`); se estiver, registra
  "adb pela rede no ar: sem reinício automático" e segue gravando os logs.

Ordem no boot: `post-fs` → `hy300-diag` (logs) · `boot` → `hy300-wifi-modules` (wlan0 ~40 s) ·
`boot_completed` → `hy300-net` (adb pela rede, Wi-Fi, apaga o `wifi.conf`) · 480 s → diag:
adb no ar fica; senão marca de ficar + reboot para o Alpine.

**O que o Alpine grava no `/metadata` antes do boot** (o metadata não é mais zerado; só o
userdata, quando pedido; nesse caso apague também `/mnt/metadata/vold`, que guarda o estado do
checkpoint do `/data` antigo, e deixe o `hy300-diag`):

```sh
mkdir -p /mnt/metadata
mount -t ext4 /dev/block/by-name/metadata /mnt/metadata      # com escrita
mkdir -p /mnt/metadata/hy300-diag
umask 077
cat > /mnt/metadata/hy300-diag/wifi.conf <<'CONF'
WIFI_SSID=<nome da rede>
WIFI_PSK=<senha>
WIFI_SECURITY=wpa2
CONF
chmod 600 /mnt/metadata/hy300-diag/wifi.conf
# chave pública do PC (cat ~/.android/adbkey.pub no PC), por exemplo:
#   scp ~/.android/adbkey.pub root@<IP do Alpine>:/mnt/metadata/hy300-diag/adb_keys
chmod 644 /mnt/metadata/hy300-diag/adb_keys
sync; umount /mnt/metadata
hy300-android
```

Artefatos da rodada 5 em `~/hy300-work/lineage-artifacts/` (rodada 4 em `r4/`), kernel
`1ee24ab83ac1`; `verify-boot` passa nos três boot.img; `check_vintf_hals.py`: "11 HALs
obrigatórios declarados; todo HAL declarado tem serviço no init". O `boot.img` é idêntico ao da
rodada 4 (kernel e ramdisk iguais); o que mudou está na `super`.

| Arquivo | Tamanho | sha256 |
|---|---|---|
| `boot.img` (`gpu=panfrost`, vai na `recovery`) | 19.888.128 | `a122e5154d4249ba2c7facebb4ed0f14e10ed8899f55d3a1c779aa4e45105735` |
| `boot-sw.img` (`gpu=sw`, reserva) | 19.888.128 | `084c78c5ff184f2538509700afa46b19da7d05aca545786616e44c7a3e7a9d0d` |
| `recovery.img` | 32.614.400 | `54cffba5570ffef49f75c38ce095b432a97b52edf640c93cf9d9e49a5eef8542` |
| `super.img` (sparse) | 1.413.367.800 | `c84ae8b79dc5b828ebd3ab5db972416f220e016fd8345a8c5933f14743213bb4` |
| `super.raw` (vai na `super`) | 3.263.168.512 | `49444ff5ea317ffa0b9f5458ec242d1c8b74db9d9dfe1ca641f86e292f1dabd6` |

Formato do `wifi.conf`: uma chave por linha, `CHAVE=valor`, o valor é tudo depois do primeiro `=`
(espaços valem); `WIFI_SECURITY` é `wpa2` (padrão), `wpa3` ou `open`; linhas com `#` e chaves
desconhecidas são ignoradas; o arquivo não é executado e é recusado se não tiver modo 600 (ou
400). No PC, depois do boot: `adb connect <IP>:5555` (o IP sai do DHCP; está no `net.txt` do
próximo diag ou no roteador).

### Rodada 6: encoder, entrada por Surface, GApps e memória (23/11/2026)

O boot 4 (rodada 5) completou: boot_completed em menos de 3 min, Wi-Fi com DHCP, adb pela rede,
Mesa Panfrost GLES 3.1, 1024x600 a 60 Hz, CPUs a 1,8 GHz, áudio e Codec2 (decoders) rodando,
sem reinício depois dos 480 s. O que entrou:

- **Encoders por hardware** `c2.rk.avc.encoder` e `c2.rk.hevc.encoder` (patch `codec2/0004`,
  `media_codecs_c2_rk.xml`, seccomp estendido). Detalhes em "Vídeo por hardware".
- **Entrada por Surface**: `debug.stagefright.c2inputsurface=-1` no vendor e o patch
  `frameworks/av/0001`. Com isso o scrcpy e a gravação de tela não derrubam o processo, e passam a
  poder usar o `c2.rk.avc.encoder` em vez do encoder de software (que ficava a ~109 % de CPU no
  `media.swcodec`).
- **Seletor "Concluir a ação usando: Configurações / Projetor"**: a `AndroidSettingsActivity` do
  app vem desligada (ver o README do app). O item "Projetor" do TvSettings
  (`com.android.tv.settings.SOUND`) continua: `cmd package query-activities` no boot 4 mostrou o
  `MainActivity` como único destino da ação, e o `MainFragment.updateSoundSettings()` do TvSettings
  mostra o item quando um app de sistema a trata.
- **Fuso padrão** `America/Campo_Grande` (`persist.sys.timezone` no product).
- **Assistente de configuração**: o `LineageSetupWizard` não cabe em 1024x600 (botões fora da tela)
  e saiu da imagem; no lugar entra o `TvProvision` do AOSP (`device/google/atv`), que só marca
  `device_provisioned` e `user_setup_complete` e se desativa. O `Updater` também saiu (não há OTA
  para este aparelho, e ele ficava residente com 13 a 15 MB). Os dois saem pelo módulo
  `hy300-package-overrides` da árvore (`overrides`).
- **Diag mais leve**: com boot_completed e adb pela rede no ar, o `hy300-diag.sh` para as coletas
  (o `dmesg` como root a cada 20 s deixava o processo em estado D, 9 % de CPU) e só confere se o adb
  continua de pé; no prazo de 8 min ele termina. Se o adb cair antes do prazo, as coletas voltam, e
  sem adb no prazo a volta ao Alpine continua igual.
- **GApps e Aurora Store** (só no build local) e **zram pelo mmd** com writeback: seções abaixo.

#### Memória: medição do boot 4 e o que mudou

Medido no aparelho (`~/hy300-work/lineage-artifacts/boot4/medicao/` e leitura direta pelo adb):

| Item | Valor |
|---|---|
| `MemTotal` | 1.486.400 kB |
| Nó `memory` do DT (preenchido pelo U-Boot) | `0x00200000+0x08200000` e `0x09400000+0x56c00000` = 1.554.432 kB, termina em `0x60000000` |
| Buraco em `0x08400000` | 16 MiB (OP-TEE/BL32, fora do kernel) |
| Reservado pelo kernel no boot | 71.508 kB (código 21 MB, rodata/dados 13 MB, `struct page` ~24 MB) |
| `reserved-memory` do DT | `linux,cma` 8 MiB (reutilizável); `ramoops` 960 KiB; `rknpu` 512 MiB **desativado** (`status = "disabled"`, não reserva nada); `drm-logo`, `drm-cubic-lut`, `vendor-storage-rm` com tamanho 0 |
| Zona DMA32 | 388.608 páginas presentes |
| `MemAvailable` / `MemFree` (assistente aberto) | 580 a 630 MB / 23 a 78 MB |
| `AnonPages` / `Cached` | 457 a 474 MB / 608 a 687 MB |
| `Slab` (não recuperável) | 160 MB (105 MB) |
| `KernelStack` / `PageTables` | 20 MB / 42 MB |
| DMA-BUF | 64 MB |
| zram (`mm_stat`) | 78,8 MB de páginas em 22,8 MB comprimidos, 30,5 MB com a sobra do zsmalloc: razão 3,45 (2,58 efetiva) |
| Maiores PSS | system_server 151 MB, surfaceflinger 80 MB, systemui 71 a 81 MB, tv.settings 56 MB, launcher 37 MB, media.provider 27 MB, lineageos.updater 13 a 15 MB, setupwizard 60 MB enquanto aberto |

Conclusões:

- **A RAM física é 1,5 GB, não 2 GB.** O nó `memory` vem do U-Boot, que o monta a partir do que o
  blob de DDR mediu, e termina em `0x60000000`. Não há reserva escondida no DT: o que o DT reserva
  soma ~9 MB. **Não há mudança de DT que devolva memória**, e declarar memória além da física
  derruba o kernel.
- O CMA de 8 MiB basta: minigbm (dumb no DRM com IOMMU), MPP e RGA alocam no heap `system`
  (páginas espalhadas, IOMMU), não no CMA. Nenhuma reserva fixa pensada para 4K/10 bits existe no DT
  ou no MPP (o rkvdec2 usa 45 KiB de SRAM e 64 KiB de RCB); os buffers do Codec2 são alocados por
  stream, e o teto de 1920x1088 no `media_codecs_c2_rk.xml` limita o DPB a 1080p.
- **Para o worker do kernel** (descrição, não mexi nos repositórios de kernel):
  1. Opcional: `CONFIG_CRYPTO_ZSTD=y` só se quisermos testar zstd; a recomendação é ficar no lz4
     (abaixo). O kernel tem `CONFIG_ZRAM_WRITEBACK=y` e `CONFIG_BLK_DEV_LOOP=y`, que é o que o
     writeback precisa.
  2. Investigar os 105 MB de slab não recuperável com root (`/proc/slabinfo` no Alpine ou num
     build eng): o `/sys/kernel/slab` não é legível pelo shell. Suspeitos: buffers pré-alocados do
     AIC8800 (`aicwf_prealloc_txq_alloc`, `aicbsp_resv_mem_alloc_skb`) e caches de kmalloc.
     `CONFIG_KFENCE` (63 objetos) e `CONFIG_SCHED_DEBUG` custam pouco; `SLUB_DEBUG` já está desligado.

**zram e writeback** (diretriz do usuário: mais swap e compressão, vídeo até 720p):

- **Tamanho 125 % da RAM (1,81 GB).** Com a razão efetiva medida (2,58), o zram cheio ocupa
  ~700 MB, menos da metade da RAM; acima disso a memória comprimida disputaria com o que precisa
  ficar descomprimido (SurfaceFlinger, o app de vídeo, o cache de arquivos). 150 % ocuparia ~840 MB
  (58 % da RAM) quando cheio.
- **lz4, não zstd.** O kernel só tem lz4 (`CONFIG_CRYPTO_ZSTD` desligado). Mesmo com zstd: nos
  quatro A55 a 1,8 GHz o zstd comprime várias vezes mais devagar e descomprime ~3 vezes mais
  devagar que o lz4, para ganhar ~25 % de razão. Cada falta de página no zram vira descompressão no
  caminho do app em primeiro plano; com vídeo tocando, a latência do lz4 pesa mais que a razão. O
  kernel 6.1 não tem recompressão (`ZRAM_MULTI_COMP` veio no 6.2), que seria o meio-termo (lz4 na
  hora, zstd nas páginas ociosas).
- **Writeback para o eMMC pelo `mmd`** (o daemon de memória do Android 17, `system/memory/mmd`,
  ligado pela flag `android.mmd.flags.mmd_enabled` no `cp2a`). O zram saiu do fstab: com a linha
  lá, o `swapon_all` ativa o zram antes do `mmd_setup`, que então pula a configuração inteira, e o
  writeback junto. Agora o `mmd_setup` monta o zram no boot_completed (como antes) com um arquivo
  de 512 MiB em `/data/per_boot/zram` atrás de um loop como dispositivo de writeback, e o `mmd`
  grava no eMMC só páginas ociosas há 2 a 4 horas, no máximo 256 MiB por dia (~90 GB por ano, bem
  abaixo da resistência de um eMMC de 16 GB). A manutenção não espera o aparelho ficar ocioso
  (`mm.zram.maintenance.require_device_idle=false`): o projetor é desligado, não fica parado com a
  tela apagada. Se o `/data` tiver menos de 1,5 GiB livres depois do arquivo, o `mmd` monta o zram
  sem writeback.
- lmkd: sem mudança (PSI, `kill_heaviest_task`, `swap_util_max=90`). Com o zram maior, o
  `swap_util_max` passa a valer sobre 1,81 GB.

A medir no próximo boot (com e sem GApps): `/proc/meminfo`, `dumpsys meminfo`,
`/sys/block/zram0/{mm_stat,bd_stat,backing_dev}`, `getprop | grep mmd`, e se o `mmd` registrou o
writeback (`logcat -s mmd`).

#### GApps (MindTheGapps ATV minimal) e Aurora Store

**Proprietário, só no build local**: nada disso vai para repositório público. A árvore pública só
tem a configuração condicional.

- Fonte: o repositório que gera os zips do MindTheGapps para TV,
  `MindTheGapps/vendor_gapps_tv`, branch `cinnamonbun` (Android 17), commit `9da5e04c873d` (o da
  release `MindTheGapps-17.0.0-arm64-ATV-20260630_185024`). O local_manifest
  `.repo/local_manifests/hy300-gapps.xml` (local) traz o projeto em `vendor/gapps_tv`:

  ```xml
  <project path="vendor/gapps_tv" name="MindTheGapps/vendor_gapps_tv" remote="hy300-github"
           revision="9da5e04c873dee6c53d8aeea1e92e093500d87cc" upstream="cinnamonbun" clone-depth="1" />
  ```

  e `repo sync -c --no-tags vendor/gapps_tv` (980 MB de checkout).
- Conferência: o zip `MindTheGapps-17.0.0-arm64-ATV-minimal-20260630_185024.zip` da release do
  GitHub tem sha256 `b3d473ad2510c3cfdde7decdef03ae54a60394a84420ac5e4639931b84bddeb9`, igual ao
  `.sha256sum` publicado e ao digest do GitHub. Cada APK e XML do zip foi comparado com o do
  checkout (as partes `.apk.00/.01` concatenadas): todos iguais. O `ATVOverlay` do zip é compilado
  do fonte no checkout (`overlay/`).
- Como entra: `device.mk` faz `GMS_VARIANT := minimal` e `inherit-product` do
  `vendor/gapps_tv/arm64/arm64-vendor.mk` só se o arquivo existir e `HY300_WITH_GAPPS` não for
  `false`. A minimal traz GmsCore (`PrebuiltGmsCorePano`), GSF, Play Store (`Tubesky`),
  `AndroidMediaShell` (Cast), `Katniss` (busca/Assistente), `Backdrop`, `AtvRemoteService`,
  `DfuService`, TTS, TalkBack e o calendário; **não** traz o `TVLauncher` (o launcher continua o
  do LineageOS). O `SetupWraithPrebuilt` (assistente do Google TV) sai pelo
  `hy300-gapps-overrides`: o `TvProvision` já marca o aparelho como configurado, e a conta Google
  entra por **Configurações > Contas e login**.
- Permissões privilegiadas: o produto tem `ro.control_privapp_permissions=enforce`; o MindTheGapps
  traz os `privapp-permissions-*.xml` dele, conferidos no host contra os APKs (ver o resultado da
  rodada abaixo). sepolicy segue permissive; os GApps não declaram HAL (o `check_vintf_hals.py`
  roda igual).
- **Aurora Store** 4.8.4 (GPLv3, fonte em `gitlab.com/AuroraOSS/AuroraStore`), APK da F-Droid
  `com.aurora.store_76.apk`, sha256 `fd9c75d90d0f4a7c132b9b4a5a2cf1992a45e03b8d8ff988b7dcfbc0db2c4d11`,
  pré-instalada como app comum no `/product` (atualizável pela própria loja). O APK fica fora do
  git; `device/txcz/hy300/tools/fetch_aurora.py` baixa o `index-v2.json` da F-Droid, confere a
  versão e o sha256 fixados, baixa o APK, confere de novo e gera `prebuilt/aurora/Android.bp`
  (`--from <apk>` usa uma cópia local, com a mesma conferência).
- Sem GApps: `HY300_WITH_GAPPS=false` no ambiente do build, ou sem o checkout.

**Aparelho não certificado.** Um LineageOS não passa na certificação do Play Protect; o Play Store
pode avisar "dispositivo não certificado" e alguns apps se recusam a instalar. O registro é feito
pelo usuário, com a conta Google dele:

1. Descobrir o **GSF ID** (Google Services Framework Android ID). Sem root no aparelho
   (`ro.debuggable=0`), o caminho é um app que o mostra, por exemplo o "Device ID" (Evozi), instalado
   pela Aurora Store. O app mostra o valor em hexadecimal; o formulário do Google aceita o número
   em decimal (`printf '%d\n' 0x<valor>` no PC).
2. Abrir `https://www.google.com/android/uncertified/` no PC, entrar com a mesma conta Google usada
   no projetor e colar o GSF ID.
3. No projetor: **Configurações > Apps**, limpar dados do Google Play Store e do Google Play
   Services, e reiniciar. O registro pode levar alguns minutos a algumas horas para valer.

O Widevine segue separado: os GApps não trazem DRM (ver "DRM").

#### Artefatos e como gravar

Kernel igual ao da rodada 5 (`hy300-ack-6.1 1ee24ab83ac1`, nenhum prebuilt novo nesta rodada).
`verify-boot` passa nos três boot.img; `check_vintf_hals.py`: "11 HALs obrigatórios declarados;
todo HAL declarado tem serviço no init" nas duas imagens; os 104 testes da árvore passam. Permissões
privilegiadas conferidas no host (aapt2 contra o `AndroidManifest.xml` do framework e os
`privapp-permissions` da imagem): nenhuma priv-app pede permissão privilegiada fora do allowlist
(o GmsCore pede 106, as 106 estão no XML do MindTheGapps).

Com GApps, em `~/hy300-work/lineage-artifacts/r6/` (substituídos pela rodada 7, abaixo):

| Arquivo | Tamanho | sha256 |
|---|---|---|
| `boot.img` (`gpu=panfrost`, vai na `recovery`) | 19.888.128 | `5c4436d5b5093eea16b9c50982acea667297e64dac522f2bfe6589466e6eda7b` |
| `boot-sw.img` (`gpu=sw`, reserva) | 19.888.128 | `fee8324d602acd5a224a33ef796ca7f3dbfdaf0e342edfd4b21561fdb7741200` |
| `recovery.img` | 32.614.400 | `15ee072943740ad2cfc892d85207417dd1d8d5e944a8b28c60399546727ef887` |
| `super.img` (sparse) | 1.885.061.212 | `10d2275e29363065a2bf0a0e6499fe0a66f8e9830ed9fbea15f05e7cca0d77aa` |
| `super.raw` (vai na `super`) | 3.263.168.512 | `0951489ec4f8c002ed4c91b633d3a6107379c81672dcbcb46fdb37f3f7b959df` |

Sem GApps (`HY300_WITH_GAPPS=false`), em `r6/sem-gapps/`; o `boot.img` e o `boot-sw.img` são os
mesmos:

| Arquivo | Tamanho | sha256 |
|---|---|---|
| `recovery.img` | 32.614.400 | `a27d72dda2820acf126de6a868c6d685459934dc3842f48c489198f527f29642` |
| `super.img` (sparse) | 1.403.607.032 | `845917642d10805d7eac98bd16f20be0e3425365fffafab7278c11442930caa2` |
| `super.raw` | 3.263.168.512 | `ddbfbc2c47046accaaa47b1a4a47f697a93eb1df835011cc8d3817cc1d5e4319` |

O `boot.img` mudou em relação à rodada 5 porque o fstab do ramdisk perdeu a linha do zram.

Antes de gravar:

- **Com GApps, apague o `/data`.** GApps instalados por cima de um `/data` que já subiu sem eles
  costumam deixar o Play Services sem as permissões padrão (o LineageOS recomenda instalar os
  GApps antes do primeiro boot). Pelo Alpine, depois de gravar a `super`:
  `dd if=/dev/zero of=/dev/block/by-name/userdata bs=1M count=64 && sync`; o fstab tem
  `formattable` e o Android formata no boot. O `/metadata` fica: o `adb_keys` volta sozinho, mas o
  `wifi.conf` é apagado depois de usado e precisa ser gravado de novo (roteiro em "Rodada 5").
- **Fuso**: `persist.sys.timezone` só vale num `/data` novo. Num `/data` que já existe o valor
  gravado (UTC) vence; troque em Configurações > Sistema > Data e hora (ou apague o `/data`).
- Sem GApps (`r6/sem-gapps/`) dá para gravar por cima do `/data` do boot 4.

YouTube para Android TV (`com.google.android.youtube.tv`): não vem na minimal. Não há fonte com
hash publicado fora do Google Play; a forma confiável é instalar pela Aurora Store depois do boot
(ela baixa do Google Play, com a assinatura do Google conferida pelo Android na instalação), sem
precisar de conta (sessão anônima da Aurora).

### Rodada 7: imagem de uso e ida ao Alpine pelo adb (23/11/2026)

**Perfil na cmdline**, `androidboot.hy300.perfil`:

| Perfil | Arquivo | Diag | adb pela rede |
|---|---|---|---|
| `teste` (padrão do build) | `boot.img` | ligado (com `androidboot.hy300.diag=1` ou o arquivo `ativo`) | ligado sozinho no boot_completed (porta 5555, com chave) |
| `uso` | `boot-uso.img` | desligado, mesmo com `diag=1` ou `ativo` | desligado; o usuário liga nas Opções do desenvolvedor do TvSettings: "Depuração USB" e "ADB pela rede" |

A `super` é a mesma nos dois: o `boot-uso.img` é o `boot.img` com a chave trocada por
`tools/lineage_prebuilt.py variant --set androidboot.hy300.perfil=uso` (o ID do header é
recalculado). Nos dois perfis o `hy300-net.sh` continua aplicando o `wifi.conf` e a chave do adb
que o Alpine deixar no `/metadata`; no de uso ele só não liga o adb. Para ir de um perfil ao outro
basta gravar o outro `boot.img` na `recovery` (ou trocar a chave pelo `hy300-kexec` do Alpine).
O "ADB pela rede" do TvSettings seta `service.adb.tcp.port`, que não sobrevive a um reboot: na
imagem de uso ele precisa ser religado depois de reiniciar.

**Ir ao Alpine e ficar nele, com o Lineage no ar e sem adb root:**

```bash
adb shell setprop debug.hy300.alpine 1
```

- O shell do adb pode setar `debug.*` (`debug.` é `debug_prop` no `property_contexts`, e o
  `shell.te` tem `set_prop(shell, debug_prop)`); apps comuns não podem.
- O `init.rk3566.rc` inicia o serviço `hy300-alpine` (root, `u:r:su:s0`, oneshot) em
  `on property:debug.hy300.alpine=1 && property:ro.build.type=userdebug && property:init.svc.adbd=running`.
  Na imagem de uso isso só vale depois de o usuário ligar o adb.
- `configs/init/hy300-alpine.sh` volta a prop para 0, grava a marca de ficar na `misc` (0x10000,
  `hy300-ficar\0` + `01 00 00 00`, a mesma função do diag) só se a área estiver zerada ou já com a
  marca, confere lendo de volta, faz `sync` e reboot normal (`sys.powerctl=reboot`, sem alvo, sem
  BCB). O U-Boot sobe a `boot`, o estágio 1 do Alpine vê a marca, apaga e fica sem contagem.
- Se a área da marca tiver outra coisa, não reinicia e registra em
  `/metadata/hy300-diag/alpine.txt`.
- Quando a sepolicy ficar enforcing (worker de recursos), o domínio `su` só existe no userdebug;
  o serviço continua restrito ao userdebug pelo gatilho.

Texto proposto para o `README.md` do hy300-alpine, seção "Marca de ficar e contador de boots
falhos (misc)", logo depois do bloco do `reboot-to-alpine.sh`:

> - **Com o LineageOS no ar** não há `adb root` (o userdebug do Lineage sai com
>   `ro.debuggable=0`), então o `reboot-to-alpine.sh` não grava a `misc`. O Lineage do HY300 tem
>   um gatilho próprio:
>
>   ```bash
>   adb shell setprop debug.hy300.alpine 1
>   ```
>
>   Um serviço root do Lineage (só no userdebug e com o adbd no ar) grava a mesma marca em
>   `0x10000`, com a mesma regra (só sobre área zerada ou já marcada), e faz um reboot normal. O
>   Alpine sobe pela `boot` e fica. Se a área tiver outra coisa, o Lineage não reinicia e registra
>   em `/metadata/hy300-diag/alpine.txt`. Voltar ao Lineage: `hy300-android` no Alpine.

Sugestão para o mesmo repositório (não aplicada): o `reboot-to-alpine.sh` pode tentar esse gatilho
quando `adb root` falhar, para o mesmo comando servir nos dois sistemas.

**Kernel `cae418b6c490`** (worker do kernel; detalhes em `docs/kernel-6.1.md`, "Hardware da TXCZ
no ACK"): motor de foco `hy300_focus_motor` embutido, RK628 ligado no DT e o módulo novo
`aic8800_btlpm`. Os sha256 do `prebuilt/VERSION` conferem com os arquivos (Image.gz `bb0b84b8…272a`,
dtb `b3126dba…aae6`, `aic8800_btlpm.ko` `8441a9b5…79ab`; os outros módulos iguais).

- `aic8800_btlpm` (rfkill do Bluetooth, depende do `aic8800_bsp`): o `hy300-wifi-modules.sh`
  carrega depois do `load_wifi_modules` (bsp e fdrv), só se o bsp subiu; se falhar, o Wi-Fi segue.
  `BOARD_VENDOR_KERNEL_MODULES_LOAD` registra a ordem `drm_shmem_helper`, `gpu-sched`, `panfrost`,
  `aic8800_bsp`, `aic8800_btlpm`, `aic8800_fdrv` no `modules.load` (ninguém carrega a lista
  inteira: a GPU sobe pelo `init.rk3566.rc` e o AIC8800 pelo script). O HCI do Bluetooth e o HAL
  ficam com o worker de recursos.
- Motor de foco: `/sys/class/motor_cc/motor_cc/motor` passa a `system:vendor_hy300_motor` 0660 e o
  `hd_camera_on` fica 0444 (a fábrica fazia `chmod 0777`). O caminho do gid:
  - AID de vendor `AID_VENDOR_HY300_MOTOR` (2901) em `config.fs`;
  - `product/etc/permissions/hy300-focus-motor.xml` associa a permissão
    `io.github.hy300.settings.permission.FOCUS_MOTOR` ao gid (só `/system` e `/product` podem
    associar permissão a gid);
  - o app declara essa permissão com nível `signature` e a pede, então só ele a recebe;
  - sepolicy (`sepolicy/vendor`): tipo `sysfs_hy300_motor` para
    `/devices/platform/focus-motor/motor_cc/motor_cc/{motor,hd_camera_on}` (nó `focus-motor` do DT)
    e `allow platform_app sysfs_hy300_motor:file rw_file_perms` (o app é priv-app com a chave de
    plataforma). Vale quando o boot sair do permissive.
  - Falta no aparelho: conferir `ls -lZ` do nó e o foco pelo app.

Artefatos da rodada 7 em `~/hy300-work/lineage-artifacts/` (rodada 6 em `r6/`; o primeiro build da
rodada 7, com o kernel antigo, em `r7a/`), com GApps. `verify-boot` passa nos quatro boot.img
contra o Image.gz novo; `check_vintf_hals.py`: "11 HALs obrigatórios declarados; todo HAL
declarado tem serviço no init"; 124 testes da árvore passam; nenhuma priv-app fora do allowlist.

| Arquivo | Tamanho | sha256 |
|---|---|---|
| `boot.img` (perfil `teste`, vai na `recovery`) | 19.890.176 | `55bebe21d952150bd466eecb85ed0c31a63ee2a0a8cfaa53540fc1bcd60efe65` |
| `boot-uso.img` (perfil `uso`) | 19.890.176 | `47be28acfe3c1c89ad7756acac54ee7d015da830eccaf0ba7c219fd4e72ea2c3` |
| `boot-sw.img` (perfil `teste`, `gpu=sw`) | 19.890.176 | `638f1b676bd5e49b20d77dcdaa0abebf4fb7f95edd54c89509087dcd41a9d378` |
| `recovery.img` | 32.616.448 | `4f18f2b76e4b01a9f36fcc2b13681a022c10f69302f66bafc5d052a37010c30a` |
| `super.img` (sparse) | 1.875.750.920 | `48e9ffb6cd21e84e7ab56387164b18b282c0ed2d7e79cb2bbf63336364e9e214` |
| `super.raw` (vai na `super`) | 3.263.168.512 | `9f2dd74c961641dd52f1fff67bd78b4c9b12714334239489e9a68092f80533f5` |

Valem os mesmos avisos da rodada 6 para gravar com GApps (apagar o `/data`, `wifi.conf` de novo,
fuso num `/data` antigo).

### Rodada 8: integração da branch `recursos` (23/11/2026)

Merge (não rebase) da branch `recursos` do worker de recursos nos dois repositórios: árvore
`2a82b58` (12 commits, guia em [`lineage-recursos.md`](lineage-recursos.md)) e este repositório
`ed46538` (bootlog e app prontos para o enforcing, o app usa `persist.sys.hy300.picture.*` no
Lineage). Entrou tudo:

- keystone no SurfaceFlinger (`frameworks/native/0001`, `hy300-keystone.rc` no system_ext);
- BCSH pelo VOP2 (`external/drm_hwcomposer/0001`);
- HAL de sensores para o SC7A20 (`sensors/`);
- Bluetooth: HAL AIDL padrão + `hy300-bt-uart` (`hardware/interfaces/0002`), **ligado** nesta
  imagem (`HY300_WITH_BLUETOOTH ?= true`; `false` no ambiente do build desliga);
- TV input do HDMI (`tvinput/`), ainda sem imagem: o drm_hwcomposer não compõe sideband;
- Codec2 10 bits (`codec2/0005`, depois do 0004);
- sepolicy completa (`sepolicy/vendor`, `sepolicy/system_ext/{public,private}`), com o boot ainda
  **permissive** para colher as negações dos domínios novos.

Conflitos: `sepolicy/vendor/{file.te,genfs_contexts,platform_app.te}` ficaram com a versão da
`recursos` (superconjunto; o app agora roda em `hy300_settings_app`, e o `platform_app.te` fica
vazio); o `BoardConfig.mk` ficou com uma linha de `BOARD_VENDOR_SEPOLICY_DIRS`.

O que o Soong pegou e foi corrigido (commit `10268e9`):

- `sensors`: os cabeçalhos do libfmq não passam no `-Wconversion -Werror` (sinal e 64 para 32
  bits dentro dos templates). Os includes deles ficam entre `#pragma clang diagnostic`; o código
  do HAL continua com a flag.
- `tvinput`: faltava linkar `android.media.audio.common.types-V1-ndk`, onde fica
  `AudioDeviceDescription::CONNECTION_HDMI` (a `tv.input` V1 importa os tipos V1).
- O patch do SurfaceFlinger compilou sem mudança (CompositionEngine e RenderEngine com
  `-Wconversion -Werror`); o keystone não precisou ficar atrás de flag.

Conferências: `check_sepolicy.py` ("sepolicy compila com as neverallows do build e os contextos
conferem"), `check_vintf_hals.py` ("11 HALs obrigatórios declarados; todo HAL declarado tem
serviço no init"), `verify-boot` nos quatro boot.img, 152 testes da árvore, nenhuma priv-app fora
do allowlist. Kernel `cae418b6c490`.

Artefatos em `~/hy300-work/lineage-artifacts/r8/` (substituídos pela rodada 9), com GApps. O
`boot.img`, o `boot-uso.img` e o `boot-sw.img` são os da rodada 7 (o ramdisk não mudou):

| Arquivo | Tamanho | sha256 |
|---|---|---|
| `boot.img` | 19.890.176 | `55bebe21d952150bd466eecb85ed0c31a63ee2a0a8cfaa53540fc1bcd60efe65` |
| `boot-uso.img` | 19.890.176 | `47be28acfe3c1c89ad7756acac54ee7d015da830eccaf0ba7c219fd4e72ea2c3` |
| `boot-sw.img` | 19.890.176 | `638f1b676bd5e49b20d77dcdaa0abebf4fb7f95edd54c89509087dcd41a9d378` |
| `recovery.img` | 32.620.544 | `62444c76560ae4c5d1e33fafdb4711a579cc680c81caace63fb50a45be1e6f72` |
| `super.img` (sparse) | 1.876.541.476 | `aa9535bb68cd15f73f1132a76dc4cc29f270546376842e79479c695cad5aba13` |
| `super.raw` | 3.263.168.512 | `29a4b065dd4000a300c745bdccfe24fe653b304f6c571a687c173f4da73bd67d` |

**O que conferir no aparelho, por frente** (com SELinux permissive, colher as negações de cada uma:
`adb shell 'dmesg | grep avc; logcat -b all -d | grep avc'`):

- **SELinux**: nenhuma negação dos domínios `hy300_*`, `hal_sensors_default`,
  `hal_tv_input_default`, `hal_bluetooth_default`, `vendor_misc_writer`; só então tirar
  `androidboot.selinux=permissive`.
- **Keystone**: mexer nos cantos pelo app; `dumpsys SurfaceFlinger | grep Keystone` mostra os
  cantos e se está ativo; a imagem deforma sem tela preta; `persist.sys.keystone.*` vale depois de
  reiniciar (`hy300-keystone.rc`).
- **BCSH**: brilho, contraste, saturação e matiz do app mudam a imagem (VOP2), na UI e em vídeo.
- **Sensores**: `dumpsys sensorservice` lista o acelerômetro; os valores mudam ao inclinar; o
  keystone automático reage. Se os eixos saírem trocados, `ro.vendor.hy300.accel.axes`.
- **Foco**: `ls -lZ /sys/class/motor_cc/motor_cc/motor` (system vendor_hy300_motor 0660,
  `sysfs_hy300_motor`); o app move a lente nos dois sentidos e para no fim de curso.
- **Bluetooth**: `hy300-bt-uart` liga os rfkill e acerta o `ttyS1`; o HAL acha o controlador
  (`dumpsys bluetooth_manager`), sem a pilha reiniciando em laço (se reiniciar, rebuild com
  `HY300_WITH_BLUETOOTH=false`); parear um controle ou fone; o Wi-Fi continua estável com o BT
  ligado (coexistência sem o `pta_config` da AICSemi).
- **HDMI-in**: o RK628 faz probe sem fonte; com fonte, o TV input vê o cabo e a resolução
  (`dumpsys tv_input`); a imagem ainda fica preta (sideband); o áudio chega ao alto-falante (placa
  1, taxa em `/sys/class/hdmirx/rk628/audio_rate`).
- **10 bits**: um HEVC Main10 e um VP9 perfil 2 tocam por `c2.rk.*` (não pelo software), sem
  cores erradas.
- Continuam da rodada 6/7: encoders e entrada por Surface, zram pelo `mmd`, gatilho
  `debug.hy300.alpine`, perfil `uso`.

### Rodada 9: imagem da entrada HDMI e espelhamento (23/11/2026)

Segundo merge da branch `recursos` (árvore `f0266a8`, este repositório `13cb1b6`): serviço
`vendor.hy300.hdmiin-service` (AIDL `vendor.hy300.hdmiin.IHdmiCapture` V1 congelado) que captura o
`/dev/video` do rkisp e copia pela RGA para a `Surface` do `TvView`; app `HY300HdmiInput`
(`io.github.hy300.hdmi`, priv-app no system_ext) como TV input de hardware do HDMI;
`configs/vintf/device_framework_matrix.xml` para o HAL novo; patch `frameworks/native/0002` (só
testes do keystone); no app de configurações, o modo de instalação zera o espelho nativo e o "Abrir
HDMI". Detalhes em [`lineage-recursos.md`](lineage-recursos.md).

O que o Soong pegou e foi corrigido (commit `0ca3960`):

- o `aidl_api` congelado estava em `hdmiin/aidl/aidl_api`; o Soong procura ao lado do
  `Android.bp` (`hdmiin/aidl_api`). Mudou só de lugar; o hash congelado (`ced0fd31…`) passou;
- o namespace da árvore passa a importar `hardware/rockchip/librga`;
- o serviço linka o `libhy300tvinput_core` (biblioteca estática não leva as dependências estáticas
  dela), inclui `libnativebase_headers`, `libsystem_headers` e `libcutils_headers` (o
  `vndk/window.h` precisa) e passa o pedido do `ioctl` como `int` (assinatura do bionic, que
  quebrava no `-Wshorten-64-to-32`);
- `tools/apply_patches.py`: patches empilhados (`codec2/0005` sobre o 0002,
  `frameworks/native/0002` sobre o 0001) faziam o script parar com "não encaixa", porque o de
  baixo não se desfaz sozinho com o de cima aplicado. Agora a série é desfeita de trás para a
  frente numa cópia dos arquivos tocados para saber o que já está aplicado (teste novo).

Conferências: `check_sepolicy.py` ("sepolicy compila com as neverallows do build e os contextos
conferem"), `check_vintf_hals.py` ("11 HALs obrigatórios declarados; todo HAL declarado tem
serviço no init"; o `vendor.hy300.hdmiin` está no manifesto do vendor e na matriz), `verify-boot`
nos quatro boot.img, 168 testes da árvore, nenhuma priv-app fora do allowlist (o `HY300HdmiInput`
traz o `privapp-permissions-hy300-hdmi.xml`). Kernel `cae418b6c490`; SELinux permissive;
Bluetooth ligado; GApps.

Artefatos em `~/hy300-work/lineage-artifacts/r9/` (**não bootam**, ver rodada 10). `boot.img`,
`boot-uso.img` e `boot-sw.img` iguais aos das rodadas 7 e 8:

| Arquivo | Tamanho | sha256 |
|---|---|---|
| `boot.img` | 19.890.176 | `55bebe21d952150bd466eecb85ed0c31a63ee2a0a8cfaa53540fc1bcd60efe65` |
| `boot-uso.img` | 19.890.176 | `47be28acfe3c1c89ad7756acac54ee7d015da830eccaf0ba7c219fd4e72ea2c3` |
| `boot-sw.img` | 19.890.176 | `638f1b676bd5e49b20d77dcdaa0abebf4fb7f95edd54c89509087dcd41a9d378` |
| `recovery.img` | 32.622.592 | `cddd11c512275b3f859d7774349eb6a7b83218a4a20a676ed2016021a3d179b3` |
| `super.img` (sparse) | 1.876.717.576 | `7c16f6601cc599864f089ca8ee95b94d419d195b9c62813ed5e942bf93be0427` |
| `super.raw` | 3.263.168.512 | `e934c9415d1ae4efc0cd96a5fab00f205b5101af8eaf9d2f73a7bb7846acb9cb` |

A conferir no aparelho, além da lista da rodada 8:

- **HDMI com imagem**: `dumpsys tv_input` mostra a entrada "HDMI"; o app HDMI (launcher ou "Abrir
  HDMI") mostra a fonte em tela cheia, com keystone e BCSH; trocar a resolução da fonte não trava.
  Se o serviço não achar o vídeo, conferir o nome do nó (`rkisp_mainpath` contra `rkisp-vir0` em
  `/sys/class/video4linux/*/name`) e trocar `ro.vendor.hy300.hdmiin.video`. Áudio: a placa
  `rockchiphdmiin` tem de ser a 1 (`cat /proc/asound/cards`).
- **Espelhamento**: cada modo de instalação (mesa/teto, frente/trás) espelha uma vez só; um app
  de espelhamento (AirScreen, Cast) também recebe o keystone.
- Negações de SELinux dos domínios novos (`hy300_hdmiin`, `hy300_hdmi_app`).

### Rodada 10: o boot 6 e o HDMI In do áudio (23/11/2026)

**Boot 6** (super da rodada 9 sobre os dados da 7): `boot_completed=0` aos 501 s, sem panic; o diag
voltou ao Alpine (logs em `~/hy300-work/lineage-artifacts/boot6/`). O coordenador voltou a super da
rodada 7.

**Causa:** o HAL de áudio AIDL de exemplo (`android.hardware.audio.service-aidl.example`, APEX
`com.android.hardware.audio`) abortou 55 vezes com
`Function: convertModuleConfigToAidl Line: 534 Failed result (BAD_VALUE)`. A linha 534 do
`hardware/interfaces/audio/aidl/default/XsdcConversion.cpp` é a conversão das devicePorts, e o log
logo antes diz qual regra:
`convertDevicePortsInModuleToAidl: Review Audio Policy config: <attachedDevices> list is incorrect or devicePort "HDMI In" type= AudioDeviceDescription{type: IN_DEVICE, connection: hdmi} is incorrect.`
A regra (mesmo arquivo, `convertDevicePortsInModuleToAidl`):

```cpp
if (xAttachedDeviceSet.count(port.name) != devicePort.device.type.connection.empty()) {
    ... return unexpected(BAD_VALUE);
```

um devicePort está em `<attachedDevices>` **se e só se** a conexão do tipo dele for vazia. A
tabela legado para AIDL (`frameworks/av/media/audioaidlconversion/AidlConversionCppNdk.cpp`,
`getAudioDevicePairs`) dá a `AUDIO_DEVICE_IN_HDMI` a conexão `HDMI`: é dispositivo externo, que só
existe depois de conectado. Anexado ao módulo, o HAL aborta, reinicia em laço e o system_server
fica preso no AudioService, como na rodada 4.

**Correção:** o "HDMI In" (`CARD_1_DEV_0`, placa `rockchiphdmiin`) passa a
`AUDIO_DEVICE_IN_TV_TUNER`, tipo embutido (conexão vazia) e sempre presente, o que é verdade no
HY300: o RK628 é soldado na placa. Endereço, perfis, mixPort `hdmi input` e rota continuam. O HAL
de TV input anuncia o mesmo tipo (`AudioDeviceType::IN_TV_TUNER`) e o app HDMI procura a porta
`DEVICE_IN_TV_TUNER` para o patch de áudio. A alternativa (manter `IN_HDMI` fora do
`<attachedDevices>`) exigiria alguém conectar o dispositivo com `setWiredDeviceConnectionState`
antes de cada uso e o HAL de exemplo ler o perfil da placa nessa hora: mais partes sem teste.

**Teste no host:** `tools/check_audio_policy.py` aplica as regras do `XsdcConversion.cpp` aos
módulos do `audio_policy_configuration.xml` do vendor (incluindo os `xi:include`): um
`<devicePorts>` e um `<mixPorts>` por módulo, tipo presente na tabela (`convertDeviceTypeToAidl`),
anexado só se a conexão for vazia, e rotas só entre portas que existem
(`getSinkPortId`/`getSourcePortIds`). A conexão de cada tipo vem da própria tabela do AOSP, lida do
checkout. O `r_submix` não passa pela conversão no HAL (`AudioPolicyConfigXmlConverter::init`) e
fica de fora. O XML do boot 6 fica em `tools/tests/data/` como caso que tem de falhar. Rodar a
conversão do AOSP no host não deu: o `audio_policy_config_xml_converter_tests` só compila para o
aparelho (libmedia_helper e os parsers do xsdc não são de host).

**Outras falhas da rodada 9 no mesmo log:** nenhuma. Os 55 tombstones são todos do HAL de áudio.
`vendor.sensors-hy300`, `vendor.tv-input-hy300`, `vendor.hy300-hdmiin` e
`vendor.bluetooth-default` ficaram `running` com o PID do começo do boot (sem reinício); o
`hy300-bt-uart` terminou (oneshot); o SurfaceFlinger rodou sem erro do keystone (só
"trackPendingFrame: Invalid present fence", que já aparecia). O logcat e o dmesg do diag guardam
só o fim do boot, então o que veio antes do laço do áudio não ficou registrado.

Conferências: `check_audio_policy.py` (árvore e o XML da imagem), `check_sepolicy.py`,
`check_vintf_hals.py` ("11 HALs obrigatórios declarados; todo HAL declarado tem serviço no
init"), `verify-boot` nos quatro boot.img, 178 testes da árvore, nenhuma priv-app fora do
allowlist. Árvore `3948804`.

Artefatos em `~/hy300-work/lineage-artifacts/` (rodada 9 em `r9/`); `boot.img`, `boot-uso.img` e
`boot-sw.img` iguais aos das rodadas 7 a 9:

| Arquivo | Tamanho | sha256 |
|---|---|---|
| `boot.img` | 19.890.176 | `55bebe21d952150bd466eecb85ed0c31a63ee2a0a8cfaa53540fc1bcd60efe65` |
| `boot-uso.img` | 19.890.176 | `47be28acfe3c1c89ad7756acac54ee7d015da830eccaf0ba7c219fd4e72ea2c3` |
| `boot-sw.img` | 19.890.176 | `638f1b676bd5e49b20d77dcdaa0abebf4fb7f95edd54c89509087dcd41a9d378` |
| `recovery.img` | 32.622.592 | `9ae5a837075755562192d073e109a065c9c8f4cfd2be0a4d1b85a0d77890d0d6` |
| `super.img` (sparse) | 1.876.717.576 | `84fb2ca2a4f1a253f8d007bf82361042737ceb7d33a3d80d0cd627fdbd59651a` |
| `super.raw` | 3.263.168.512 | `aa7197a3d7a443918911b4f39dba5717194070e2be9337548341f93caf5ed5ed` |

No aparelho, além das listas das rodadas 8 e 9: `logcat -s AHAL_Config` sem "Review Audio Policy
config", `dumpsys media.audio_policy` com o "HDMI In" (`AUDIO_DEVICE_IN_TV_TUNER`,
`CARD_1_DEV_0`) entre os dispositivos de entrada disponíveis, e o áudio do HDMI no alto-falante
com o app HDMI aberto.

### Rodada 11: som na placa certa e Bluetooth (23/11/2026)

O boot 7 (rodada 10) completou: boot_completed aos 74 s, keystone carregado e inativo, acelerômetro
com dados, "HDMI In" na audio policy sem crash, RK628 com probe (`video0` = `rkisp_mainpath`), nó
do motor com `system:vendor_hy300_motor` 0660 e `sysfs_hy300_motor`, MemAvailable 607 MB. Logs em
`~/hy300-work/lineage-artifacts/boot7/`.

**Som (kernel `acf8a8518737`).** As placas vinham trocadas: `/proc/asound/cards` mostrava 0 =
`rockchiphdmiin` e 1 = `rockchip-i2s-sound` (o alto-falante). O "Speaker" do audio policy não tem
endereço, e o módulo primário do HAL de exemplo usa então o padrão `PrimaryMixer::kAlsaCard` (placa
0, `StreamPrimary::getCardAndDeviceId`): o áudio ia para o I2S do RK628 (a placa 0 também tem
`pcmC0D0p`). O `dumpsys media.audio_flinger` mostrava a saída primária em standby sem escrita
nenhuma, e os logs do HAL do começo do boot já tinham saído do buffer. O worker do kernel fixou a
ordem (`hy300,card-index` no DT): alto-falante = 0, `rockchiphdmiin` = 1, o que também acerta o
`CARD_1_DEV_0` do HDMI In. Os sha256 do `prebuilt/VERSION` conferem (Image.gz `bd4b62f3…8d6b`, dtb
`fdb26ebf…8b54`, módulos iguais aos do `cae418b6c490`).

**Bluetooth (parado em `BLE_TURNING_ON`).** O `vendor.bluetooth-default` estava `running`, o
`/dev/ttyS1` com `bluetooth:bluetooth` 0660 e `hci_attach_dev`, o `aic8800_bsp` carregou o patch do
BT (`bt patch version ... Nov 09 2023`, `uart_baud 1500000`, `uart_flowctrl 1`) e o
`/sys/class/bluetooth` estava vazio (sem `hci0`, como esperado no modo UART). A causa está no HAL
padrão: o `initialize()` tenta primeiro o hci do kernel (`NetBluetoothMgmt::openHci`), e o
`waitHciDev()` reenvia o "Read Index List" a cada 500 ms **sem prazo** enquanto nenhum hci aparece.
Sem `hci0`, o `initialize()` nunca volta e a pilha fica em `BLE_TURNING_ON`; o HCI_RESET nem chega
a ser enviado. Correções:

- patch `hardware/interfaces/0003`: com `vendor.ser.bt-uart` definido, o HAL abre o tty direto
  (H4 pela UART), sem passar pelo hci do kernel;
- o `hy300-bt-uart` roda de novo quando o `hy300-wifi-modules` termina
  (`vendor.hy300.wifi.iface`): o `aic8800_btlpm` cria o rfkill `bluetooth` depois da primeira
  passada, e no boot 7 ele ficou bloqueado (`rfkill2 soft=1`);
- vendor-init da AICSemi: não entra. O `aic8800_bsp` já carrega o patch e a configuração da UART
  do BT pelo SDIO, e no Linux o AIC8800 por UART sobe com o H4 genérico
  (`hciattach ... any 1500000 flow`). Se o controlador não responder ao HCI_RESET, o próximo passo
  é olhar `logcat -s android.hardware.bluetooth-service.default bt_hci`.

**SELinux.** O `insmod` do `aic8800_bsp` e do `aic8800_btlpm` era negado em `module_load` porque
`/vendor/lib/modules` ficava `vendor_file` (o AOSP não rotula esse diretório). O
`sepolicy/vendor/file_contexts` agora dá `vendor_kernel_modules`, que o `hy300_wifi_modules` e o
`vendor_modprobe` já podem carregar. As outras negações do boot 7 não são do insmod; as do
`hy300_bootlog` (SurfaceFlinger escrevendo no socket e no binder dele, fence do composer) ficam para
o worker de recursos.

**Outros.** Builds de teste com `ro.logd.size=1M` (com `ro.config.low_ram` os buffers do logd são
mínimos e o log do HAL de Bluetooth sumiu antes de ser lido). A Aurora Store voltou à imagem: o
`rsync --delete` do kernel em `prebuilt/` tinha apagado o `prebuilt/aurora`, e as imagens das
rodadas 7 a 10 saíram sem ela; agora ela fica em `prebuilt-apps/aurora/`.

Conferências: `check_audio_policy.py`, `check_sepolicy.py`, `check_vintf_hals.py` ("11 HALs
obrigatórios declarados; todo HAL declarado tem serviço no init"), `verify-boot` nos quatro
boot.img, 183 testes da árvore, nenhuma priv-app fora do allowlist. Árvore `ffb218a`.

Artefatos em `~/hy300-work/lineage-artifacts/` (rodada 10 em `r10/`). Boot e super mudaram (kernel
novo no boot; Bluetooth, sepolicy, logd e Aurora na super):

| Arquivo | Tamanho | sha256 |
|---|---|---|
| `boot.img` | 19.892.224 | `3f27d6f43a026374bf274ea6a59a8e885db5d83630c3b7978d45e595d295aab0` |
| `boot-uso.img` | 19.892.224 | `49b0567f7f172a9435d4a4c86968346f5b18058484213779b5a6840f799ab8b5` |
| `boot-sw.img` | 19.892.224 | `4756c318c876924c01f5de5a34d1292871564d3d628b7184db026155fac2a271` |
| `recovery.img` | 32.624.640 | `8b8034c4fa40dc98fd1d8997d0bb1ee118569c75a4e7c2188cd229773e13ac17` |
| `super.img` (sparse) | 1.886.056.540 | `7b704b92812e3649531224452a13ea445019c5d267c7a8ac47b6cd414ed2e14a` |
| `super.raw` | 3.263.168.512 | `86f786cf60319e6456aa2084d12fdb47408fc6dde3096b7988732dc8c7975378` |

A conferir no aparelho: `/proc/asound/cards` com 0 = alto-falante e 1 = `rockchiphdmiin`; som no
alto-falante; áudio do HDMI com o app HDMI aberto; `dumpsys bluetooth_manager` em `ON` com
endereço; `rfkill` do `bluetooth` com `soft=0`; parear um controle; nenhuma negação `module_load`;
Aurora Store no launcher.

### Rodada 12: adb root, ClearKey e encoder sem lock (23/11/2026)

O boot 8 (rodada 11) confirmou as placas de som certas (0 = alto-falante, 1 = `rockchiphdmiin`),
áudio escrevendo no card 0 sem erro, Bluetooth `ON` e a Aurora presente. O alto-falante físico
ainda não foi ouvido.

**adb root e adb remount.** O `vendor/lineage/config/common.mk` liga
`PRODUCT_NOT_DEBUGGABLE_IN_USERDEBUG` (fora do `WITH_ADB_INSECURE`), e o userdebug saía com
`ro.debuggable=0`. É variável de valor único do produto: o produto de topo não a desfaz (vazio herda
o valor de cima, e `false` vira verdadeiro no `add_json_bool` do `soong_extra_config.mk`). O patch
`vendor/lineage/0001` faz o `common.mk` respeitar `TARGET_USERDEBUG_DEBUGGABLE`, que o
`lineage_hy300.mk` liga. O build sai com `ro.debuggable=1`, `ro.secure=1` e `ro.adb.secure=1` (a
chave do adb continua exigida). O `boot.img` não mudou (o `ro.debuggable` fica no `build.prop` do
system).

Remount: o kernel tem `CONFIG_OVERLAY_FS`, `CONFIG_DM_SNAPSHOT`, `CONFIG_DM_USER` e loop; não há AVB
(`verifiedbootstate=orange`); as partições são lógicas na `super` (3,26 GB, ~1,9 GB usados) e o
`/metadata` monta no primeiro estágio. Passos, com o Lineage no ar:

```bash
adb root
adb remount          # na primeira vez cria o "scratch" e pede reboot
adb reboot           # reboot normal: o U-Boot sobe o Alpine; voltar com hy300-android
adb root && adb remount   # agora /system, /vendor, /product... ficam graváveis por overlayfs
```

O scratch do overlayfs fica no espaço livre da `super` (ou, sem espaço, num arquivo no `/data`
pelo `gsid`); `adb enable-verity` desfaz. **Atenção ao reboot**: o `adb reboot` cai no autoboot do
Alpine, que volta ao Lineage em 5 s; para ficar no Alpine, `adb shell setprop debug.hy300.alpine 1`.
Não testado no aparelho. Na imagem de uso o perfil continua decidindo se o adb liga.

**ClearKey (YouTube para TV fechava).** O app (Cobalt) chama
`MediaDrm.isCryptoSchemeSupported(Widevine)` e recebia `IllegalArgumentException: Failed to query
crypto scheme support`. No código: sem nenhum `IDrmFactory`, `DrmHalAidl` e `DrmHalHidl` ficam com
`mInitCheck = ERROR_UNSUPPORTED` (`mFactories.size() == 0`), `DrmHal::initCheck()` devolve isso,
`DrmUtils::MakeObject()` devolve nulo e o `JDrm::IsCryptoSchemeSupported` dá `BAD_VALUE`, que o JNI
vira exceção. Com um `IDrmFactory`, o `initCheck` é `NO_INIT`, o `MakeDrm` funciona e
`DrmHalAidl::isCryptoSchemeSupported` percorre as fábricas, não acha o UUID do Widevine e devolve
`false` com `OK`. Entrou o `android.hardware.drm-service-lazy.clearkey` (AOSP, sob demanda, com
`interface aidl android.hardware.drm.IDrmFactory/clearkey` e o fragmento VINTF), e o
`required_hals.txt` passou a exigir o `IDrmFactory/clearkey`. Widevine continua fora; ele entra na
rodada 13.

**Encoder por Surface preto** (scrcpy com `c2.rk.avc.encoder`, boot 8): `Gralloc5: lock(...) failed:
3`, `C2AllocatorGralloc: failed transaction: lock(RGBA_8888)`, `C2RKMpiEnc: failed to
mapInputBuffer with err 14`. O buffer RGBA da Surface de entrada (display virtual) vem do minigbm
sem uso de CPU, e o encoder mapeava o bloco pela CPU só para saber o layout e para o dump. O MPP
(RGBA direto no VEPU540, `hasRkVenc`) e a RGA já recebem o fd do dma-buf. Patch `codec2/0006`: com
o gralloc genérico não há lock; o layout vem do formato HAL do handle (`C2RKGenericInput.h`:
RGBA/RGBX/BGRA/IMPLEMENTATION_DEFINED são RGBA, YCBCR_420_888/NV12 são YUV), e o dump de quadros de
entrada fica de fora. Teste no host (`tools/tests/test_codec2_encoder_input.py`, gtest tirado do
patch) com o caso do boot 8: entrada RGBA sem CPU nunca mapeia.

Conferências: `check_audio_policy.py`, `check_sepolicy.py`, `check_vintf_hals.py` ("12 HALs
obrigatórios declarados; todo HAL declarado tem serviço no init"), `verify-boot` nos quatro
boot.img, 190 testes da árvore, nenhuma priv-app fora do allowlist. Árvore `d702fa3`, kernel
`acf8a8518737`.

Artefatos em `~/hy300-work/lineage-artifacts/` (rodada 11 em `r11/`). **Só a `super` mudou** (e o
`recovery.img`, que não se grava): os boot.img são os da rodada 11.

| Arquivo | Tamanho | sha256 |
|---|---|---|
| `boot.img` | 19.892.224 | `3f27d6f43a026374bf274ea6a59a8e885db5d83630c3b7978d45e595d295aab0` |
| `boot-uso.img` | 19.892.224 | `49b0567f7f172a9435d4a4c86968346f5b18058484213779b5a6840f799ab8b5` |
| `boot-sw.img` | 19.892.224 | `4756c318c876924c01f5de5a34d1292871564d3d628b7184db026155fac2a271` |
| `recovery.img` | 32.624.640 | `9dedf36d4c6872640ccb5f8cfb70097cf4a8ba71ea0a37ec3f8faa9a2310b156` |
| `super.img` (sparse) | 1.886.421.084 | `857116e574e2293f867bb8836b8d7dc3ba9dd9a355b2a0e150bd019e24d3c59d` |
| `super.raw` | 3.263.168.512 | `276bf514b89948f1e5105fe09a839200b06e7d491b769f2ebce24281849b8e37` |

A conferir no aparelho: `getprop ro.debuggable` = 1 e `adb root`; `adb remount` (e o reboot);
YouTube para TV abre e toca vídeo sem DRM; `lshal`/`service list` com o `IDrmFactory/clearkey`
subindo sob demanda; scrcpy com `--video-encoder=c2.rk.avc.encoder` mostra a tela, sem
"mapInputBuffer" no logcat.

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

### Estado (boots 1 a 4)

Só conta como visto no aparelho o que está nos logs de `~/hy300-work/lineage-artifacts/boot{1,2,3}`
e nas medições do boot 4 (`boot4/medicao`, e leituras pelo adb durante a rodada 6).

**Feito e visto no aparelho**

- Primeiro boot pelo Alpine, com o ciclo do diag (logs no `/metadata`, marca de ficar) e a volta
  automática ao Alpine.
- Kernel ACK `hy300-ack-6.1` com o DT corrigido: sem tempestade de IRQ ("GPIO Key Home" = 0).
- Display (painel LVDS 1024x600 a 60 Hz) e bootlog nativo.
- Boot completo (boot 4): boot_completed em menos de 3 min, sem reinício depois dos 480 s.
- GPU Panfrost (Mesa, GLES 3.1) sem erro.
- Wi-Fi AIC8800 com a pilha do Android (DHCP) e adb pela rede com chave.
- Áudio (HAL core e efeitos) e o serviço do Codec2 com os decoders `c2.rk.*`.
- CPUs em performance a 1,8 GHz.
- Shutdown e reboot.

**Feito, sem verificação no aparelho**

- App de configurações (`HY300Settings`) como priv-app: o item "Projetor" resolve para ele
  (`query-activities`); a correção do seletor de Configurações é da rodada 6.
- Decodificação por hardware tocando vídeo (o componente sobe; falta tocar um vídeo).
- Rodada 6: encoders, entrada por Surface, zram pelo `mmd` com writeback, diag mais leve,
  `TvProvision`, fuso, GApps e Aurora Store.

**Falta**

- Bluetooth e sensores.
- Widevine (os GApps não trazem DRM).
- Vídeo 10 bits.
- sepolicy própria (hoje permissive).
- Keystone no SurfaceFlinger.
- Entrada HDMI (RK628, vídeo e áudio).

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

Levantamento de 22/11, antes do primeiro build; o estado atual está em "Estado (boots 1 a 3)".

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
