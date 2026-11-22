# Mapa função → mecanismo → comando (HY300 / TXCZ LightOS)

Resumo para implementar o app novo. Detalhes em `txcz-settings/`, `services-jar/`, `libfocus/`, `display/`, `telemetria/`.
Tela lógica: **1280×720** (painel físico 1024×600). Os comandos de keystone, foco, fonte e BCSH foram executados pelo app `android/hy300-settings`
(como app comum, porque o SELinux está em permissive); os demais não. Detalhes e estado de cada um no README do app.

## Display / projeção

| Função (UI TXCZ) | Mecanismo | Consumidor | Comando shell equivalente |
|---|---|---|---|
| Keystone 4 cantos | `persist.sys.keystone.{lt,lb,rt,rb}="x,y"` (px, x→dir., y→cima, deslocamento do canto) + `persist.sys.keystone.update=1` | SurfaceFlinger + `/system/lib/librkgfx_dc.so` (malha GPU) | `setprop persist.sys.keystone.lt 20,-11; setprop persist.sys.keystone.update 1` |
| Reset do keystone | todos `0,0` + update (ou `persist.sys.keystone.reset`) | SF | `for c in lt lb rt rb; do setprop persist.sys.keystone.$c 0,0; done; setprop persist.sys.keystone.update 1` |
| Desligar keystone | `persist.sys.keystone.disable` (valor exato não confirmado; provavelmente `1`) | SF | `setprop persist.sys.keystone.disable 1` |
| Trapézio V/H (`trapezoid.mode=1`) | passos de 5 px movendo 2 cantos 5 px em x **e** 5 px em y; `offsetx` = vertical (↑ +5, positivo estreita o topo), `offsety` = horizontal (→ +5, positivo estreita a direita), limite ±1/3 da largura/altura com zoom (bytecode do `ProjectorVerticalActivity`) | SF (via cantos) | ex.: estreitar o topo em 20 (mesa frontal): `lt 20,-20`, `rt -20,-20` |
| Zoom (20–100 %) | cantos andam para dentro `minX=(W-W·z/100)/2`, `minY=(H-H·z/100)/2`; contador em `persist.txcz.trapezoid.zoom` | SF | zoom 90: `lt 64,-36 lb 64,36 rt -64,-36 rb -64,36` + update |
| Proporção 16:9 / 4:3 | `persist.txcz.screen.{width,height,ratio}` (área lógica, 4:3 → 960×720) e recalcula os cantos | SF (via cantos) | 4:3: `lt 160,0 lb 160,0 rt -160,0 rb -160,0` + update |
| Mesa frontal (modo 0) | cantos base `reset()` | SF | todos `0,0` + update |
| Mesa traseira / espelho H (modo 1) | `x_mirror()`: `lt=W,0 lb=W,0 rt=-W,0 rb=-W,0` | SF | `lt 1280,0 lb 1280,0 rt -1280,0 rb -1280,0` + update |
| Teto frontal / 180° (modo 2) | `xy_mirror()` | SF | `lt 1280,-720 lb 1280,720 rt -1280,-720 rb -1280,720` + update |
| Teto traseira / espelho V (modo 3) | `y_mirror()` | SF | `lt 0,-720 lb 0,720 rt 0,-720 rb 0,720` + update |
| (estado do modo) | `persist.txcz.install.model=0..3` + `*.init.xy` + vendor storage id 50 (`'0'..'3'`) | id 50: **U-Boot**, gira o logo de boot 180° com `'2'`/`'3'` | `setprop persist.txcz.install.model 2` |
| Keystone automático (inclinação) | acelerômetro → pitch − `persist.txcz.tt.angle` → `v=⌊|a|·4,2⌋`, `vH=⌊720·v·2/1280⌋` → cantos de cima ou de baixo; liga/desliga `persist.txcz.tt.enable` (o `OnLineOrOffLineReceiver` sobe o `TaitouService` no boot com 1); calibração `tt.angle`/`tt.bdstate=1`; último ângulo `tt.preAngle` | app (TaitouService) → SF | a=10°: base + `lt +42,-47`, `rt -42,-47` + update |
| API de keystone do app TXCZ | `BridgeService` `settings2txcz://?action=1..4` | TxczSetting | `am startservice -a com.android.settings.action.bridge -n com.android.tv.settings/com.shzhtxcz.txbox.service.BridgeService -d 'settings2txcz://k?action=1&mode=2'` |
| Rotação/flip de display (`persist.sys.hwrotation(.txcz)`, `isflip.*`, `mirror_*.txcz`) | **não usado**: só o build.prop e o app TXCZ (leitura) | ninguém | — |
| Escala de tela (overscan) | `persist.sys.txcz.dscale` (<100 → overscan nos 4 lados, só no boot) | `services.jar` `RkDisplayModes.init` → `drm_device_management` | `setprop persist.sys.txcz.dscale 90` (+reboot) |
| Overscan em runtime | `RkDisplayOutputManager.setOverScan(disp,dir,val)` / `persist.vendor.overscan.main="overscan l,t,r,b"` | HWC RK | `setprop persist.vendor.overscan.main "overscan 95,95,95,95"` |

