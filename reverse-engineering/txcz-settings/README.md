# TxczSetting (`com.android.tv.settings`) — engenharia reversa

- APK: `/system/app/TxczSetting/TxczSetting.apk` (tem `classes.dex`; `oat/arm/*.odex|vdex` são só AOT).
- `versionName 3.7.0115.rk11pro`, `versionCode 116`, `targetSdk 30`, **`sharedUserId=android.uid.system`**
  (roda como uid 1000 → pode `SystemProperties.set` em `persist.*`, escrever sysfs com dono `system`, etc.).
- Código Kotlin em `com.shzhtxcz.txbox.*`. Lib nativa: `lib/{arm64-v8a,armeabi-v7a}/libvendor_store.so`
  (JNI `com.vendor.store.VendorStorageJNI`).
- Decompilado com jadx 1.5.7. Saída bruta **não** versionada (proprietária); só trechos curtos aqui.

Arquivos de referência no app (classe → papel):

| Classe | Papel |
|---|---|
| `uitls/PropUtils` | lista de todas as props usadas (ver tabela abaixo); `getProp/setProp` = `android.os.SystemProperties` |
| `model/ProjectorModel` | estado do projetor; cada campo é um *delegate* que lê/escreve uma prop |
| `model/XYProjectorDelegate` | conversão canto lógico ⇄ prop `persist.sys.keystone.{lt,lb,rt,rb}` (rotação/flip) |
| `utils/ProjectUtils` | toda a lógica de keystone/zoom/modo de instalação/cor |
| `Limit` | passos e limites (zoom 20..100 passo 5; canto passo 10 px; trapézio passo 5 px; limite = 1/3 da tela) |
| `activity/ProjectorActivity` | menu "Configuração de projeção" |
| `activity/Projector4PointActivity` | correção de 4 cantos + zoom |
| `activity/ProjectorVerticalActivity` | correção trapezoidal (vertical/horizontal) |
| `activity/AutoTixingActivity` + `service/TaitouService` | keystone automático por acelerômetro (`persist.txcz.tt.*`) |
| `activity/AutoFocusActivity` + `service/Sensorservice` | "autofoco" (só dispara app externo `com.hysd.txczscreen`, ausente) |
| `activity/SystemSettingAppActivity` | "Outras configurações": fonte ao ligar (Home/HDMI/App) |
| `activity/StartAppActivity` | escolhe app para abrir no boot |
| `service/BridgeService` | API externa de keystone via Intent (`settings2txcz://`) |
| `receiver/*` | boot, USB, `intent.action.txcz.sensor`, `intent.action.txcz.vs` |
| `com.vendor.store.*` | leitura/escrita de *vendor storage* (JNI + serviço AIDL exportado) |

## Props usadas (de `PropUtils`)

