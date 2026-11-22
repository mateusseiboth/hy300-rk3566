# Foco: motor `motor_cc` e `libfocusvahysd.so`

## Resumo

| Item | Situação no HY300 |
|---|---|
| Motor de foco | driver de kernel embutido (`usb-cam-gpio` / `rk_motor`), nó `/sys/class/motor_cc/motor_cc/motor` |
| Foco manual pelo controle | tratado **dentro do kernel** pelo driver do controle IR (`rk pwm remotectl`), que usa `motor_status` |
| Foco manual pelo userspace | escrever `user_cw` / `user_ccw` (1 passo) e `stop` em `.../motor`; o fim de curso aparece em `.../hd_camera_on` |
| Autofoco (câmera) | `libfocusvahysd.so` é a lib JNI do app `com.hysd.txczscreen`, **que não existe no ROM**. Nada carrega a lib. |
| "Autofoco" do TxczSetting | só aciona o app ausente (ver `../txcz-settings/README.md` §5) |

## 1. Driver de kernel

DT (`device-tree/rk3566-hy300-txcz.dts`):
```
rk_motor { compatible = "rk_motor", "usb-cam-gpio"; };
```
Sem propriedades de GPIO no nó: o driver usa GPIOs fixos no código (e `hd-cam-gpios` / `ir-cam-gpios`, se houver).

Símbolos (`/proc/kallsyms`): `motor_cw`, `motor_ccw`, `motor_run` (kthread), `motor_timer` (hrtimer),
`motor_timer_interrupt`, `motor_store`, `motor_show`, `dev_attr_motor`, `motor_status`.

sysfs (`/sys/devices/virtual/motor_cc/motor_cc/`):

| Nó | Permissão | Conteúdo |
|---|---|---|
| `motor` | `0777 system:system` (feito pelo `init.rk356x.rc` em `sys.boot_completed=1`) | escrita = comando; leitura = `0` |
| `hd_camera_on` | `0644 root` | leitura `0`/`1`. O txczbox usa como "fim de curso atingido" (`"1"`) |

Comandos aceitos por `motor_store` (strings do kernel em `boot.img`; parser exato não desmontado):
```
user_cw   user_ccw            # 1 passo em cada sentido (uso confirmado no app txczbox)
stop                          # parar (uso confirmado no txczbox e no framework)
aacw  aaccw  aastop           # variantes com prefixo "aa" (logs "in ir_camera_on_store =cw/ccw/stop")
aacw_end  aaccw_end           # ir até o fim de curso
```
O driver do controle (`rk pwm remotectl v2.0`) loga `hason rc timer/getdata/seq motor_status=%d`. Isso indica que as teclas de foco
do controle IR acionam o motor direto no kernel, sem passar pelo Android: nenhuma tecla de foco aparece no
`fdd70030_pwm.kl`.

### Como os apps TXCZ usam

- **`com.shzhtxcz.txbox`** (`/system/app/txczbox`, já removido pelo debloat), `utils/SettingsUtils`:
  - caminhos configuráveis: `persist.txcz.motor.path` (padrão `sys/class/motor_cc/motor_cc/motor`) e
    `persist.txcz.motor.limit` (padrão `sys/class/motor_cc/motor_cc/hd_camera_on`);
  - `motorCwOne()` → escreve `user_cw`; `motorCcwOne()` → `user_ccw`;
  - `motorCwUntil()/motorCcwUntil()`: thread que repete o passo **a cada 60 ms** enquanto o estado não mudar,
    lendo `hd_camera_on` (`"1"` = chegou no limite);
  - `motorStop()` → escreve `stop`.
- **`services.jar` `MaDaDialog`** (teclas KEYCODE 137/138 = F7/F8): mostra um diálogo e, a cada 60 ms, escreve `cw`/`ccw`
  em `sys/class/motor_cc/motor_cc/motoraa`. Ao soltar a tecla escreve `stop`. **Esse nó não existe neste kernel**
  (só existe `motor`), então esse caminho não funciona no HY300. F7/F8 também não estão no layout do controle IR.

### Reproduzir pela shell (NÃO executado)