## Foco

| Função | Mecanismo | Consumidor | Comando |
|---|---|---|---|
| Foco manual + | escrever `user_cw` em `/sys/class/motor_cc/motor_cc/motor` (1 passo; repetir a cada 60 ms) | driver de kernel `usb-cam-gpio` | `printf user_cw > /sys/class/motor_cc/motor_cc/motor` |
| Foco manual − | `user_ccw` | idem | `printf user_ccw > /sys/class/motor_cc/motor_cc/motor` |
| Parar | `aastop` (sem `\n`; o kernel usa strcmp — usar `printf`) | idem | `printf aastop > /sys/class/motor_cc/motor_cc/motor` |
| Fim de curso | ler `/sys/class/motor_cc/motor_cc/hd_camera_on` (`1` = limite) | — | `cat /sys/class/motor_cc/motor_cc/hd_camera_on` |
| Foco pelo controle IR | tratado no kernel (`rk pwm remotectl` usa `motor_status`) | kernel | — |
| Teclas F7/F8 (framework) | `MaDaDialog` escreve em `.../motoraa` (inexistente) → **não funciona** | — | — |
| Autofoco (câmera) | app `com.hysd.txczscreen` + `libfocusvahysd.so` → **app ausente, nada carrega a lib** | — | — |
| Switch "autofoco" do TXCZ | `persist.txcz.focus.auto/tixing/txmode` + `Sensorservice` (dispara app ausente) | — | — |

## Fonte / boot

| Função | Mecanismo | Consumidor | Comando |
|---|---|---|---|
| Abrir HDMI | activity `com.android.rockchip.camera2/.RockchipCamera2` (`rkCamera3.apk`); tecla F6 = keycode 136 | framework (`PhoneWindowManager`) | `am start -n com.android.rockchip.camera2/.RockchipCamera2` ou `input keyevent 136` |
| Boot direto no HDMI | `persist.txcz.source=1` + `persist.txcz.boot.app=com.android.rockchip.camera2,com.android.rockchip.camera2.RockchipCamera2` (abre 10 s após a Home) | `services.jar` `RootWindowContainer` | `setprop persist.txcz.boot.app com.android.rockchip.camera2,com.android.rockchip.camera2.RockchipCamera2` |
| Boot direto em app | `persist.txcz.source=2` + `persist.txcz.boot.app=<pkg>` (abre na hora) ou `<pkg>,<Activity>` (+10 s) | idem | `setprop persist.txcz.boot.app org.exemplo.app` |
| Boot na Home | `persist.txcz.source=0`, `persist.txcz.boot.app=""` | idem | `setprop persist.txcz.boot.app ""` |
| `persist.txcz.boot.enable` | nenhum leitor encontrado | — | — |
| Abrir config. TXCZ | tecla F12 (142) | framework | `input keyevent 142` |

## Imagem / PQ

| Função | Mecanismo | Consumidor | Comando |
|---|---|---|---|
| Modo de cor (TXCZ) | `persist.txcz.color.model=0/1/2` + `persist.vendor.pq.path=/vendor/etc/pq_play{,_yanli,_rouhe}.json` | **nenhum** (prop não é lida no ROM; yanli ≡ rouhe) | — |
| PQ real (RK) | `persist.vendor.rkpq.config.path` (init força `/vendor/etc/pq_ui.json` a cada boot), `persist.vendor.tvinput.rkpq.mode` | `vendor/lib/libpq.so` (caminho tv_input/HDMI) | `setprop persist.vendor.rkpq.config.path /vendor/etc/pq_play_yanli.json` (efeito/recarga não confirmados) |
| Brilho/contraste/saturação/matiz | `persist.vendor.{brightness,contrast,saturation,hue}.main` (0–100, padrão 50) + incrementar `vendor.display.timeline` | HWC RK (`UpdateBCSH`): o conector LVDS tem as propriedades BCSH e o HWC as envia (log com `vendor.hwc.log=511`); efeito visual a confirmar | `setprop persist.vendor.contrast.main 55; setprop vendor.display.timeline $(( $(getprop vendor.display.timeline)+1 ))` |

