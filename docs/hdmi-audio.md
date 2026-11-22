# Áudio da entrada HDMI não funciona

**Status:** diagnóstico parcial — falta reproduzir com uma fonte HDMI conectada.

## Cadeia esperada

```
fonte HDMI → RK628 → I²S (fe430000) → ALSA card1 "rockchiphdmiin" (captura)
          → loop (app/HAL) → ALSA card0 (alto-falante)
```

## O que o HAL faz (`/vendor/lib/hw/audio.primary.rk30board.so`)

Strings relevantes: `open HDMIIN %d`, `rockchiphdmiin`, `rk628`,
`/sys/class/hdmirx/%s/%s`, `audio_present`, `audio_rate`, `vendor.hdmiin.audiorate`,
`hdmiin audio is no present, don't open hdmiin sound`.

→ o HAL só abre a captura se `/sys/class/hdmirx/rk628/audio_present == 1`.

## O que o app de HDMI-in faz (`com.android.rockchip.camera2`)

Strings do dex: `HdmiInUtils`, `AudioStream` (AudioRecord→AudioTrack), `EnableHDMIInAudio`,
`HDMIin_enable=true/false` (via `AudioManager.setParameters`), `media.audio.hdmiin`,
`set media.audio.hdmiin 1`, `startHdmiAudioService`,
`HDMIIN_AUDIO_PACKAGE_NAME = com.rockchip.rkhdmiinaudio`,
`HDMIIN_AUDIO_CLS_NAME = com.rockchip.rkhdmiinaudio.HdmiInAudioService`.

## Achado principal

O pacote **`com.rockchip.rkhdmiinaudio` não existe na ROM** (nem em `pm list packages -u`,
nem em nenhum lugar do sistema de arquivos). Se o app escolhe o caminho do serviço externo,
o áudio nunca é iniciado.

## Próximos passos

1. Conectar fonte HDMI, abrir a entrada e acompanhar:
   `adb logcat | grep -iE "hdmiin|HdmiIn|AudioStream|rk628|audio_hw"` e
   `cat /sys/class/hdmirx/rk628/audio_present`.
2. Se `audio_present=1` e nada toca → implementar/obter `com.rockchip.rkhdmiinaudio`
   (SDK Rockchip) ou serviço equivalente.
3. Se `audio_present=0` com fonte tocando → problema no driver RK628 / I²S.
