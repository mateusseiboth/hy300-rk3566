# HY300 Settings (`io.github.hy300.settings`)

App de configurações do projetor HY300 (RK3566, TXCZ LightOS, Android 12) que substitui o
TxczSetting (`com.android.tv.settings`). É uma reimplementação: nenhum código do app TXCZ foi copiado.
A especificação dos mecanismos está em `reverse-engineering/MAP.md`.

UI no estilo das Configurações do Android TV (`androidx.leanback:leanback-preference` 1.2.0, painel lateral),
toda navegável por D-pad. Telas de ajuste em tela cheia, com padrão de teste. Strings em PT-BR. Java, sem código nativo.

## O que funciona

Legenda: **[testado]** = executado no aparelho e conferido pelas props/logs; **[não testado]** = implementado, sem verificação no aparelho.

| Função | Estado | Mecanismo |
|---|---|---|
| Gravar props `persist.*` como app comum | **[testado]** | `Runtime/ProcessBuilder` → `/system/bin/setprop` (SELinux permissive) |
| Keystone 4 cantos (passos 1/5/20 px, OK troca o canto, 0/Del restaura) | **[testado]** | `persist.sys.keystone.{lt,lb,rt,rb}` + `*.init.xy` + `update=1` |
| Trapézio V/H | **[testado]** | move 2 cantos; contador em `persist.txcz.trapezoid.offsetx/offsety` |
| Zoom 20–100 % | **[testado]** (95 → 100) | base recalculada, ajustes preservados |
| Restaurar keystone (tecla 0/Del na tela cheia ou item do menu) | **[testado]** | |
| Modo de instalação (4 modos) e proporção 16:9/4:3 | **[não testado no aparelho]** (matemática coberta por testes unitários) | |
| Padrão de teste em tela cheia (borda, grade, cantos, círculo) | **[testado]** | `TestPatternView` |
| SF consome `update=1` e volta para 0 | **[testado]** | relê na próxima composição; com a tela parada fica em 1 até o próximo quadro |
| Foco +/− com repetição a cada 60 ms enquanto a tecla está pressionada | **[testado]** só os comandos (logs do kernel); movimento visual **[não confirmado]** | sysfs `motor` |
| Fim de curso (`hd_camera_on == 1` para o motor) | **[não testado]** (o nó lê 0) | |
| Abrir HDMI | **[não testado]** (o intent é o do MAP) | `com.android.rockchip.camera2/.RockchipCamera2` |
| Fonte ao ligar (Home / HDMI / app da lista) | UI e leitura **[testadas]**; gravação usa o mesmo `setprop` | `persist.txcz.source` + `persist.txcz.boot.app` |
| Brilho/contraste/saturação/matiz | grava as props **[testado]**; efeito visual **[não confirmado]** | ver "Imagem" |
| Keystone automático (liga/desliga, calibrar, inverter) | **[não testado no aparelho]** (ver aviso abaixo); fórmula coberta por teste | serviço próprio com o acelerômetro |
| Tecla F12 do controle abre este app | **[testado]** com evento real de evdev (`sendevent`) | serviço de acessibilidade |
| Ícone/banner leanback (aparece no Projectivy) | **[testado]** | `android:banner`, `LEANBACK_LAUNCHER` |
| Item "Projetor" no menu principal do TvSettings | preparado; **requer instalação como app de sistema + reboot** | ver "Integração" |
| A2DP sink | switch de `persist.bluetooth.rka2dpsink` **[não testado]** | precisa reiniciar o BT/aparelho |

Testes unitários (JVM): `./gradlew testDebugUnitTest` (7 testes de `Keystone` e da fórmula do automático, todos passando).

### Modelo do keystone

`Keystone.java`. Props do SF: deslocamento "x,y" de cada canto, em px de 1280×720, com x para a direita e y para cima.
- **base(modo, zoom, proporção)** = mesmas fórmulas do TXCZ (`reset/x_mirror/xy_mirror/y_mirror`):
  `zw=Sw·z/100`, `minX=(1280−zw)/2`, `maxX=minX+zw` (idem para y). Os modos espelhados usam `max`.
- **ajuste do usuário** por canto, em coordenadas do *espectador* (canto da imagem como aparece na parede).
  Nos eixos espelhados pelo modo, o sinal é invertido (mesma regra de `getXRealValue/getYRealValue` do TXCZ).
