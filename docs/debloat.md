# Debloat

Feito com `pm uninstall -k --user 0` — **nada é apagado de `/system`**; qualquer pacote volta com
`adb shell pm install-existing <pacote>` (ou `scripts/restore-debloat.sh`).

Lista aplicada: [`scripts/debloat-packages.txt`](../scripts/debloat-packages.txt).

## Mantidos de propósito (por enquanto)

| Pacote | Motivo |
|---|---|
| `com.android.tv.settings` (TxczSetting) | app de config da TXCZ — keystone/projeção até existir substituto |
| `com.android.tv.set` (TvSettings) | configurações base |
| `com.android.rockchip.camera2` | visualizador da entrada HDMI |
| `com.android.toofifi` | espelhamento (AirPlay/Miracast/DLNA) — persistente, candidato a remoção |
| `com.shzhtxcz.txbox.launcher` | launcher original (fallback) |
| `com.actions.hidaudio` | áudio do controle remoto BT (voz) |
| `com.rockchips.mediacenter` | player de mídia USB |

## Observações de segurança

Todos os apps TXCZ rodam com `sharedUserId=android.uid.system` (uid 1000), ou seja, têm
`INSTALL_PACKAGES`, `DELETE_PACKAGES`, `MASTER_CLEAR`, `REBOOT`, `READ_LOGS`,
`WRITE_SECURE_SETTINGS`, localização, câmera e microfone. Na verificação inicial só havia
conexões ativas para Google (GMS); nada para servidores chineses.

`com.android.toofifi` = espelhamento de tela (componentes mphotool / waxrain AirPin / ijkplayer).

## Ajustes de desempenho aplicados

```
settings put global window_animation_scale 0.5
settings put global transition_animation_scale 0.5
settings put global animator_duration_scale 0.5
```

## Removidos do /system e /product (overlay)

`scripts/remove-txcz-system-apps.sh` apaga de vez (não só `--user 0`):

| Pacote | Caminho | Motivo |
|---|---|---|
| `com.shzhtxcz.txbox` | `/system/app/txczbox` + update em `/data` | backdoor: instala/desinstala APKs do servidor, envia logcat/dmesg |
| `com.shzhtxcz.txbox.launcher` | `/system/app/txcz_launcher` | envia serial/MACs em HTTP |
| `com.txcz.update` | `/product/app/FotaUpdate` | Adups FOTA (androidId/MAC) |

Detalhes em `reverse-engineering/telemetria/`. Reverter: restaurar a `super` do backup.

## Teste: renderizar em 1024×600 (resolução real do painel) — não funcionou

`persist.vendor.framebuffer.main=1024x600@60` foi ignorado pelo HWC (continuou 1280×720); com o
keystone escalado ×0,8 a imagem só encolheu. Revertido. Para renderização nativa o HWC precisa
expor o modo 1024×600 — investigar (`persist.vendor.resolution.*`, `GetFramebufferInfo`).
