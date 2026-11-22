# Pipeline de display: keystone (SurfaceFlinger), HWC, overscan e PQ

## Keystone = SurfaceFlinger + `librkgfx_dc.so` (Rockchip "keystone v5.1")

- `/system/bin/surfaceflinger` (binário estático, com patch RK) faz `dlopen("/system/lib/librkgfx_dc.so")` (só existe a
  versão 32 bits). Funções: `RKGFX_DC_init/configure/prepare/process/updatemesh/calculateMVP/getMeshBuffer/draw_mask/deinit`.
- A composição final passa por uma malha GLES (deformação dos 4 cantos + máscara preta fora do quadrilátero).
  Por isso o keystone funciona igual na Home, no HDMI (camera2) e em qualquer app, e custa uma passada de GPU
  (o HWC deixa de fazer overlay da camada final).
- Props lidas pelo SF (`getKeyStonePropVal`):

| Prop | Valor no aparelho | Papel |
|---|---|---|
| `persist.sys.keystone.lt` / `lb` / `rt` / `rb` | `"x,y"` | deslocamento do canto em px do painel (x→direita, y→cima) |
| `persist.sys.keystone.update` | 0 | gatilho: escrever `1` faz o SF reler os cantos |
| `persist.sys.keystone.reset` | (vazia) | zera os 4 pontos (`reset all point (0,0)`) |
| `persist.sys.keystone.disable` | (vazia) | desliga o keystone (`keystone is disabled !`) |
| `persist.sys.keystone.display.id` | 0 | display onde aplicar |
| `persist.sys.keystone.mirror_x` / `mirror_y` | 0 / (vazia) | espelhamento nativo da malha |
| `persist.sys.keystone.log` | — | log |
| `persist.sys.keystone.version` | `v5.1` (escrita pela lib) | — |
| `persist.sys.keystone.boot_effect` | 1 (build.prop) | provavelmente aplica o keystone também na animação de boot |

- O `init.rk356x.rc` (vendor) faz `setprop persist.sys.keystone.update 1` em `on boot`.
- **Nenhuma** prop `*.txcz` de rotação ou flip é lida pelo SF, HWC ou framework (`persist.sys.hwrotation(.txcz)`,
  `isflip.*`, `mirror_*.txcz` só aparecem no `build.prop` e no TxczSetting). Rotação de 180° e espelhamento são feitos
  pelos cantos do keystone (ver `../txcz-settings/README.md` §1).

Comando mínimo:
```sh
setprop persist.sys.keystone.lt 0,0; setprop persist.sys.keystone.lb 0,0
setprop persist.sys.keystone.rt 0,0; setprop persist.sys.keystone.rb 0,0
setprop persist.sys.keystone.update 1
```

## HWC (`/vendor/lib/hw/hwcomposer.rk30board.so`)

Não lê nenhuma prop `txcz` ou `keystone`. Props relevantes (RK padrão): `persist.vendor.overscan.{main,aux}`
(`"overscan l,t,r,b"`), `persist.vendor.resolution.*`, `persist.vendor.{brightness,contrast,saturation,hue,color}.%s`,
`persist.vendor.tvinput.rkpq.mode`, `persist.vendor.framebuffer.*`, `vendor.hwc.*`.

## Overscan / escala

- `persist.sys.txcz.dscale` (framework, só no boot) → `RkDisplayModes.nativeSetScreenScale(0, dir, %)`
  (ver `../services-jar/README.md` §2).
- Em runtime: `RkDisplayOutputManager.setOverScan(display, dir, valor)` (tela "Escala de tela" do TvSettings RK,
  `com.android.tv.set/.display.ScreenScaleActivity`).

## PQ (qualidade de imagem)

- `vendor/lib/libpq.so` (RK PQ: CSC, DCI, ACM, gamma 1024 pontos, sharp) lê **`persist.vendor.rkpq.config.path`**
  (fallback `/vendor/etc/pq_config.json`, `/data/pq_config.json`). O `init.rk356x.rc` força
  `persist.vendor.rkpq.config.path=/vendor/etc/pq_ui.json` e `persist.vendor.tvinput.rkpq.mode=1` a cada boot.
  Também: `persist.vendor.tvinput.rkpq.zme.*`, `vendor.tvinput.pq.version` (Pq-1.3.14), `vendor.rkpq.scene.timeline`.
- `librkswpq.so` (PQ por software, SR/3D-LUT): `persist.vendor.rkpq.{3dlut.enable,acm.*}`, `persist.sys.rk.auth.{ip,port}`
  (licença RK por rede, não investigado a fundo).
- **`persist.vendor.pq.path`** (escrita pelo modo de cor do TxczSetting) e **`persist.vendor.txcz.pq.config.path`**
  (build.prop) **não são lidas por nenhum binário** do ROM (busca na `super.img` inteira). Portanto o modo de cor do app
  TXCZ é inócuo neste ROM.
- Arquivos em `/vendor/etc`: `pq_play.json` ≡ `pq_ui.json` (normal) e `pq_play_yanli.json` ≡ `pq_play_rouhe.json` (vívido;
  os dois "modos" são o mesmo arquivo). Estrutura: `pq_tuning_param.{csc,dci,acm,gamma,sharp}`:
  - `csc`: `cscEnable, cscMode=HIGH_QUALITY_MODE, cscBrightness 88, cscHue 253, cscContrast 345, cscSaturation 385, cscR/G/BGain 256`
  - `dci`: curvas de contraste dinâmico (33 coef. × 3 faixas)
  - `acm`: tabelas de cor por matiz (65 pontos) + ganhos (`lumGain/hueGain/satGain`)
  - `gamma`: `gammaTab_{R,G,B}` 1024 entradas
  - `sharp`: `sharpPeakingGain 701` + parâmetros de *shoot/coring/gain/limit*
- O PQ parece se aplicar ao caminho de vídeo/HDMI-in (tv_input/camera); não está claro se afeta a UI.
  Um app novo que quiser "modos de cor" deveria trocar `persist.vendor.rkpq.config.path` (e verificar se o `libpq`
  relê o arquivo sem reboot, ainda em aberto) ou usar `persist.vendor.{brightness,contrast,saturation,hue}.main` do HWC.

## Outros apps com lógica de projetor

- `com.android.tv.set` (`/system_ext/priv-app/TvSettings`): TvSettings RK. Só usa `ro.txcz.buildmodel` e
  `ro.txcz.devicename` na tela Sobre; overscan pela tela "Escala de tela"; `system/InputsFragment` (entradas TIF).
  Não tem keystone.
- `com.shzhtxcz.txbox.launcher` (`/system/app/txcz_launcher`): Home TXCZ. Atalho "Sinal" abre
  `com.android.rockchip.camera2` (HDMI). Sem keystone. Rede: ver `../telemetria/README.md`.
