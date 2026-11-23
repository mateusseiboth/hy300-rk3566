# HY300 Settings (`io.github.hy300.settings`)

App de configurações do projetor HY300 (RK3566, TXCZ LightOS, Android 12) que substitui o
TxczSetting (`com.android.tv.settings`). É uma reimplementação: nenhum código do app TXCZ foi copiado.
A especificação dos mecanismos está em `reverse-engineering/MAP.md`.

UI no estilo das Configurações do Android TV (`androidx.leanback:leanback-preference` 1.2.0, painel lateral),
toda navegável por D-pad. Telas de ajuste em tela cheia, com padrão de teste. Strings em PT-BR. Java, sem código nativo.

## O que funciona

Legenda: **[testado]** = executado no aparelho e conferido (props, logs, `uiautomator dump`, `screencap`); **[não testado]** = implementado, sem verificação no aparelho;
**[só o usuário]** = depende de olhar a projeção ou de usar o controle físico.

| Função | Estado | Mecanismo |
|---|---|---|
| Gravar props `persist.*` como app comum | **[testado]** | `Runtime/ProcessBuilder` → `/system/bin/setprop` (SELinux permissive) |
| Keystone 4 cantos (passos 1/5/20 px, OK troca o canto, 0/Del restaura) | **[testado]** | `persist.sys.keystone.{lt,lb,rt,rb}` + `*.init.xy` + `update=1` |
| Trapézio V/H com a mesma regra do TXCZ | matemática **[testado]** nos testes unitários; no aparelho **[não testado]** desde a mudança | contador em `persist.txcz.trapezoid.offsetx/offsety` (ver "Modelo do keystone") |
| Zoom 20–100 % | **[testado]** (95 → 100) | base recalculada, ajustes preservados |
| Restaurar keystone (tecla 0/Del na tela cheia ou item do menu) | **[testado]** | também esquece a contribuição do automático |
| Modo de instalação (4 modos) e proporção 16:9/4:3 | **[só o usuário]** (matemática coberta por testes) | |
| Padrão de teste em tela cheia (borda, grade, cantos, círculo) | **[testado]** | `TestPatternView` |
| SF consome `update=1` e volta para 0 | **[testado]** | relê na próxima composição; com a tela parada fica em 1 até o próximo quadro |
| Foco +/− com repetição a cada 60 ms enquanto a tecla está pressionada | comandos **[testado]** (logs do kernel); movimento **[só o usuário]** | sysfs `motor` |
| Fim de curso (`hd_camera_on == 1` para o motor) | **[não testado]** (o nó lê 0) | |
| Abrir HDMI | **[não testado]** | `com.android.rockchip.camera2/.RockchipCamera2` |
| Fonte ao ligar (Home / HDMI / app da lista) | UI e leitura **[testadas]**; gravação usa o mesmo `setprop` | `persist.txcz.source` + `persist.txcz.boot.app` |
| Brilho/contraste/saturação/matiz | HWC aplica no conector **[testado]** (log); efeito visual **[só o usuário]** | ver "Imagem" |
| Keystone automático | **desligado por padrão** e não sobe no boot **[testado]**; calibrar/ativar **[só o usuário]** | estado próprio em SharedPreferences (`AutoKeystoneState`) |
| Tecla F12 do controle abre este app | **[testado]** com `sendevent`, inclusive depois de reiniciar | serviço de acessibilidade `directBootAware` |
| "Configurações do Android" (Projectivy, `android.settings.SETTINGS`) abrem o TvSettings | **[testado]** | `AndroidSettingsActivity` + TxczSetting desativado (ver "Integração") |
| TvSettings com o menu completo (sabor TwoPanel) | **[testado]** (abre sem fechar; itens conferidos com `uiautomator dump`) | overlay estático `tvsettings-overlay` |
| Item "Projetor" no menu principal do TvSettings | **[testado]** depois do reboot | app de sistema + ação `com.android.tv.set.SOUND` |
| LEDs indicadores (verde, vermelho) | permissão 0666 no boot **[testado]**; liga/desliga pelo app **[só o usuário]** | `system/hy300-settings.rc` + `Leds` |
| Ícone/banner leanback (aparece no Projectivy) | **[testado]** | `android:banner`, `LEANBACK_LAUNCHER` |
| A2DP sink | **[não testado]** | `persist.bluetooth.rka2dpsink`, vale depois de reiniciar |