| Prop | Uso no app | Valores |
|---|---|---|
| `persist.sys.keystone.lt/lb/rt/rb` | **escrita** – cantos do keystone | `"x,y"` px (ver §1) |
| `persist.sys.keystone.{lt,lb,rt,rb}.init.xy` | escrita – posição-base de cada canto (modo de instalação + zoom) | `"x,y"` |
| `persist.sys.keystone.update` | escrita – "aplicar" | `1` (ou `true` em placas HiSilicon) |
| `persist.txcz.install.model` | modo de instalação | 0 mesa-frontal, 1 mesa-traseira, 2 teto-frontal, 3 teto-traseira |
| `persist.txcz.trapezoid.mode` | tipo de correção ativa | 0 = 4 cantos, 1 = trapézio V/H |
| `persist.txcz.trapezoid.offsetx/offsety` | contador do trapézio (só UI/limites) | ±(zoomW/3), ±(zoomH/3), passo 5 |
| `persist.txcz.trapezoid.zoom` | zoom global | 20..100 (%), passo 5 |
| `persist.txcz.screen.width/height/ratio` | área lógica (ratio 0=16:9, 1=4:3) | px; padrão = tela real (1280x720) |
| `persist.sys.hwrotation.txcz`, `persist.sys.isflip.{h,v}.txcz`, `persist.sys.mirror_{x,y}.txcz` | **só leitura** (entram na matemática dos cantos) | 0/90/180/270; 0/1 |
| `persist.txcz.color.model` | modo de cor | 0 normal, 1 vívido, 2 suave |
| `persist.vendor.pq.path` | escrita pelo modo de cor | `/vendor/etc/pq_play{,_yanli,_rouhe}.json` |
| `persist.txcz.source` | fonte ao ligar | 0 Home, 1 HDMI, 2 App |
| `persist.txcz.boot.app` | app aberto no boot (consumido pelo framework) | `pkg` ou `pkg,Activity` |
| `persist.txcz.tt.enable/angle/preAngle/bdstate/txfx` | keystone automático | ver §2 |
| `persist.txcz.focus.auto/tixing/txmode` | chaves do "autofoco" | 0/1; modo 0..n |
| `persist.txcz.sensor.angle/shake` | escrito pelo Sensorservice | `"%.2f,%.2f"` |
| `persist.txcz.sound.enable`, `persist.bluetooth.rka2dpsink` | modo "caixa de som BT" | 0/1, true/false |
| `persist.txcz.hs352.project`, `persist.txcz.qz713.project` | seleciona backend HiSilicon/Allwinner (0 no HY300) | — |
| `persist.sys.txcz.disablebt`, `persist.sys.txcz.bt`, `persist.sys.txcz.sys2update`, `persist.sys.onlyset`, `persist.sys.limit`, `persist.sys.prison_break` | montagem do menu principal | 0/1 |

Escritas pelo app em runtime também: `persist.txcz.resolution=p<altura>` e
`persist.keystone.datapath=/cust` (Sensorservice).

---

## 1. Keystone manual (4 cantos, trapézio, zoom, proporção, modo de instalação)

**Tudo** (keystone, zoom, 4:3, espelhar/inverter para teto ou retroprojeção) é feito **só** com os
4 cantos do keystone em GPU do SurfaceFlinger (Rockchip `librkgfx_dc`, "keystone v5.1",
ver `../display/README.md`). O app nunca mexe em rotação de display, HWC ou kernel.

### Formato das props

`persist.sys.keystone.<canto>="x,y"`, com `<canto>` ∈ `lt` (sup. esq.), `lb` (inf. esq.),
`rt` (sup. dir.), `rb` (inf. dir.). Cada valor é o **deslocamento em pixels do painel** daquele canto a partir
da sua posição nativa, eixo **x para a direita, y para cima**. `0,0` em todos = imagem cheia, sem correção.
Depois de escrever os 4, o app grava `persist.sys.keystone.update=1`. O SF relê os cantos e recalcula a malha.
Provavelmente também volta `update` para 0 (inferido: no aparelho `update=0` em repouso; o `init.rk356x.rc` faz `setprop ... update 1` em
`on boot` para aplicar no boot).

Valores reais no aparelho (modo teto-frontal, zoom 70 %, trapézio aplicado):
```
persist.sys.keystone.lt=1068,-592   lt.init.xy=1088,-612
persist.sys.keystone.lb=1078,602    lb.init.xy=1088,612
persist.sys.keystone.rt=-1073,-597  rt.init.xy=-1088,-612
persist.sys.keystone.rb=-1088,612   rb.init.xy=-1088,612
```
Ou seja: o canto `lt` foi levado para perto do canto inferior direito → rotação de 180° feita pelo próprio keystone.

### Posição-base por modo de instalação (`ProjectUtils.changeInstallMode`)