- Ao gravar: `init.xy = base` e `canto = base + sinal·ajuste`. O ajuste é extraído das props atuais (`prop − base`),
  então mudar o zoom, a proporção ou o modo **não perde** os ajustes, e mudanças feitas pelo app TXCZ também são respeitadas.
- Props TXCZ mantidas coerentes: `persist.txcz.install.model`, `trapezoid.zoom`, `trapezoid.offsetx/offsety`, `screen.width/height/ratio`.
- Limites: até 1/3 da área para dentro; para fora, só até a borda do painel.
- Trapézio: positivo em V estreita o topo (negativo, a base); positivo em H estreita a esquerda. Cada unidade move os dois cantos 1 px em x e 9/16 px em y (H: 16/9 px em x e 1 px em y).
  **Diferença do TXCZ:** a semântica de `offsetx/offsety` do TXCZ não ficou clara no código decompilado. Se o TXCZ deixar
  um contador ≠ 0 com outro significado, o primeiro passo do trapézio aqui pode deslocar os cantos de forma inesperada. Use "Restaurar".

### Foco: o que o kernel aceita de fato

O `motor_store` (kernel em `boot.img`, desmontado em `0x7359b0`) compara o buffer **inteiro** com `strcmp`, então `echo cmd >` (com `\n`) **não faz nada**:
- `user_cw` / `user_ccw` = 10 passos síncronos; `aacw`/`aaccw` = contínuo; `aastop` = parar; `aacw_end`/`aaccw_end` = até o fim de curso.
- **`stop` não existe** (o MAP/libfocus diz o contrário: corrigir lá). O framework (`MaDaDialog`) também usa `stop` e `motoraa`, por isso nunca funcionou.
- Depois de tratar o comando, a função tenta `kstrtoint` e devolve **-EINVAL para qualquer string**: a escrita "falha" mesmo quando o motor anda. O app ignora o erro.
- Pela shell: `printf user_cw > /sys/class/motor_cc/motor_cc/motor`.

### Imagem

- Escala **0–100, padrão 50**: é o que o TvSettings RK usa (`display/AdvancedDisplaySettingsActivity`, via `RkDisplayOutputManager.setBrightness(display, v)`).
- `android.os.RkDisplayOutputManager` está **bloqueada pela política de API oculta** para este app (log: `Accessing hidden method ... blocked`). O app tenta essa classe primeiro e, se falhar, grava
  `persist.vendor.<item>.main` e incrementa `vendor.display.timeline`. Esse é o gatilho que o HWC observa (`HwcDisplay::UpdateBCSH` faz `property_get_int32("vendor.display.timeline")` e só reaplica quando o valor muda).
- Efeito visual no painel LVDS **não confirmado**. O HWC pode cair no caminho de "baseparameter" se o conector LVDS não tiver propriedades BCSH.
- **Perfil PQ** (`persist.vendor.rkpq.config.path`): testado. O `libpq` não relê em runtime (nenhum log, sem efeito), e o `init` força `pq_ui.json` em todo boot.
  Removido da UI. Observação: o HWC roda o PQ (RKSWPQ/OpenCL) em **todo quadro**, então o PQ afeta também a UI, não só o HDMI.

### Keystone automático: aviso

O serviço `AutoKeystoneService` (foreground) reimplementa o `TaitouService`: média de 2 amostras, estabilidade de 3 leituras, `a = pitch − tt.angle`,
`v=⌊|a|·4,2⌋` e `vH=⌊720·v·2/1280⌋` (ou `⌊|90−a|·3,9⌋` projetando no teto). Ele recalcula quando |Δ| ≥ 2° parado ou ≥ 4° em movimento, calibra quando pedido (`tt.angle`, `tt.bdstate=1`) e grava `tt.preAngle`.
Diferenças: a correção é **somada** ao ajuste manual (a contribuição anterior fica em SharedPreferences e é retirada antes da nova). Ao desligar, ela é removida. Nos modos de teto o sinal é invertido, e `tt.txfx` funciona como "inverter direção".

