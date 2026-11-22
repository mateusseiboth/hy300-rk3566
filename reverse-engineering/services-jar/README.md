# `services.jar` — modificações TXCZ no framework

- `/system/framework/services.jar` (com `classes.dex` + `classes2.dex`; o `oat/arm/services.{odex,vdex,art}` é só AOT).
- Decompilado com jadx 1.5.7 (`--no-res`). Busca por `txcz|keystone|trapezoid|hysd|zeasn` + leitura das classes.
- `framework.jar` **não** tem nenhuma referência a `txcz`/`keystone`/`isflip` (busca nos 4 dex).

Classes alteradas ou adicionadas:

| Classe | Alteração |
|---|---|
| `com.android.server.policy.TxczPwd` (nova) | teclas especiais e sequências secretas do controle |
| `com.android.server.policy.MaDaDialog` (nova) | diálogo + motor de foco por teclas F7/F8 |
| `com.android.server.policy.PhoneWindowManager` | chama `TxczPwd.setExKey` em `interceptKeyBeforeDispatching`; keycodes 136/137/138; LED piscando em apps de teste |
| `com.android.server.wm.RootWindowContainer` | abre `persist.txcz.boot.app` ao iniciar a Home |
| `com.android.server.rkdisplay.RkDisplayModes` | aplica `persist.sys.txcz.dscale` como overscan no boot |
| `com.android.server.am.UserController` | envia broadcast extra `android.intent.action.txcz.BOOT_COMPLETED` |
| `com.android.server.am.ActivityManagerService` | `checkBroadcastFromSystem`: ignora actions que contêm `"txcz"` (sem aviso de broadcast não protegido) |

Nenhum hook de keystone, trapézio, PQ ou rotação no framework: o keystone é todo no SurfaceFlinger (ver `../display/README.md`).

## 1. Boot direto em app/fonte — `RootWindowContainer.startHomeOnTaskDisplayArea`

Depois de iniciar a Home, se `startApp` ainda for falso e `persist.txcz.boot.app` não estiver vazia:
- formato `pkg,Activity` → thread dorme **10 s** (`JobStatus.DEFAULT_TRIGGER_UPDATE_DELAY`) e depois
  `startActivityAsUser(new ComponentName(pkg, Activity), FLAG_ACTIVITY_NEW_TASK, CURRENT_OR_SELF)`;
- formato `pkg` → resolve a activity `MAIN/LAUNCHER` do pacote e abre na hora.
- Só uma vez por boot (`startApp=true`).

`persist.txcz.boot.enable` **não** é lida aqui nem em nenhum outro lugar encontrado.

```sh
setprop persist.txcz.boot.app com.android.rockchip.camera2,com.android.rockchip.camera2.RockchipCamera2   # HDMI no boot
setprop persist.txcz.boot.app ""                                                                          # só Home
```

## 2. Escala / overscan — `RkDisplayModes.init()`

```java
int i = SystemProperties.getInt("persist.sys.txcz.dscale", 100);
if (i < 100) { nativeSetScreenScale(0, 0, i); nativeSetScreenScale(0, 1, i);
               nativeSetScreenScale(0, 2, i); nativeSetScreenScale(0, 3, i); }
```
Display 0, direções 0..3 (esquerda/topo/direita/baixo), valor em % (RK: 100 = sem borda). Só roda na
inicialização do serviço `drm_device_management` (`RkDisplayDeviceManagementService`). Nenhum app escreve a prop
(padrão 100 no `build.prop`).

Em runtime, o mesmo efeito vem do overscan RK padrão:
- API oculta `android.os.RkDisplayOutputManager.setOverScan(display, direção, valor)` (o `TvSettings` /
  `ScreenScaleActivity` usa por reflexão) → binder `drm_device_management.setScreenScale(...)`;
- o HWC (`hwcomposer.rk30board.so`) lê `persist.vendor.overscan.main` = `"overscan l,t,r,b"` (vazia no aparelho).