Com tela `W×H` (1280×720), zoom `z` (%) e área lógica `Sw×Sh` (`screen.width/height`):
```
zw = Sw*z/100 ; zh = Sh*z/100
minX = (W - zw)/2 ; minY = (H - zh)/2            # getWidthPositionMin / getHeightPositionMin
maxX = minX + zw  ; maxY = minY + zh              # getWidthPositionMax / getHeightPositionMax
```
| `install.model` | função | lt | lb | rt | rb |
|---|---|---|---|---|---|
| 0 mesa frontal | `reset()` | `minX,-minY` | `minX,minY` | `-minX,-minY` | `-minX,minY` |
| 1 mesa traseira (espelho H) | `x_mirror()` | `maxX,-minY` | `maxX,minY` | `-maxX,-minY` | `-maxX,minY` |
| 2 teto frontal (180°) | `xy_mirror()` | `maxX,-maxY` | `maxX,maxY` | `-maxX,-maxY` | `-maxX,maxY` |
| 3 teto traseira (espelho V) | `y_mirror()` | `minX,-maxY` | `minX,maxY` | `-minX,-maxY` | `-minX,maxY` |

Esses valores são gravados em `*.init.xy` (base) e nos cantos, e depois vem `update=1`. Além disso o modo é
gravado no *vendor storage* id 50 (`VendorStorageJNI.writeVendorStorage(50, "<modo>")`). Quem lê esse id
(u-boot/logo de boot?) ficou em aberto.

Trocar o modo zera `trapezoid.offsetx/offsety`. Trocar a proporção (`doScreenRatio`) força o modo 0, zoom 100,
zera o trapézio e recalcula `screen.width/height` (4:3 em 1280x720 → 960x720).

### Ajustes relativos

- **4 cantos** (`Projector4PointActivity`): OK alterna o canto selecionado (nenhum → lt → lb → rt → rb). Setas
  movem o canto em ±10 px (`Limit.step`), limitados a uma janela de 1/3 da área (`Limit.changeLimitList`).
  Sem canto selecionado, as setas mudam o zoom. Duplo MENU (keycode 82 em <500 ms) = reset (zoom 100 + base).
- **Trapézio** (`ProjectorVerticalActivity`, `trapezoid.mode=1`): ↑/↓ mudam `offsetx` e ←/→ mudam `offsety`
  em passos de 5 px. Cada passo move **dois** cantos (de cima ou de baixo; da esquerda ou da direita)
  5 px para dentro em x e em y. O contador fica em `trapezoid.offsetx/offsety`; as props reais continuam sendo os cantos.
- **Zoom** (`ProjectUtils.zoomOffset`): `trapezoid.zoom` ± 5 (20..100). Os 4 cantos andam `Δ(minX)` e `Δ(minY)`
  para dentro. Ou seja, o zoom também é só keystone (não é overscan).
- O app converte entre coordenadas "lógicas" e as da prop aplicando `hwrotation.txcz`, `isflip.*.txcz` e
  `mirror_*.txcz` (todos 0 no HY300, então a conversão é a identidade) e somando/subtraindo `init.xy`.

### Reproduzir pela shell (NÃO executado)

```sh
# imagem cheia, mesa frontal
for c in lt lb rt rb; do setprop persist.sys.keystone.$c 0,0; done
setprop persist.sys.keystone.update 1

# teto frontal (180°), zoom 100
setprop persist.sys.keystone.lt 1280,-720; setprop persist.sys.keystone.lb 1280,720
setprop persist.sys.keystone.rt -1280,-720; setprop persist.sys.keystone.rb -1280,720
setprop persist.sys.keystone.update 1

# zoom 90 % (mesa frontal): minX=64, minY=36
setprop persist.sys.keystone.lt 64,-36;  setprop persist.sys.keystone.lb 64,36
setprop persist.sys.keystone.rt -64,-36; setprop persist.sys.keystone.rb -64,36
setprop persist.sys.keystone.update 1
```
Para o app TXCZ continuar coerente, atualize também `*.init.xy`, `persist.txcz.install.model` e
`persist.txcz.trapezoid.zoom`.