**Não foi ligado no aparelho:** a calibração atual (`tt.angle=27,99`) está muito longe da inclinação lida agora (≈72,8°). Ligar sem recalibrar aplicaria uma correção enorme.
Para testar: projetor na posição instalada → "Calibrar agora" → "Ativar". Se o app TXCZ continuar instalado com `tt.enable=1`, o `TaitouService` dele também liga no boot e os dois brigam.
Nesse caso, desative o dele: `adb shell pm disable com.android.tv.settings/com.shzhtxcz.txbox.service.TaitouService`.

## Compilar e instalar

```sh
cd android/hy300-settings
export JAVA_HOME=~/.jdks/jbr-17.0.8          # JBR 17 (o java 25 do sistema não serve para o AGP)
echo "sdk.dir=$HOME/Android/Sdk" > local.properties
./gradlew assembleRelease                     # R8 ligado, assinado com a chave debug (~2 MB)
./gradlew testDebugUnitTest
adb install -r app/build/outputs/apk/release/app-release.apk
```
Toolchain: Gradle 8.14.3 (wrapper), AGP 8.11.0, compileSdk 35, minSdk 30, targetSdk 32.
`assembleDebug` também funciona (~11 MB, sem R8). Release e debug usam a mesma chave, então dá para trocar um pelo outro com `install -r`.

Para o atalho F12 (uma vez): `adb shell pm grant io.github.hy300.settings android.permission.WRITE_SECURE_SETTINGS`
e ligar em **Outros → Tecla de configurações (F12)** (ou `settings put secure enabled_accessibility_services io.github.hy300.settings/io.github.hy300.settings.F12KeyService`).
Como priv-app a permissão é concedida automaticamente.

## Modelo de permissões (decisão)

**App comum (uid de app, `/data`) + `setprop` por `ProcessBuilder`.** Verificado logo no início com um APK mínimo:
o `setprop` de um `untrusted_app` grava `persist.*` (o audit mostra `avc: denied { set } ... permissive=1`, mas o valor é gravado).
Os nós do motor são 0777 (DAC ok, SELinux permissive). Leitura: um único `getprop` com parse da saída, para não usar API oculta.

Por quê: dispensa assinatura de plataforma (não temos a release-key) e `sharedUserId=system`. Instala e atualiza com `adb install`.
**Fragilidade:** depende do SELinux em permissive. Se algum dia ficar enforcing, as alternativas são:
1. priv-app não resolve `setprop` (o domínio continua `priv_app`, sem permissão para `default_prop`/`system_prop`). Precisaria de política SELinux nova (vendor/system sepolicy), o que exige reflash.
2. Ponte pelo app TXCZ (uid system): `BridgeService` (`settings2txcz://?action=1..4`) para o keystone e `VsReceiver`. Cobre só o keystone e depende do app que vai ser aposentado.
3. Serviço nativo root via `init.rc` no overlay, ouvindo props `persist.hy300.*` e repassando.

Nada disso foi necessário agora.

Os LEDs/ventoinha (`/sys/class/leds/{Fan_h,green,red}`) são `0644 root/system` → um app comum não grava. Ficou em TODO (o `Lcd_power` é 0777, mas é a fonte de luz: não mexer).

## Integração com as Configurações do Android

O TvSettings do aparelho é o `com.android.tv.set` (flavor "Classic", `res/xml/main_prefs.xml`). Não há mecanismo genérico de tiles injetados no menu principal do TvSettings 12.
Há, porém, o item oculto **`sound`**, com `intent action=com.android.tv.set.SOUND`:
`MainFragment.updateSoundSettings()` o torna visível se um **app de sistema** (`FLAG_SYSTEM`) tratar essa ação. Título, resumo e ícone vêm dos
recursos `sound_pref_title`, `sound_pref_summary` e `sound_icon` do pacote que trata a ação. Este app declara a ação na `MainActivity` e fornece os três recursos
("Projetor" / "Keystone, foco, fonte e imagem"), protegidos do `shrinkResources` por `res/raw/keep.xml`.
Efeito colateral: com isso, o `DevicePrefFragment` esconde o item "Sons do sistema" (em Preferências do dispositivo).

Para ativar (**pendente, precisa de reboot**):
```sh
./gradlew assembleRelease
system/install-system.sh     # adb root + remount; copia para /system/priv-app/HY300Settings + privapp-permissions
adb reboot
```
Depois do reboot, a cópia em `/data` (mesma assinatura e versão) vira atualização do app de sistema.
`ro.control_privapp_permissions` está vazio (não é enforce), então não há risco de bootloop por permissão faltando. Reverter: `system/uninstall-system.sh` + reboot.

