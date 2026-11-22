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
  - [ ] versão nativa C++ (log desde ~6 s, boot mais rápido) — ver `android/bootlog/README.md`
- [ ] Engenharia reversa do app de configurações da TXCZ (keystone, espelhamento, foco, fontes)
- [ ] App de configuração próprio integrado às Configurações do Android
- [ ] Áudio da entrada HDMI (RK628)
- [ ] Avaliar Android mais novo (GSI `arm32_binder64` / LineageOS)
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
| Tela | painel interno **LVDS** 1280×720 (`card0-LVDS-1`) |
| HDMI | **entrada** via bridge **RK628** → MIPI-CSI (sem saída HDMI) |
| Wi-Fi/BT | AIC (aicsemi, driver `AICWFDBG`) |

Detalhes em [`docs/hardware.md`](docs/hardware.md).

## Estrutura

```
docs/               anotações técnicas (hardware, áudio HDMI, debloat, ROM…)
scripts/            scripts adb (backup, debloat, restauração)
dumps/              dumps pequenos e não sensíveis (ex.: EDID do RK628)
reverse-engineering/ notas de RE por componente da TXCZ/Rockchip
kernel/             patches / DTS (futuro)
android/            app de configurações próprio, overlays, GSI (futuro)
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