Testes unitários (JVM): `./gradlew testDebugUnitTest` (29 testes: `Keystone`, `AutoKeystoneState`, `AndroidSettingsTarget`, `Leds`, `Diag`).

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
- Trapézio, mesma regra do `ProjectorVerticalActivity` do TXCZ (conferida no bytecode, a decompilação do jadx sai errada para ↓ ← →):
  `offsetx` é o **vertical** (↑ soma, ↓ subtrai; positivo estreita o topo, negativo a base) e `offsety` é o **horizontal**
  (→ soma, ← subtrai; positivo estreita a borda direita, negativo a esquerda). Cada unidade move os dois cantos da borda 1 px em x **e** 1 px em y.
  Limite: ±1/3 da largura (V) ou da altura (H) com zoom. Como a regra é a mesma, um contador deixado pelo TXCZ é desfeito corretamente.

### Foco: o que o kernel aceita de fato

O `motor_store` (kernel em `boot.img`, desmontado em `0x7359b0`) compara o buffer **inteiro** com `strcmp`, então `echo cmd >` (com `\n`) **não faz nada**:
- `user_cw` / `user_ccw` = 10 passos síncronos; `aacw`/`aaccw` = contínuo; `aastop` = parar; `aacw_end`/`aaccw_end` = até o fim de curso.
- **`stop` não existe** (o MAP/libfocus diz o contrário: corrigir lá). O framework (`MaDaDialog`) também usa `stop` e `motoraa`, por isso nunca funcionou.
- Depois de tratar o comando, a função tenta `kstrtoint` e devolve **-EINVAL para qualquer string**: a escrita "falha" mesmo quando o motor anda. O app ignora o erro.
- Pela shell: `printf user_cw > /sys/class/motor_cc/motor_cc/motor`.

### Imagem

- Escala **0–100, padrão 50**: é o que o TvSettings RK usa (`display/AdvancedDisplaySettingsActivity`, via `RkDisplayOutputManager.setBrightness(display, v)`).
- O app grava `persist.vendor.<item>.main` e incrementa `vendor.display.timeline`. É o mesmo caminho do `RkDisplayOutputManager`.
  **No LineageOS** grava `persist.sys.hy300.picture.<item>` (o drm_hwcomposer do HY300 lê e aplica no BCSH do VOP2; o sistema não pode
  gravar props do vendor com a sepolicy do Treble), sem o timeline. A ROM é detectada por `ro.lineage.version` (`RkDisplay`).
  Com `vendor.hwc.log=511`, o HWC registra `hwc-drm-connector: UpdateBCSH ... LVDS-0 BCSH=[b,c,s,h]` a cada mudança do timeline, e **não**
  registra "can't find suitable BCSH Property": o conector LVDS tem as propriedades BCSH e o HWC as envia ao kernel. O efeito visual depende do VOP2 e só dá para ver na projeção.
  `screencap` não serve (captura antes do HWC). Não há `/dev/mem` (`CONFIG_DEVMEM` desligado) para ler os registradores do VOP2.
- `android.os.RkDisplayOutputManager` fica bloqueada pela política de API oculta. Com `settings put global hidden_api_policy 1` ela carrega (testado, depois revertido),
  mas não traz nada além do caminho por props, então a política global não é mexida.
- O HWC também relê o `baseparameter` nesse momento ("UpdateConnectorBaseInfo ... Update success"). A partição ficou idêntica ao backup (SHA-256 conferido).
- **Perfil PQ** (`persist.vendor.rkpq.config.path`): o `libpq` não relê em runtime, e o `init` força `pq_ui.json` em todo boot. Removido da UI.
  O HWC roda o PQ (RKSWPQ/OpenCL) em **todo quadro**, então o PQ afeta também a UI, não só o HDMI.

### Keystone automático

O serviço `AutoKeystoneService` (foreground) reimplementa o `TaitouService`: média de 2 amostras, estabilidade de 3 leituras, `a = pitch − ângulo calibrado`,
`v=⌊|a|·4,2⌋` e `vH=⌊720·v·2/1280⌋` (ou `⌊|90−a|·3,9⌋` projetando no teto). Recalcula quando |Δ| ≥ 2° parado ou ≥ 4° em movimento.
Diferenças: a correção é **somada** ao ajuste manual (a contribuição anterior é retirada antes da nova). Ao desligar, ela é removida. Nos modos de teto o sinal é invertido.