Também:
- **Launcher leanback:** banner e ícone. Aparece no Projectivy como "Projetor".
- **Tecla F12 (142):** o `TxczPwd.setExKey` roda em `PhoneWindowManager.interceptKeyBeforeDispatching`. O filtro de teclas da acessibilidade roda **antes**,
  então o `F12KeyService` consome o 142 e abre este app, sem mexer no `services.jar`. Observação: `input keyevent 142` **não** passa pelo filtro
  (eventos injetados não passam), então para testar use o controle ou `sendevent /dev/input/event0 1 188 1; ... 0 0 0; ... 1 188 0; ... 0 0 0`.
  Alternativa sem acessibilidade (depois de aposentar o TXCZ): apagar o `TxczSetting` do `/system` e instalar um "shim" com pacote
  `com.android.tv.settings` e uma activity chamada `com.shzhtxcz.txbox.MainActivity` que só redireciona para cá.

## Estrutura

```
app/src/main/java/io/github/hy300/settings/
  Sys               getprop/setprop/sysfs
  Keystone          modelo (base + ajuste), props
  KeystoneApplier   gravação assíncrona com coalescência
  KeystoneActivity  tela cheia: cantos / trapézio / zoom / padrão
  TestPatternView   padrão de teste
  Focus, FocusActivity
  AutoKeystoneService, AutoKeystoneFragment
  Source, SourceFragment, AppPickerFragment
  RkDisplay, ImageFragment
  OtherFragment (A2DP, F12, abrir TXCZ), DiagFragment, Diag
  F12KeyService, BootReceiver (religa o automático no boot; ouve também android.intent.action.txcz.BOOT_COMPLETED)
  MainActivity, SettingsFragment, RootFragment, ProjectionFragment, BasePrefs, Bg
system/  install-system.sh, uninstall-system.sh, privapp-permissions-hy300-settings.xml
```

## Pendências / TODO (para o próximo agente)

1. **Reboot para a integração com o TvSettings:** rodar `system/install-system.sh`, reiniciar e conferir o item "Projetor" no menu principal de `com.android.tv.set` e o `DiagFragment` ("Instalado como app de sistema: sim").
2. **Keystone automático:** calibrar no lugar, ligar e validar a direção (usar "Inverter direção" se estreitar o lado errado). Validar a regra dos modos de teto. Desativar o `TaitouService` do TXCZ.
3. **Validação visual com o usuário:** foco (sentido de `user_cw` = "+"?, tamanho do passo, fim de curso), BCSH (se tem efeito; senão remover a tela Imagem ou achar outro caminho, por exemplo `settings put global hidden_api_policy 1` para liberar `RkDisplayOutputManager`, ou o binder `drm_device_management`), modo de instalação e 4:3.
4. **Segurar a tecla no foco:** usa `ACTION_DOWN` repetido/`ACTION_UP`; conferir com o controle IR real (o IR pode mandar repetições sem `UP` intermediário, o que é tratado, mas não foi testado).
5. **Trapézio × TXCZ:** confirmar a semântica de `persist.txcz.trapezoid.offsetx/offsety` no TXCZ (`ProjectorVerticalActivity`/`Limit.offsetXIsInLimit`, decompilação confusa) e alinhar, ou zerar os contadores ao abrir.
6. **Vendor storage id 50** (modo de instalação): o TXCZ grava ao trocar o modo; este app não grava (sem JNI). Investigar quem lê (u-boot/logo). Se importar, usar o `VsReceiver` do TXCZ enquanto existir: `am broadcast -a intent.action.txcz.vs --ei wid 50 --es value <modo>`.
7. **Ventoinha/LEDs:** nós `0644`; precisa de root/init (ex.: `chmod` num `init.rc` do overlay) para o app controlar.
8. **PQ:** trocar perfil exige reiniciar o HWC/reboot e contornar o `init` que força `pq_ui.json`. Fora do alcance de um app.
9. Corrigir `reverse-engineering/libfocus/README.md` e `MAP.md`: comando de parada é `aastop` (não `stop`), escrita sem `\n`, -EINVAL esperado.
10. Polimento: resumo do Diagnóstico é truncado pelo layout leanback (máx. linhas); ícones nos itens do menu; textos de ajuda das telas cheias.