```sh
M=/sys/class/motor_cc/motor_cc
echo user_cw  > $M/motor      # 1 passo (repita a cada ~60 ms para girar continuamente)
echo user_ccw > $M/motor
echo stop     > $M/motor
cat $M/hd_camera_on           # 1 = fim de curso
```
Para o app novo: rodar um loop de 60 ms enquanto o botão estiver pressionado e parar quando `hd_camera_on == 1`.
Como `motor` é 0777, um app comum consegue escrever, se o SELinux permitir (`sysfs` genérico: provavelmente
não permite para `untrusted_app`; um app `platform`/uid system consegue).

## 2. `libfocusvahysd.so`

- `/system/lib/libfocusvahysd.so` (ARM32, 11,5 MB) e `/system/lib64/libfocusvahysd.so` (ARM64, 13 MB). NDK r22b,
  stripped. Depende só de `libandroid, liblog, libc, libz, libdl, libm`. Embute OpenCV inteiro e o SDK de
  câmera USB Sonix (`SonixCam_*`, `XU_*` = UVC Extension Units).
- **Ninguém carrega a lib no ROM**: as únicas referências na `super.img` são os próprios arquivos e o diretório.
  Os nomes JNI mostram que ela pertence ao app `com.hysd.txczscreen` (classe `com.hysd.vafocus.HYSDVAF2`,
  callbacks em `com.hysd.client.MotorAPIs2`), que não está instalado.

Exports JNI (54), agrupados:

| Grupo | Funções `Java_com_hysd_vafocus_HYSDVAF2_*` |
|---|---|
| Init/licença | `hysdinit`, `prepare`, `givepath`, `savepath`, `keydatapath`, `setmac`, `getsoftnumber`, `getcameranumber` |
| Câmera (UVC/Sonix) | `camcontrol`, `camdata`, `camreset`, `s0cam`, `s1cam`, `s2cam`, `releaseCam`, `ForceReleaseCam`, `getcamver`, `gcamver`, `getlight`, `setpose`, `transpic` |
| Autofoco | `AutoFocusInit2`, `AutoFocusRun`, `AutoFocusRun2`, `FocusEvaluate`, `computefocusvalue`, `getfocusvalue` |
| Motor | `initmotor(MotorAPIs2)`, `motorcontrol`, `setmotorname`, `setmotorslow`, `setmotortype`, `stopmotorthread` |
| Keystone por câmera/ToF | `afkeystone`, `afkeystone3`, `quickkeystone`, `keystone2plus`, `keystone3plus`, `keystone4plus`, `keystone2tof`, `getkeypoint`, `savekeypoint`, `compute` |
| Calibração (Tsai) | `calib3`, `calibtof`, `tofinit`, `gettofdata`, `checkdata`, `checkdataeffective`, `checkemmcdata`, `getsavedemmcdata`, `amlogicreademmc`, `ALTEST`, `sfk` |

Interface com o hardware (strings):
- câmera: `/dev/video%d` (V4L2/UVC), `/dev/i2c-%d`, comandos XU para o sensor Sonix;
- motor: callbacks Java `motorforward/motorback/motorstop/getmotorstatus` (o app Java é quem escreve no
  sysfs) ou `/dev/hi_motor` (placas HiSilicon);
- dados: `/data/focus/` (`detect.yuv`, `detect1.yuv`, `wifimac`), `persist.keystone.datapath=/cust` (gravado pelo
  Sensorservice). A partição `/cust` (`init.rk356x.rc` faz `chown system system /cust/hybin`) guarda a calibração;
- `setmac` + `/data/focus/wifimac` sugerem licença amarrada ao MAC do Wi-Fi;
- `http://%s`: aparentemente só do OpenCV/libcurl embutido. Não foi encontrado endpoint fixo.

Conclusão: implementar autofoco por câmera exigiria o app hysd (proprietário, ausente) ou um algoritmo novo
(V4L2 na câmera USB + varredura do motor maximizando o contraste). O HY300 tem a câmera USB? `/dev/video0..8`
existem, mas parte é do RK628 (HDMI-in) e do ISP. `hd_camera_on` sugere que dá para ligar uma câmera "HD", mas
isso ficou em aberto.