### API externa: `BridgeService` (exportado, sem permissão)

`startService` com action `com.android.settings.action.bridge` e data `settings2txcz://x?action=N&...`:

| action | parâmetros | efeito |
|---|---|---|
| 1 | `mode=0..3` | troca o modo de instalação (= menu) |
| 2 | `position=0..3&direction=UP/DOWN/LEFT/RIGHT&moveDistance=5` | move um canto (índice 0 lt, 1 lb, 2 rt, 3 rb) |
| 3 | `position=i&xy=x,y` | grava o canto i com valor absoluto (coordenadas lógicas) |
| 4 | `0=x,y&1=x,y&2=x,y&3=x,y` | `absChange`: offsets **relativos à base `init.xy`**, com limite (é o que o keystone automático usa) |

```sh
am startservice -a com.android.settings.action.bridge -n com.android.tv.settings/com.shzhtxcz.txbox.service.BridgeService \
  -d 'settings2txcz://k?action=4&0=20,-11&1=0,0&2=-20,-11&3=0,0'
```

## 2. Keystone automático (sensor) — `persist.txcz.tt.*`

UI: "Correção trapezoidal automática" (`AutoTixingActivity`). Liga/desliga `persist.txcz.tt.enable` e inicia ou para
`TaitouService`. No boot, `OnLineOrOffLineReceiver` religa o serviço se `tt.enable=1`.

`TaitouService`:
1. Registra o **acelerômetro** (`Sensor.TYPE_ACCELEROMETER`, `SENSOR_DELAY_NORMAL`) e faz a média de 2 amostras.
   Inclinação `pitch = asin(-y/|g|)` em graus.
2. **Calibração** ("标定", botão na UI → `startService(... "biaoding"=true)`): quando estável (3 leituras com Δ<0,3),
   grava `persist.txcz.tt.angle=<pitch>` e `persist.txcz.tt.bdstate=1`. Se `bdstate=0`, calibra sozinho na
   primeira vez que o pitch estiver em (-5°,5°) ou (80°,90°).
3. Ângulo efetivo `a = round(pitch - tt.angle)` (invertido se `tt.angle>60`, projetor apontando pro teto). Recalcula quando
   |Δ| ≥ 2° parado ou ≥ 4° em movimento; guarda `persist.txcz.tt.preAngle`.
4. Converte em cantos:
   - parede (|a|<45): `v = floor(|a|*4.2)`, `vH = floor(H*v*2/W)`;
   - teto (45..135): `v = floor(|90-a|*3.9)`, idem `vH`.
   - Para modos 0/1 e `a ≥ 0`: `lt="v,-vH"`, `rt="-v,-vH"`, `lb=rb="0,0"` (estreita a borda de cima).
     Para `a<0`: estreita a borda de baixo (`lb="v,vH"`, `rb="-v,vH"`). Modos de teto invertem.
5. Aplica via `BridgeService.absChange(lt, lb, rt, rb)` → cantos = base `init.xy` + offset (com limites) →
   `persist.sys.keystone.update=1`.

`persist.txcz.tt.txfx` (switch "direção") é gravado mas não é lido pelo serviço. `tt.display` só vem do build.prop.
Só corrige a inclinação vertical (pitch). Não há correção horizontal (yaw), nem câmera ou ToF.

Shell (equivalente a um passo do serviço, a=10° parede): `v=42, vH=floor(720*42*2/1280)=47`
```sh
am startservice ... -d 'settings2txcz://k?action=4&0=42,-47&1=0,0&2=-42,-47&3=0,0'
# ou direto: somar (42,-47) a lt.init.xy e (-42,-47) a rt.init.xy, gravar lt/rt e update=1
```

## 3. Espelhar / girar / inverter