```sh
setprop persist.sys.txcz.dscale 90                       # vale no próximo boot
setprop persist.vendor.overscan.main "overscan 90,90,90,90"   # formato do HWC RK (provavelmente precisa de refresh/reboot)
```

## 3. Teclas — `PhoneWindowManager` + `TxczPwd.setExKey(keyCode, ctx, down)`

Mapeamento do controle IR (`/vendor/usr/keylayout/fdd70030_pwm.kl`): scancode linux 180..184 → `F1..F5`
(keycodes 131..135), 187 → `F6` (136), 189 → `F11` (141), 188 → `F12` (142), 185/186 → DPAD_UP/DOWN.

| Keycode | Origem | Ação |
|---|---|---|
| 84 (SEARCH) | — | broadcast `com.txcz.voice` (`keyCode`, `down`) em descida e subida |
| 131, 132, 133, 134 (F1..F4) | IR | broadcast `com.shzhtxcz.exkey` (`keyCode`) → `com.shzhtxcz.txbox/ExKeyIntentService` (abre "todos os apps", "ao vivo", "desktop", configuráveis pelo servidor) |
| 29, 135, 140, 141, 183 | IR/BT | broadcast `com.txcz.myapplication.NewBlueReceiver` (`keyCode`) |
| 136 (F6) | IR | `startActivity com.android.rockchip.camera2/.RockchipCamera2` (**HDMI**) |
| 137 / 138 (F7/F8) | — (não estão no .kl IR) | `MaDaDialog.rotation(ccw/cw)`: escreve `ccw`/`cw` a cada 60 ms em `sys/class/motor_cc/motor_cc/motoraa` e `stop` ao soltar. Esse nó não existe no HY300 (ver libfocus) |
| 142 (F12) | IR | abre `com.android.tv.settings/com.shzhtxcz.txbox.MainActivity` (TxczSetting) |

Sequências secretas (`TxczPwd.checkMsg`, keycodes em sequência):

| Sequência | Ação |
|---|---|
| `1 8 6 5 0` (8,15,13,12,7) ou `← → ↓ MENU BACK` | `setprop persist.sys.prison_break 1` + broadcast `com.shzhtxcz.prison` (destrava menus "limitados") |
| `1 8 6 2` ou `← → ↓ MENU ↓` | abre `com.shzhtxcz.txcz.test/com.shzhtxcz.txbox.MainActivity` (app de teste de fábrica) |
| `MENU ↑ ↓ ← →` | abre `com.shzhtxcz.txcz.test/com.shzhtxcz.txbox.VideoActivity` |
| `1 8 6 3` ou `← → ↓ BACK BACK` | abre teste de envelhecimento (`com.example.txczdevicetest`, `com.rockchip.devicetest/.AgingTestActivity` ou `com.linkin.devicerest`) |

`startTimer()`: enquanto um app de teste (`com.linkin.product.test`, `com.linkin.devicerest`, `com.rockchip.devicetest`,
`com.example.txczdevicetest`) estiver em primeiro plano, pisca `/sys/class/leds/green/brightness` a cada 1 s.

Shell equivalente:
```sh
input keyevent 136          # HDMI
input keyevent 142          # TxczSetting
am broadcast -a com.shzhtxcz.exkey --ei keyCode 131
```

## 4. Broadcast de boot extra — `UserController`

Antes do `BOOT_COMPLETED` normal, o sistema envia `android.intent.action.txcz.BOOT_COMPLETED` (com
`RECEIVE_BOOT_COMPLETED`, `FLAG_RECEIVER_FOREGROUND`). O TxczSetting (`OnLineOrOffLineReceiver`) escuta esse broadcast
e o normal, e no boot religa `SoundBoxService` (se `persist.txcz.sound.enable=1`), `Sensorservice` (se `persist.txcz.focus.auto=1` e o
app hysd existir) e `TaitouService` (se `persist.txcz.tt.enable=1`). `android.intent.action.txcz.fast.BOOT_COMPLETED` também
está no manifest, mas ninguém o envia no `services.jar`.
