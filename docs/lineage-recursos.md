# LineageOS 24 no HY300: keystone, imagem, sensores, foco, Bluetooth, HDMI-in, 10 bits e sepolicy

Trabalho da branch `recursos` (árvore do aparelho `android_device_hy300_rk3566` e este
repositório). Nada foi testado no aparelho: o que está marcado como testado foi no host.
Estado geral do LineageOS em [`lineageos.md`](lineageos.md).

## Resumo

| Frente | Como ficou | Testado no host | Falta |
|---|---|---|---|
| Keystone | patch `frameworks/native/0001`: homografia dos 4 cantos no RenderEngine | gtest da matemática (17 casos) | ver no aparelho |
| Imagem (BCSH) | patch `external/drm_hwcomposer/0001`: bloco BCSH do VOP2 pelas propriedades do conector | gtest da leitura das props | ver se o VOP2 muda a imagem |
| Keystone automático | HAL de sensores AIDL próprio (`sensors/`) | gtest com sysfs e input falsos | ligar no aparelho |
| Foco | esquema do worker do Lineage (grupo `vendor_hy300_motor`, permissão `FOCUS_MOTOR`) + sepolicy | teste do grupo | mover a lente |
| Bluetooth | HAL AIDL padrão do AOSP + `hy300-bt-uart` | gtest com rfkill falso e pty | `HY300_WITH_BLUETOOTH=true` e teste |
| Entrada HDMI | HAL de TV input próprio (`tvinput/`) + HDMI In no audio policy | gtest da lógica | consumidor da imagem (ver abaixo) |
| Vídeo 10 bits | patch `hardware/rockchip/codec2/0005` | gtest das regras | tocar HEVC Main10 e VP9 perfil 2 |
| SELinux | `sepolicy/vendor` e `sepolicy/system_ext` | `tools/check_sepolicy.py` (neverallows do build) | trocar para enforcing depois do teste |

Regra de build seguida: nada disto rodou o Soong. Os patches foram conferidos com
`git apply --check` no checkout e o código novo compilado no host com os cabeçalhos do checkout
(incluindo os AIDL gerados do último build).

## Keystone (correção de trapézio)

**Fábrica (RE):** o SurfaceFlinger da Rockchip (`/system/bin/surfaceflinger`, 32 bits) abre
`/system/lib/librkgfx_dc.so` ("keystone v5.1") e chama `RKGFX_DC_updatemesh`, `calculateMVP`,
`drawMesh` e `draw_mask`: uma malha GLES na composição final, com máscara preta fora do
quadrilátero. Lê `persist.sys.keystone.{lt,lb,rt,rb}` ("x,y", y para cima), `update` (gatilho, volta
a 0), `reset` ("reset all point (0,0)"), `disable`, `mirror_x`, `mirror_y` e `display.id`.

**Aqui:** `Keystone/KeystoneController` numa thread parada em `__system_property_wait` (custo zero
por quadro) relê tudo quando `update` vira 1, devolve 0 e pede um quadro. `KeystoneMath` monta a
homografia projetiva (forma fechada de Heckbert, quadrado unitário para o quadrilátero), com os
cantos convertidos de 1280x720 para o tamanho real do display, e recusa quadriláteros não
convexos (fica sem keystone, nunca tela preta). O resultado vai em
`CompositionRefreshArgs::keystone` só para o display principal (um display virtual espelhando a
mesma pilha de camadas não recebe), entra no `DisplaySettings` e o `SkiaRenderEngine` aplica no
canvas antes da escala do display, com filtro linear. Com keystone ativo o display compõe pelo
cliente (uma passada de GPU, como na fábrica); zerado, nada muda.

- `disable`, `mirror_x` e `mirror_y` valem no próximo `update=1`.
- `display.id` é ignorado: só o display principal.
- `hy300-keystone.rc` (system_ext) dá o gatilho quando as props persist carregam; o
  `setprop` do `init.rk3566.rc` saiu (o `vendor_init` não pode gravar `persist.sys.*`).
- `dumpsys SurfaceFlinger | grep Keystone` mostra os cantos e se está ativo.

## Imagem: brilho, contraste, saturação e matiz

Rotas avaliadas:

1. **Matriz de cor do SurfaceFlinger** (como o modo noturno): o VOP2 não tem CTM e brilho e
   contraste precisam de deslocamento, então o drm_hwcomposer mandaria tudo para a GPU
   (`CtmByGpu`) sempre que a imagem saísse do neutro.
