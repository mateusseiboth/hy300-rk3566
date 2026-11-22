# Hardware e layout do sistema

## Partições (`/dev/block/by-name`, eMMC `mmcblk2`)

| Partição | Tamanho | Observação |
|---|---|---|
| uboot | 4 MB | |
| trust | 4 MB | |
| misc | 4 MB | |
| dtbo | 4 MB | |
| vbmeta | 1 MB | |
| boot | 40 MB | kernel + ramdisk (+ DTB em `resource`?) |
| recovery | 108 MB | |
| security | 4 MB | |
| baseparameter | 1 MB | parâmetros de display Rockchip |
| backup | 372 MB | |
| cust | 64 MB | |
| metadata | 16 MB | |
| super | ~3,04 GB | dinâmica: system, system_ext, vendor, product, odm… |
| cache | 384 MB | |
| userdata | resto | |

Backup: ver `scripts/backup-partitions.sh`.

## Display

- Painel interno via **LVDS** (`/sys/class/drm/card0-LVDS-1`), 1280×720, densidade 160.
- `ro.rk.hdmi_enable=false` — não existe saída HDMI.
- Keystone/trapézio, espelhamento e rotação controlados por propriedades `persist.txcz.*`
  (ex.: `persist.txcz.trapezoid.{mode,offsetx,offsety,zoom}`, `persist.sys.mirror_{x,y}.txcz`,
  `persist.sys.hwrotation.txcz`) — mecanismo ainda em investigação
  (`/system/framework/services.jar` foi modificado pela TXCZ e referencia `txcz`).

## Entrada HDMI (RK628)

- Bridge **RK628** em I²C `1-0050`, driver `rk628-csi-v4l2`, saída MIPI-CSI → `rkisp`.
- Visualizada pelo app `com.android.rockchip.camera2` (`/system/app/rkCamera3`),
  que é também o app de boot (`persist.txcz.boot.app`).
- Sysfs: `/sys/class/hdmirx/rk628/{audio_present,audio_rate,video_fmt,hdcp_key}`.
- Controles V4L2 no subdev: `audio_sampling_rate`, `audio_present`, `power_present`, DV timings.
- EDID (`dumps/rk628-edid.*`): bloco CEA com *basic audio*, LPCM 2 ch 32/44,1/48 kHz 16 bit,
  VSDB HDMI → a fonte **deve** enviar áudio.

## Áudio

| Card ALSA | Nome | I²S | Uso |
|---|---|---|---|
| 0 | `rockchip,rockchip-i2s-sound` (dummy-codec) | `fe410000` | alto-falante |
| 1 | `rockchip,hdmiin` (hdmi-codec) | `fe430000` | captura do áudio do RK628 |

Ver [`hdmi-audio.md`](hdmi-audio.md).

## Outros

- Classe sysfs `motor_cc` → motor do foco.
- Biblioteca de autofoco `libfocusvahysd.so` em `/system/lib{,64}` (não no vendor).
- `/odm/etc/build.prop` contém configurações TXCZ.