**Estado próprio, desligado por padrão.** Liga/desliga, calibração, "inverter" e a contribuição atual ficam juntos no SharedPreferences `autoks` (`AutoKeystoneState`).
Antes o app usava `persist.txcz.tt.enable`, que a TXCZ tinha deixado em 1: o serviço subia em todo boot. Por que SharedPreferences e não uma prop `persist.hy300.*`:
o "ligado" e a contribuição gravada nos cantos têm de sumir juntos. Se os dados do app forem apagados, tudo volta desligado e sem calibração. Com uma prop, o "ligado"
sobreviveria e a próxima correção seria somada sobre a antiga, que já está nos cantos. O app não lê nem grava mais `persist.txcz.tt.*`.
Só corrige com o automático ligado **e** calibrado. "Calibrar agora" com ele desligado só calibra e para. A calibração automática silenciosa do TXCZ (ao achar o aparelho nivelado) foi retirada.

**Não foi ligado no aparelho**: a calibração exige o projetor na posição física e alguém olhando a projeção. O `TaitouService` da TXCZ também fica parado
(pacote desativado e `persist.txcz.tt.enable=0`).

## Compilar e instalar

```sh
cd android/hy300-settings
echo "sdk.dir=$HOME/Android/Sdk" > local.properties   # commandline-tools com platform 35 e build-tools 35.0.0
./gradlew assembleRelease testDebugUnitTest            # JDK 17 (o java do sistema); R8 ligado, assinado com a chave debug
```
Toolchain: Gradle 8.14.3 (wrapper), AGP 8.11.0, compileSdk 35, minSdk 30, targetSdk 32. Saídas: `app/build/outputs/apk/release/app-release.apk`
e `tvsettings-overlay/build/outputs/apk/release/tvsettings-overlay-release.apk`.

Instalação completa (com `ANDROID_SERIAL=<ip:porta>` se houver mais de um aparelho):
```sh
system/install-system.sh            # priv-app + privapp-permissions + .rc dos LEDs no overlay do /system, e o mesmo APK em /data
system/install-tvsettings-overlay.sh  # overlay estático do TvSettings em /product/overlay
system/disable-txcz-settings.sh     # desativa o TxczSetting, liga o atalho F12 (não precisa reiniciar)
adb reboot
```
Reverter: `system/enable-txcz-settings.sh`, `system/uninstall-tvsettings-overlay.sh`, `system/uninstall-system.sh` e reiniciar.

A chave debug é a de `~/.android/debug.keystore` de quem compila. Um APK assinado com outra chave não atualiza o instalado
(`INSTALL_FAILED_UPDATE_INCOMPATIBLE`): rode `adb uninstall io.github.hy300.settings` antes. Os dados do app (atalho, automático, LEDs) se perdem; o keystone fica nas props.

## Modelo de permissões (decisão)

**App comum (uid de app, `/data`) + `setprop` por `ProcessBuilder`.** Verificado logo no início com um APK mínimo:
o `setprop` de um `untrusted_app` grava `persist.*` (o audit mostra `avc: denied { set } ... permissive=1`, mas o valor é gravado).
Os nós do motor são 0777 na ROM de fábrica (DAC ok, SELinux permissive). No LineageOS o `motor` é `system:vendor_hy300_motor` 0660 e o app entra no grupo pela permissão de assinatura `io.github.hy300.settings.permission.FOCUS_MOTOR` que ele mesmo declara (o mapa permissão para gid e o tipo `sysfs_hy300_motor` da sepolicy ficam na árvore do aparelho). Leitura: um único `getprop` com parse da saída, para não usar API oculta.

Por quê: dispensa assinatura de plataforma (não temos a release-key) e `sharedUserId=system`. Instala e atualiza com `adb install`.
**Fragilidade:** depende do SELinux em permissive. Se algum dia ficar enforcing, as alternativas são:
1. priv-app não resolve `setprop` (o domínio continua `priv_app`, sem permissão para `default_prop`/`system_prop`). Precisaria de política SELinux nova (vendor/system sepolicy), o que exige reflash.
2. Ponte pelo app TXCZ (uid system): `BridgeService` (`settings2txcz://?action=1..4`) para o keystone e `VsReceiver`. Cobre só o keystone e depende do app que vai ser aposentado.
3. Serviço nativo root via `init.rc` no overlay, ouvindo props `persist.hy300.*` e repassando.

