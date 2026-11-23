# HY300 (variante Rockchip RK3566) — engenharia reversa e customização

Projetor chinês "HY300" vendido com a ROM **TXCZ LightOS** (Android 12). Diferente do HY300
mais comum (Allwinner H713), esta variante usa **Rockchip RK3566**, então os projetos da
comunidade para o H713 **não se aplicam**.

Objetivos:

- [x] Root / acesso total (build `userdebug`, bootloader desbloqueado)
- [x] Backup completo das partições
- [x] Debloat reversível
- [x] Launcher alternativo (Projectivy via Aurora)
- [x] Declarar `android.software.leanback` (apps de TV) — ver `docs/launcher-leanback.md`
- [x] Splash do U-Boot customizável (`docs/splash.md`)
- [x] Animação de boot com log ao vivo (`android/bootlog`)
  - [x] versão nativa C++ (libgui + FreeType), no LineageOS; desenhando no aparelho desde o boot 1
- [x] Engenharia reversa do app de configurações da TXCZ (keystone, espelhamento, foco, fontes): `reverse-engineering/MAP.md`
- [x] App de configuração próprio integrado às Configurações do Android (`android/hy300-settings`)
- [x] Kernel 6.1 ([kernel-hy300-rk3566](https://github.com/mateusseiboth/kernel-hy300-rk3566)): branch
  `hy300-6.1` (BSP Rockchip, usada pelo Alpine) e `hy300-ack-6.1` (ACK android14-6.1, usada pelo
  LineageOS). Painel por SPI, DT embutido, Wi-Fi AIC8800, DVFS até 1,8 GHz. Ver `docs/kernel-6.1.md`
- [x] Ambiente de recuperação e instalação Alpine Linux na partição `boot`
  ([hy300-alpine](https://github.com/mateusseiboth/hy300-alpine)): SSH pelo Wi-Fi, ponto de acesso
  de reserva, grava qualquer partição, fica no Alpine depois de um panic
- [ ] LineageOS 24.0 TV (Android 17), árvore em
  [android_device_hy300_rk3566](https://github.com/mateusseiboth/android_device_hy300_rk3566):
  - [x] visto no aparelho: kernel ACK, display, animação de boot, GPU Panfrost, driver Wi-Fi com scan
  - [ ] boot completo, Wi-Fi do Android e adb pela rede (em teste), áudio
  - [ ] Bluetooth, sensores, Widevine, vídeo 10 bits, sepolicy, keystone no SurfaceFlinger
  - estado detalhado e roteiro em `docs/lineageos.md`
- [ ] Entrada HDMI com áudio (RK628) no LineageOS (`docs/hdmi-audio.md`)
- [ ] (futuro) Linux mainline

## Identificação

| Item | Valor |
|---|---|
| SoC | Rockchip RK3566 (4× Cortex-A55), Mali-G52 |
| RAM / eMMC | 2 GB / 16 GB (`mmcblk2`) |
| Placa | `rk3566_sgo`, modelo TXCZ `rk3566_y356tx`, `ro.txcz.devicename=HY300` |
| ROM | `TXCZ_LightOS_T6P`, Android 12 (SDK 32), build `eng.txcz.20240118.181251` |
| Tipo de build | `userdebug` / `release-keys` → `adb root` funciona |
| Bootloader | desbloqueado (`verifiedbootstate=orange`, `flash.locked=0`) |
| Kernel | 4.19.232 (arm64) |
| Userspace | **somente 32 bits** (`armeabi-v7a`; `abilist64` vazio) |
| Treble | sim, VNDK 32, partições dinâmicas (`super`) |
| Tela | painel interno **LVDS** 1024×600 (a ROM de fábrica renderiza em 1280×720 e reduz) |
| HDMI | **entrada** via bridge **RK628** → MIPI-CSI (sem saída HDMI) |
| Wi-Fi/BT | AIC (aicsemi, driver `AICWFDBG`) |

Detalhes em [`docs/hardware.md`](docs/hardware.md).

## Estrutura

```
docs/               anotações técnicas (hardware, kernel 6.1, LineageOS, HANDOFF, áudio HDMI, debloat…)
scripts/            scripts adb da ROM de fábrica (backup, debloat, restauração, slot de teste)
dumps/              dumps pequenos e não sensíveis (ex.: EDID do RK628)
reverse-engineering/ notas de RE por componente da TXCZ/Rockchip
kernel/             config do kernel de fábrica, build do 6.1 (marco 1 e prebuilt do LineageOS), initramfs de teste
android/            app de configurações, animação de boot (Java e C++), arquivos do build do LineageOS
tools/              mkboot, resource, sequência do painel, checagens de DT e de kconfig, prebuilt do LineageOS
tests/              testes das ferramentas e scripts (python3 -m unittest discover -s tests)
```

> Imagens de partição, APKs e bibliotecas proprietárias **não** são versionados
> (ver `.gitignore`).

## Como funciona este repositório

Nada proprietário é distribuído aqui. Tudo é **reproduzível a partir do seu próprio aparelho**:

1. **Extraia** — scripts em `scripts/` puxam os binários/partições do *seu* projetor
   (`backup-partitions.sh`, e futuros `extract-*.sh`).
2. **Aplique** — modificações são distribuídas como **patches** (smali/diff, overlays, XMLs,
   props) + script que os aplica sobre o que você extraiu.
3. **Reverta** — toda modificação tem caminho de volta documentado (backup, `restore-*.sh`,
   `pm install-existing`, `adb enable-verity`, etc.).

Cada mudança documenta: **o que faz**, **pré-requisitos** (versão exata da ROM — ver
`ro.build.fingerprint`), **como aplicar**, **como reverter** e **risco**.

ROM de referência:
`rockchip/rk3566_sgo/rk3566_sgo:12/SQ3A.220705.003.A1/eng.txcz.20240118.181251:userdebug/release-keys`

## ⚠️ Aviso

**Use por sua conta e risco.** Mexer em partições e no sistema pode deixar o aparelho sem
boot. Faça o backup completo antes de qualquer coisa. Aparelhos vendidos como "HY300"
usam chips diferentes (Allwinner H713, RK3326, RK3566…): **confirme que o seu é RK3566 com
a mesma ROM** antes de aplicar qualquer patch. Em último caso, o RK3566 pode ser regravado
pelo modo MaskROM com o backup feito aqui.