## Outros

| Função | Mecanismo | Comando |
|---|---|---|
| Caixa de som BT (A2DP sink) | `persist.bluetooth.rka2dpsink=true`, `persist.txcz.sound.enable=1`; o `SoundBoxService` desliga a ventoinha (`Fan_h`) e a fonte de luz (`Lcd_power`) só nesse modo. No HY300 existem `Fan_h`, `Lcd_power`, `green` e `red` (gpio-leds); `Fan`/`LED_CRL` são de outras placas | `setprop persist.bluetooth.rka2dpsink true` (+ reiniciar BT) |
| LEDs indicadores | `/sys/class/leds/{green,red}/brightness` (0644 system; o `PhoneWindowManager` pisca o verde nos apps de teste de fábrica) | `echo 0 > /sys/class/leds/green/brightness` |
| Idioma | `ActivityManager.updateConfiguration(locale)` | — (só via API `updateConfiguration`) |
| Data/hora | `AlarmManager.setTime/setTimeZone`, `Settings.Global auto_time`, `Settings.System time_12_24` | `settings put global auto_time 1`; `setprop persist.sys.timezone America/Sao_Paulo` |
| Espelhamento de tela ("Tela Elenco") | só abre apps de terceiros (`com.hpplay.happyplay.aw`, `com.airplay.mirror`, `com.ecloud.eshare.server`) | `am start -n ...` |
| Teclas F1–F4 | broadcast `com.shzhtxcz.exkey` (keyCode) → `com.shzhtxcz.txbox` (removido) | `am broadcast -a com.shzhtxcz.exkey --ei keyCode 131` |
| Destravar menus "limitados" | sequência `1 8 6 5 0` → `persist.sys.prison_break=1` | `setprop persist.sys.prison_break 1` |
| Vendor storage | JNI `libvendor_store.so` (`readVendorStorage/writeVendorStorage(id, str)`); id 50 = modo de instalação, lido pelo U-Boot (orientação do logo) | `am broadcast -a intent.action.txcz.vs --ei wid 50 --es value 2` (**brecha**: qualquer app consegue; só com o TxczSetting ativo) |

## Segurança (resumo)

- `com.shzhtxcz.txbox` (system, já removido): registro e heartbeat em `http://shzhtxcz.com/videoadmin`, `47.113.90.237:8081`,
  **instalação/desinstalação silenciosa** de APKs vindos do servidor (incluindo Lanzou), envio de logcat/dmesg, inventário de apps, TLS sem validação.
- Launcher: layout da Home de `http://shzhtxcz.com` (HTTP) com serial e MACs nos cabeçalhos.
- `com.txcz.update`: Adups FOTA (`fota5p.adups.com/.cn`, `fruet.adups.com`) envia androidId, MAC e fingerprint; instala OTA via recovery.
- TxczSetting: `VsReceiver`/`MyService` exportados permitem escrita arbitrária no vendor storage; `BridgeService` exportado.

## Em aberto

- ~~Quem lê o vendor storage id 50~~: o U-Boot (`rockchip_display`, `vendor_storage_read(50, buf, 1)`; `'2'`/`'3'` → logo girado 180°). Kernel, serviços nativos, SF, HWC e apps de `/system` não leem. Falta conferir o id usado pela `libexplay.so` do `com.android.toofifi` (`/odm`).
- ~~Parser de `motor_store`~~: ver `libfocus/README.md` (strcmp, `aastop`, -EINVAL esperado). Falta o papel real de `hd_camera_on` e o sentido de `user_cw` na lente.
- Valor e efeito de `persist.sys.keystone.{disable,reset,mirror_y}` e se o SF zera `update` sozinho.
- Se o `libpq` relê `persist.vendor.rkpq.config.path` em runtime e se o PQ afeta a UI ou só o HDMI-in.
- `com.android.toofifi` (`/odm/bundled_persist-app`): app de **espelhamento** (AirPlay/Miracast/DLNA — mphotool, waxrain AirPin, ijkplayer), processo persistente uid system; detalhes de rede não analisados (ver `docs/debloat.md`).
- Leitor de `persist.txcz.boot.enable`: nenhum encontrado.