Nada disso foi necessário agora.

LEDs: os nós `green`/`red` do `gpio-leds` são `0644 system`. O `system/hy300-settings.rc` (em `/system/etc/init` pelo overlay) dá `0666` no `on boot`,
e o `BootReceiver` reaplica os LEDs que o usuário desligou (o device tree liga todos ao iniciar). **Ventoinha (`Fan_h`) e fonte de luz (`Lcd_power`) ficam de fora de
propósito**: a TXCZ só desligava a ventoinha no modo caixa de som (`SoundBoxService`), com a luz apagada. Desligar a ventoinha com a luz acesa aquece o projetor.

## Integração com as Configurações do Android

**Problema:** "abrir Configurações do Android trazia a tela antiga de volta". `android.settings.SETTINGS` só era tratada pelo
`com.android.tv.settings/com.shzhtxcz.txbox.MainActivity` (o TxczSetting da TXCZ, em `/system/app/TxczSetting`). As Configurações reais são o TvSettings
AOSP/Rockchip `com.android.tv.set/.MainSettings` (`/system_ext/priv-app/TvSettings`, pacote renomeado porque a TXCZ ocupou `com.android.tv.settings`;
o código é o do AOSP, a única mudança da TXCZ achada é o nome do modelo em "Acerca de"). A TXCZ tirou do `MainSettings` o filtro de `android.settings.SETTINGS`.
O Projectivy usa exatamente essa ação (`SettingsAndroidActivity` e o ícone de engrenagem da barra de status).

**Correção:**
- Este app declara `android.settings.SETTINGS` em `AndroidSettingsActivity` (sem interface), que repassa para `com.android.tv.set/.MainSettings`.
  O destino é escolhido por `AndroidSettingsTarget` entre quem trata `MAIN` + `LEANBACK_SETTINGS`, nunca o pacote da TXCZ nem este app.
- **Essa activity vem desligada no manifesto (`android:enabled="false"`).** No LineageOS o `com.android.tv.settings/.MainSettings` já trata
  `android.settings.SETTINGS`, e com as duas habilitadas o launcher mostrava o seletor "Concluir a ação usando: Configurações / Projetor". O app é
  complemento do TvSettings, nunca alternativa. Só a ROM de fábrica precisa dela: `system/disable-txcz-settings.sh` faz
  `pm enable io.github.hy300.settings/.AndroidSettingsActivity` e `enable-txcz-settings.sh` desliga de novo. `tests/test_hy300_settings_manifest.py`
  falha se algum componente habilitado do app declarar uma ação `android.settings.*`.
- `system/disable-txcz-settings.sh` desativa o pacote `com.android.tv.settings` inteiro com `pm disable` (nada é apagado; `enable-txcz-settings.sh` reverte).
  Das ações públicas do TxczSetting, só `android.settings.SETTINGS` (no `MainActivity`, com `MAIN`/`LAUNCHER`/`LEANBACK_LAUNCHER`) era de Configurações; as demais
  são do protetor de tela, do `BridgeService`, do vendor storage (`VsReceiver`, `MyService`) e do autofoco (app ausente). Nenhuma outra ação `android.settings.*`
  caía nele (conferido com `cmd package query-activities` para ~40 ações).
- O que o TxczSetting fazia no boot (`OnLineOrOffLineReceiver`): `SoundBoxService` (só com `persist.txcz.sound.enable=1`), `Sensorservice` (só com o app
  `com.hysd.txczscreen`, ausente) e `TaitouService` (por `persist.txcz.tt.enable`). Nada disso é necessário para o keystone ou a fonte: o SF lê
  `persist.sys.keystone.*` e o `services.jar` lê `persist.txcz.source/boot.app` sozinhos. Única perda: o `VsReceiver`, que gravava o vendor storage id 50 (ver TODO 6).