2. **Bloco BCSH do VOP2** (escolhida): o kernel BSP (`rockchip_drm_drv.c`) põe
   `brightness`, `contrast`, `saturation` e `hue` (0 a 100, neutro 50) em todo conector, e o
   `vop2_tv_config_update` aplica no hardware depois da composição. É o que o HWC da Rockchip
   fazia. Sem custo de GPU, vale para vídeo em overlay e para a UI.

O drm_hwcomposer lê `persist.sys.hy300.picture.<item>` (display principal) e grava as quatro
propriedades em cada commit; só relê as props quando o serial global de propriedades muda.
**O nome mudou**: o app de configurações é do sistema, e a sepolicy do Treble proíbe o sistema
de gravar qualquer prop do vendor (`persist.vendor.<item>.main`, a da fábrica). O app escolhe o
nome pela ROM (`ro.lineage.version`): fábrica continua com `persist.vendor.*.main` e o
`vendor.display.timeline`.

## Keystone automático: HAL de sensores

`android.hardware.sensors-service.hy300` (ISensors V3, só sensores contínuos sem acordar). O
acelerômetro vem de uma interface abstrata (`AccelSource`); o backend é configurado por props:

| Prop | Padrão | O quê |
|---|---|---|
| `ro.vendor.hy300.accel.backend` | `rk-gsensor` | `rk-gsensor`, `input` ou `iio` |
| `ro.vendor.hy300.accel.device` | `gsensor` | nome do input (ou do dispositivo IIO) |
| `ro.vendor.hy300.accel.control` | `/dev/mma8452_daemon` | nó de controle do gsensor |
| `ro.vendor.hy300.accel.scale` | 9,80665/16384 | m/s² por unidade crua |
| `ro.vendor.hy300.accel.axes` | `x,y,z` | troca e sinal dos eixos (`-y,x,z`...) |

O driver do kernel (`GS_SC7A20`, framework gsensor da Rockchip) só mede depois de
`GSENSOR_IOCTL_START`; o HAL liga ao ativar o sensor e desliga ao desativar, com
`GSENSOR_IOCTL_APP_SET_RATE` no período pedido. Sem o dispositivo o serviço sobe vazio.

## Foco

O worker do Lineage fez a permissão do motor na árvore principal: nó
`system:vendor_hy300_motor 0660`, AID do vendor no `config.fs`, permissão de assinatura
`io.github.hy300.settings.permission.FOCUS_MOTOR` (mapeada para o gid em
`/product/etc/permissions`). Esta branch usa o mesmo esquema; a sepolicy dá o tipo
`sysfs_hy300_motor` ao nó (genfs `/devices/platform/focus-motor/...`) e só o domínio do app pode
escrever. O app não precisou de mudança de ABI: o driver novo aceita `\n` e devolve sucesso.

## Bluetooth

Sem blobs: HAL AIDL padrão do AOSP (`android.hardware.bluetooth-service.default`) e
`hy300-bt-uart`, que no boot liga todos os rfkill de tipo `bluetooth` (`bt_default` do
rfkill-rk e `bluetooth` do `aic8800_btlpm`) e põe `/dev/ttyS1` em 1,5 Mbaud com RTS/CTS (o HAL
abre o tty cru e não ajusta velocidade). Dois modos por `ro.vendor.hy300.bt.mode`:

- `uart` (padrão): o HAL fala H4 direto no tty (`vendor.ser.bt-uart`);
- `hci`: disciplina de linha N_HCI, o kernel cria o `hci0` e o HAL usa o canal de usuário
  (precisa de `CONFIG_BT_HCIUART_H4`).

A `libbt-vendor` da AICSemi não entra (é do HAL HIDL antigo). O que ela fazia além da
velocidade (`pta_config` de coexistência com o Wi-Fi, modo de sono) não é enviado: se o
Bluetooth atrapalhar o Wi-Fi, é por aí. Tudo atrás de `HY300_WITH_BLUETOOTH=true`. Para áudio
pelo Bluetooth (A2DP), desfazer a parte de Bluetooth do patch `hardware/interfaces/0001` (o APEX
de áudio deixa de declarar o módulo `bluetooth`). O "modo caixa de som" do app
(`persist.bluetooth.rka2dpsink`) é da pilha da Rockchip: no AOSP o A2DP sink é
`bluetooth.profile.a2dp.sink.enabled`, só de build.

## Entrada HDMI

`android.hardware.tv.input-service.hy300` (AIDL V1): uma entrada HDMI, achando o `/dev/videoN`
do rkisp (`rkisp_mainpath`) e o subdev do RK628 pelo nome no sysfs. Uma thread lê o 5 V do cabo
(`V4L2_CID_DV_RX_POWER_PRESENT`) e a resolução (`VIDIOC_SUBDEV_QUERY_DV_TIMINGS`) e avisa o
framework (`STREAM_CONFIGURATIONS_CHANGED`). `openStream` devolve um sideband com o fd do nó de
captura e a geometria.