Não existe opção de rotação de display. Os 4 "modos de projeção" (`install.model`, §1) são a única forma, e
todos são feitos por keystone. `persist.sys.hwrotation(.txcz)`, `persist.sys.isflip.{h,v}(.txcz)`,
`persist.sys.mirror_{x,y}.txcz` vêm do `build.prop` (=0), o app só **lê**, e nenhum outro binário do ROM os lê
(busca em toda a `super.img`: só aparecem em `build.prop` e no APK). O SF lê `persist.sys.keystone.mirror_x/_y`
(=0), um espelho nativo do keystone que o app não usa.

## 4. Zoom / escala

- Zoom do app = keystone (§1, `persist.txcz.trapezoid.zoom`).
- `persist.sys.txcz.dscale` **não** é usada por este app. Quem lê é o framework (`RkDisplayModes.init`, só no boot): se <100,
  aplica overscan RK nos 4 lados (ver `../services-jar/README.md`). Não há UI que escreva essa prop.

## 5. Foco

O app **não** controla o motor. "Foco automático" (`AutoFocusActivity`):
- switch → `persist.txcz.focus.auto` (padrão 1) + inicia/para `Sensorservice`;
- "foco + keystone" → `persist.txcz.focus.tixing`; modo → `persist.txcz.focus.txmode`;
- `Sensorservice` lê o acelerômetro (ou o *rotation vector* se `persist.sys.automatic.mode=6D`), grava
  `persist.txcz.sensor.angle`. Quando detecta que o aparelho foi movido e ficou parado (5 amostras), chama
  `startService(ComponentName("com.hysd.txczscreen","com.hysd.client.VAF2S"))` com extras
  `mode, firstopen, afswitch, keyswitch, dmode, castmode`. Também faz isso ao receber o broadcast
  `intent.action.txcz.sensor` (`SensorReceiver`).
- **`com.hysd.txczscreen` não está instalado no HY300** (não aparece em `pm list packages` nem na `super.img`).
  Portanto o autofoco do menu não faz nada neste aparelho. O foco real é o motor (`../libfocus/README.md`).

## 6. Fonte / entrada HDMI e boot direto na fonte

- Menu "Outras configurações → Fonte ao ligar" (`SystemSettingAppActivity`):
  - 0 Home → `persist.txcz.source=0`, `persist.txcz.boot.app=""`
  - 1 HDMI → `persist.txcz.source=1`, `persist.txcz.boot.app=com.android.rockchip.camera2,com.android.rockchip.camera2.RockchipCamera2`
  - 2 App → `StartAppActivity`: `persist.txcz.source=2`, `persist.txcz.boot.app=<pacote>`
- Consumidor: `RootWindowContainer.startHomeOnTaskDisplayArea` no `services.jar` (ver services-jar). O app HDMI
  é o `rkCamera3.apk` (pacote `com.android.rockchip.camera2`).
- Abrir HDMI agora: tecla F6 (keycode 136) no controle, ou
  `am start -n com.android.rockchip.camera2/.RockchipCamera2`.
- `persist.txcz.boot.enable` (=1 no build.prop) não é lida por nenhum binário encontrado.

```sh
setprop persist.txcz.source 1
setprop persist.txcz.boot.app com.android.rockchip.camera2,com.android.rockchip.camera2.RockchipCamera2
```

## 7. Imagem / cor (PQ)

`ProjectorModel.getColorType()`: 0 se existir `/system/bin/tees1`, **1 se existir `/vendor/etc/pq_play.json` (HY300)**,
2 se existir `/system/bin/testgammatx_y.sh`.
Com tipo 1, "Modo de cor" grava `persist.txcz.color.model=i` e
`persist.vendor.pq.path` = `/vendor/etc/pq_play.json` | `pq_play_yanli.json` | `pq_play_rouhe.json`.