- O script também grava `persist.txcz.tt.enable=0`, troca o protetor de tela padrão (era o da TXCZ) pelo `com.android.dreams.basic/.Colors` e liga o `F12KeyService`.
- Tecla F12: o `TxczPwd.setExKey` (services.jar) continua chamando o `MainActivity` da TXCZ, agora desativado. Testado com `input keyevent 142`
  (eventos injetados não passam pela acessibilidade): o `startActivity` falha e o `system_server` segue vivo (o JNI do input limpa a exceção).
  Com o controle, o `F12KeyService` consome a tecla antes e abre este app.

**Item "Projetor" no menu principal.** No LineageOS a ação é `com.android.tv.settings.SOUND` (mesmo mecanismo, `MainFragment.kt`), e o `MainActivity` declara as duas.

Na ROM de fábrica: Não há tiles injetados no menu principal do TvSettings 12, mas há o item oculto **`sound`**
(`intent action=com.android.tv.set.SOUND`): `MainFragment.updateSoundSettings()` o mostra se um **app de sistema** tratar a ação, com título, resumo e ícone
dos recursos `sound_pref_title`, `sound_pref_summary` e `sound_icon` desse pacote (protegidos do `shrinkResources` por `res/raw/keep.xml`).
Por isso o app é instalado como priv-app (`install-system.sh`). Depois do reboot, a cópia em `/data` (mesma assinatura e versão) vira atualização do app de sistema.
`ro.control_privapp_permissions` está vazio (não é enforce).

**Menu completo do TvSettings.** O TvSettings escolhe o menu por `config_tvSettingsFlavor`. O build da TXCZ usa "Classic", cujo `device.xml` foi enxugado:
"Preferências do dispositivo" tinha só Ecrã, Acerca de, Bluetooth, Data e hora, Idioma e Teclado. O módulo `tvsettings-overlay` (RRO só com recursos, estático em
`/product/overlay`; o TvSettings não declara `<overlayable>`, então um overlay pré-instalado pode trocar o recurso) muda para **"TwoPanel"**, o sabor do AOSP 12
(o do LineageOS). Resultado, com `uiautomator dump`:

| Tela | Antes (Classic) | Depois (TwoPanel) |
|---|---|---|
| Menu principal | Rede e Internet, Contas e início de sessão, Apps, Preferências do dispositivo, Controlos remotos e acessórios | Rede e Internet, Contas e início de sessão, **Projetor**, **Privacidade**, **Ecrã e som**, Apps, Preferências do dispositivo, Controlos remotos e acessórios |
| Preferências do dispositivo | Ecrã, Acerca de, Bluetooth, Data e hora, Idioma, Teclado | Acerca de, Data e hora, Idioma, Teclado, **Armazenamento**, **Proteção de ecrã**, **Poupança de energia**, **Acessibilidade**, **Reiniciar** (Opções de programador aparece quando ativado) |

O "Ecrã" da Rockchip some de Preferências, mas "Ecrã e som" (menu principal) tem Ecrã, Escala do texto e as definições de visualização avançadas.
Bluetooth fica em "Controlos remotos e acessórios". Os sabores **"X" e "Vendor" não servem**: o `NetworkFragment` da Rockchip remove a categoria `vpn`, que não existe no
`network_x.xml`, e o TvSettings fecha na hora (`NullPointerException` em `removePreference`). Testado e descartado.
Também foi conferido que as activities escondidas abrem com `am start` (Armazenamento `StorageResetActivity`, Contas `AccountsActivity`, Teclado `KeyboardActivity`,
Protetor `DaydreamActivity`, Acerca de `AboutActivity`). O idioma do aparelho está em pt-PT ("Definições", "Ecrã"); dá para trocar em Preferências → Idioma.

Também:
- **Launcher leanback:** banner e ícone. Aparece no Projectivy como "Projetor".
- **Tecla F12 (142):** o filtro de teclas da acessibilidade roda antes do `interceptKeyBeforeDispatching`, então o `F12KeyService` consome o 142 e abre este app,
  sem mexer no `services.jar`. O serviço é `directBootAware`: sem isso, no boot, o `AccessibilityManagerService` o ignorava antes do desbloqueio e regravava
  `enabled_accessibility_services` sem ele (o atalho sumia a cada reboot). Para testar sem o controle:
  `sendevent /dev/input/event0 1 188 1; sendevent /dev/input/event0 0 0 0; sendevent /dev/input/event0 1 188 0; sendevent /dev/input/event0 0 0 0`.

