# Engenharia reversa

Notas por componente. Binários proprietários e saídas brutas de decompilação não são
versionados; aqui ficam análises, trechos relevantes e o mapa de propriedades/sysfs.

**Resumo para implementação: [`MAP.md`](MAP.md)** (função → mecanismo → comando shell).

| Diretório | Componente | Caminho no aparelho |
|---|---|---|
| `txcz-settings/` | app de configurações TXCZ (`com.android.tv.settings`) | `/system/app/TxczSetting` |
| `services-jar/` | framework modificado (ganchos `txcz`) | `/system/framework/services.jar` |
| `libfocus/` | motor de foco (`motor_cc`) e lib de autofoco | `/sys/class/motor_cc`, `/system/lib{,64}/libfocusvahysd.so` |
| `display/` | keystone no SurfaceFlinger, HWC, overscan, PQ | `/system/bin/surfaceflinger`, `/system/lib/librkgfx_dc.so`, `/vendor/lib/libpq.so` |
| `telemetria/` | servidores, OTA Adups, instalação remota (`txczbox`) | launcher, `/system/app/txczbox`, `/product/app/FotaUpdate` |
| `rkcamera3/` | visualizador HDMI-in + áudio | `/system/app/rkCamera3` |

## Propriedades conhecidas (`getprop | grep txcz`)

```
persist.sys.hwrotation.txcz      persist.sys.isflip.{h,v}.txcz
persist.sys.mirror_{x,y}.txcz    persist.sys.txcz.dscale
persist.txcz.trapezoid.{mode,offsetx,offsety,zoom}
persist.txcz.tt.{enable,angle,preAngle,bdstate,display}   # auto-keystone (sensor)
persist.txcz.boot.{enable,app}   persist.txcz.source
persist.txcz.screen.{width,height,ratio}   persist.txcz.color.model
persist.vendor.txcz.pq.config.path=/vendor/etc/pq_play.json
```