Achados:
- **Nenhum binário do ROM lê `persist.vendor.pq.path`** (busca na `super.img` inteira: só aparece no APK).
  O PQ real é `vendor/lib/libpq.so` (RK), que lê `persist.vendor.rkpq.config.path`. O `init.rk356x.rc` força essa prop para
  `/vendor/etc/pq_ui.json` a cada boot. Na prática, o "modo de cor" do app não tem efeito.
- `pq_play_yanli.json` e `pq_play_rouhe.json` são **idênticos** (mesmo md5). `pq_ui.json` == `pq_play.json`.
- Diferenças "vívido" × normal: `csc` brilho 88→145, matiz 253→300, contraste 345→310, saturação 385→350;
  tabelas ACM e gamma diferentes; `sharpPeakingGain` 701→900.
- Tipos 0/2 (outras placas) executam `/system/bin/tees1` ou `sh /system/bin/testgammatx_{y,r}.sh`. Voltar para "normal" pede reboot
  e, antes do reboot, apaga LEDs (`/sys/class/leds/{green,red,Fan,Lcd_power}/brightness=0`).
- `UsbReceiver` (MEDIA_MOUNTED) chama `changeColorMode()` (só tem efeito nos tipos 0/2).

Detalhes do JSON e de quem consome: `../display/README.md`.

## 8. Demais telas

| UI | Classe | Mecanismo |
|---|---|---|
| Wi-Fi | `WifiActivity`, `WifiInputPwdActivity`, `WifiAddActivity` | `WifiManager` padrão |
| Bluetooth | `BlueToothActivity` | `BluetoothAdapter` padrão |
| Idioma | `LanguageActivity` | `LocaleInfo.updateLocale` → `ActivityManagerNative.updateConfiguration` (precisa de CHANGE_CONFIGURATION) |
| Data/hora | `DateActivity` | `Settings.Global auto_time`, `Settings.System time_12_24` e `date_format`, `AlarmManager.setTimeZone`, broadcast `TIME_SET` |
| Tela Elenco (espelhamento) | `ScreenCastActivity` | só abre apps de terceiros: `com.hpplay.happyplay.aw`, `com.airplay.mirror`, `com.ecloud.eshare.server` |
| Caixa de som BT | `SoundBoxActivity` + `SoundBoxService` | `persist.bluetooth.rka2dpsink=true` (A2DP sink), `persist.txcz.sound.enable`, desliga ventoinha e LED (`/sys/class/leds/{Fan,Fan_h,LED_CRL,Lcd_power}/brightness`), Wi-Fi off |
| Outras config. | `SystemSettingAppActivity` | abre `com.android.tv.set/.MainSettings` (TvSettings RK) |
| Sobre | `AboutActivity` | `persist.txcz.set.banben`, `persist.txcz.set.xtrl`; botão de atualização abre `com.adups.fota/.GoogleOtaClient` ou `com.txcz.update/.GoogleOtaClient` |
| Atualização (item "upgrade", se `persist.sys.txcz.sys2update=1`) | `MainActivity` | idem |
| Proteção de tela | `MyDreamService` + `ColorsGLRenderer` | DreamService com animação GL |

## 9. Segurança (componentes exportados)

- `receiver.VsReceiver` (**exportado, sem permissão**, prioridade máxima), action `intent.action.txcz.vs`, extras
  `wid` (int) e `value` (string) → `VendorStorageJNI.writeVendorStorage(wid, value)`. **Qualquer app** pode
  gravar qualquer id do *vendor storage* (onde ficam SN, MACs etc.) através de um processo uid system.
- `com.vendor.store.MyService` (exportado, action `com.vs.wr.action`): binder AIDL `VsAidlInterface` com
  `readVendorStorage(id,len)` / `writeVendorStorage(id,str)`. Mesmo problema.
- `BridgeService`, `Sensorservice`, `TaitouService` exportados (qualquer app altera o keystone).
- O app em si não abre conexão de rede (nenhuma URL no código).

Telemetria e OTA do ROM: `../telemetria/README.md`.
