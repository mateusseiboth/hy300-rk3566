# HY300 (variante Rockchip RK3566) — engenharia reversa e customização

Projetor chinês "HY300" vendido com a ROM **TXCZ LightOS** (Android 12). Diferente do HY300
mais comum (Allwinner H713), esta variante usa **Rockchip RK3566**, então os projetos da
comunidade para o H713 **não se aplicam**.

Objetivos:

- [x] Root / acesso total (build `userdebug`, bootloader desbloqueado)
- [x] Backup completo das partições
- [x] Debloat reversível
- [x] Launcher alternativo
- [ ] Liberar apps Android TV na Play Store (`android.software.leanback`)
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