## Estrutura

```
app/src/main/java/io/github/hy300/settings/
  Sys               getprop/setprop/sysfs
  Keystone          modelo (base + ajuste, trapézio do TXCZ), props
  KeystoneApplier   gravação assíncrona com coalescência
  KeystoneActivity  tela cheia: cantos / trapézio / zoom / padrão
  TestPatternView   padrão de teste
  Focus, FocusActivity
  AutoKeystoneService, AutoKeystoneFragment, AutoKeystoneState, SharedPrefsStore
  Source, SourceFragment, AppPickerFragment
  RkDisplay, ImageFragment
  Leds, LedBoot, OtherFragment (A2DP, F12, LEDs)
  Diag, DiagFragment, DiagActivity
  AndroidSettingsActivity, AndroidSettingsTarget   android.settings.SETTINGS → TvSettings
  F12KeyService, BootReceiver (LEDs e automático no boot)
  MainActivity, SettingsFragment, RootFragment, ProjectionFragment, BasePrefs, Bg
tvsettings-overlay/   RRO do TvSettings (sabor TwoPanel)
system/  install-system.sh, uninstall-system.sh, privapp-permissions-hy300-settings.xml, hy300-settings.rc,
         install-tvsettings-overlay.sh, uninstall-tvsettings-overlay.sh,
         disable-txcz-settings.sh, enable-txcz-settings.sh
```

## Pendências / TODO (para o próximo agente)

1. ~~Reboot para a integração com o TvSettings~~ **Feito** (item "Projetor" no menu principal, Diagnóstico "Instalado como app de sistema: Sim").
2. **Keystone automático:** calibrar no lugar, ligar e validar a direção ("Inverter direção" se estreitar o lado errado) e a regra dos modos de teto. Só com o usuário.
3. **Validação visual com o usuário:** foco (sentido de `user_cw` = "+"?, tamanho do passo, fim de curso), BCSH (o HWC aplica; falta ver se muda a imagem),
   modo de instalação e 4:3, trapézio depois da mudança de regra, LEDs.
4. **Segurar a tecla no foco:** usa `ACTION_DOWN` repetido/`ACTION_UP`; conferir com o controle IR real.
5. ~~Trapézio × TXCZ~~ **Feito**: mesma regra do TXCZ (ver "Modelo do keystone").
6. **Vendor storage id 50 (modo de instalação): o leitor é o U-Boot da TXCZ.** No probe do `rockchip_display` ele faz `vendor_storage_read(50, buf, 1)` e,
   se o byte for `'2'` ou `'3'` (teto), gira o logo de boot 180°; com outro valor, o logo sai normal (o espelho dos modos 1 e 3 não é reproduzido).
   Kernel, serviços nativos, SF, HWC, init e os apps de `/system` não leem o id 50 (só a lib `libexplay.so` do espelhamento `com.android.toofifi`, em `/odm`,
   tem alguma referência a vendor storage, com id não conferido). Este app **não grava** o id 50 (sem JNI, e o `VsReceiver` da TXCZ ficou desativado):
   trocar o modo pelo app não muda a orientação do logo do U-Boot. Hoje ele segue o que a TXCZ gravou por último. Opções: reativar o TxczSetting por um momento e
   `am broadcast -a intent.action.txcz.vs --ei wid 50 --es value <modo>`; ou um binário nativo que faça o ioctl do `/dev/vendor_storage`.
7. ~~Ventoinha/LEDs~~ **Feito** para os LEDs. Ventoinha fica fora por segurança térmica (ver "Modelo de permissões").
8. **PQ:** trocar perfil exige reiniciar o HWC/reboot e contornar o `init` que força `pq_ui.json`. Fora do alcance de um app.
9. ~~Corrigir `libfocus/README.md` e `MAP.md`~~ **Feito**.
10. ~~Polimento~~ **Feito**: Diagnóstico em linhas, ícones e resumos no menu, textos de ajuda e de tela revistos. Pendente só o que depende de ver na projeção.
11. O atalho "Restaurar padrão de fábrica" da TXCZ gravava `"0"` no id 50. Se algum dia o app gravar o id 50, repetir isso no "Restaurar".