**Áudio:** "HDMI In" (`CARD_1_DEV_0`, a placa `rockchiphdmiin`) no módulo primário do audio
policy, sem rota para o alto-falante. O HAL de áudio de exemplo do AOSP escolhe a placa ALSA pelo
endereço; o TvInputHardwareManager pede o patch HDMI In para a saída e o audio policy monta a
ponte por software. Confirmar no aparelho que a placa é a 1 e a taxa da fonte
(`/sys/class/hdmirx/rk628/audio_rate`): a porta aceita 32, 44,1 e 48 kHz.

**Imagem, o que falta:** o TV input AIDL só entrega sideband, e o drm_hwcomposer não compõe
sideband (o SurfaceFlinger desenha preto). Além disso uma camada sideband não passa pela
composição pelo cliente, onde o keystone é aplicado. Caminhos:

1. **Recomendado:** serviço do vendor que captura o V4L2 e copia (RGA) para uma `Surface` entregue
   por um `TvInputService` do app (sessão com `onSetSurface`), por uma interface AIDL estável
   própria. A imagem vira camada comum: keystone e BCSH funcionam, como na fábrica (o app
   `rkCamera3` usava a câmera, não sideband).
2. Sideband no drm_hwcomposer (importar os dma-buf do V4L2 num plano NV12): sem custo de GPU, mas
   sem keystone.

Nos dois casos falta um `TvInputService` no app (APIs de sistema, permissão
`TV_INPUT_HARDWARE`); o build do app pelo Gradle usa só o SDK público.

## Vídeo 10 bits

O RK3566 já é reconhecido com 10 bits (AVC, HEVC, VP9) e, com o gralloc genérico, o decodificador
fica sempre em buffer mode: o MPP decodifica em NV15 e a RGA (ou a CPU) converte para NV12 de 8
bits no bloco do minigbm, o que o Panfrost e o painel de 8 bits usam. O patch `codec2/0005`
corrige o que impedia:

- a RGA recebia o `hor_stride` do MPP (bytes) como `wstride`, que para 10 bits é em pixels;
- o componente anunciava P010 (`ro.board.api_level` 202604 passa no `isP010Allowed`), que o
  minigbm genérico não aloca; agora não anuncia e um pedido de P010 vira `YCBCR_420_888`.

HDR (PQ/HLG) sai em 8 bits com os metadados de cor; o tone mapping fica com o RenderEngine.

## SELinux

`sepolicy/vendor` e `sepolicy/system_ext/{public,private}` na árvore. Conferência no host:

```sh
python3 -I tools/check_sepolicy.py ~/android/lineage
```

Refaz o `policy.conf` das neverallows com o m4 e as flags do último build (script de regra em
`out/soong`), troca a política da árvore principal pela desta, compila com o `checkpolicy` do
build e confere `file_contexts`, `property_contexts` e `service_contexts` com o `checkfc`.

Origem: negações dos boots 1 a 3. A maioria vinha de HALs sem rótulo rodando como `init`
(composer, allocator, Codec2), de `/dev/dri` sem rótulo e das libs do Mesa e do minigbm
carregadas por processos do sistema. Decisões:

| Quem | Domínio |
|---|---|
| App de configurações | `hy300_settings_app` (seapp_contexts), não `platform_app` |
| Animação de boot | `hy300_bootlog`; o bootanimation do logo volta ao `bootanim` |
| `hy300-clear-bcb` (todo build) | `vendor_misc_writer` do AOSP, o único do vendor que pode escrever na misc |
| `hy300-wifi-modules` | `hy300_wifi_modules` |
| `hy300-bt-uart` | `hy300_bt_uart` |
| HALs próprios | `hal_sensors_default`, `hal_tv_input_default`, `hal_bluetooth_default` |
| `hy300-diag`, `hy300-net`, `hy300-alpine` | continuam no `su` (só userdebug, onde o `su` é permissivo) |

Mudanças que o Treble exigiu: BCSH em prop do sistema (acima), LEDs com tipo próprio
(`sysfs_leds` é proibido ao sistema) e a marca do bootlog fora do `/dev` solto
(`/dev/hy300-bootlog/ready`).

**Para ligar o enforcing** (depois de um boot permissive limpo):
`adb shell 'dmesg | grep avc; logcat -b all -d | grep avc'` sem negações dos nossos domínios, e
então tirar `androidboot.selinux=permissive` do `BOARD_KERNEL_CMDLINE`.
