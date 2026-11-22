# Telemetria, OTA e instalação remota de apps (segurança)

Busca em todos os APKs TXCZ do ROM (e strings de libs). Domínios e IPs encontrados:

| Destino | Quem usa | O quê |
|---|---|---|
| `http://shzhtxcz.com/videoadmin/...` (**HTTP sem TLS**; domínio trocável por `persist.txcz.desttop.domain`) | launcher `com.shzhtxcz.txbox.launcher` | `GET videoadmin/layout/div/allDivPagejm?isEnc=1&dtVersion=&dtId=` (layout da Home vindo do servidor). Cabeçalhos em toda requisição: `serial`, `model`, `lanMac`, `wifiMac`, `versionCode` |
| `http://www.mfcopenapi.info/open/api/playlist/videos/v1` | launcher | playlists de vídeo |
| `http://shzhtxcz.com/videoadmin/...` | `com.shzhtxcz.txbox` (`/system/app/txczbox`) | ver abaixo (registro, heartbeat, lista de APKs para instalar, logs) |
| `http://47.113.90.237:8081/seo/...` (IP Alibaba Cloud) | `com.shzhtxcz.txbox` | `ad/serialIsCheck`, `ad/ssdd`, `txu/ppp`, `txu/nnapk`, `modelapk/create`, `dhy/mkk` |
| `http://47.113.90.237/lanzou/link?url=%s&pwd=%s` | `com.shzhtxcz.txbox` (`ApkUtils.getRealUrl`) | resolve links do Lanzou Cloud (hospedagem chinesa de arquivos) para baixar APKs |
| `https://fota5p.adups.com` / `https://fota5p.adups.cn` | `com.txcz.update` (`/product/app/FotaUpdate`, Adups FOTA) | `/otainter-5.0/fota5/{detectSchedule,fullDetectSchedule,submitReport,fcmReport}.do` |
| `https://fruet.adups.com/euft/{redsercon,repsta}` | `com.txcz.update` | relatórios e estatísticas (strings ofuscadas como `char[]`) |

## `com.shzhtxcz.txbox` (`/system/app/txczbox/txczbox.apk`) — agente remoto

> No aparelho atual ele já foi removido para o usuário 0 pelo debloat (`~/hy300-backup/debloat-removed.txt`), mas continua na
> imagem `system`. Num ROM limpo ele roda como **uid system** (`sharedUserId=android.uid.system`).

- Permissões: `INSTALL_PACKAGES`, `DELETE_PACKAGES`, `REQUEST_INSTALL_PACKAGES`, `PACKAGE_USAGE_STATS`, `READ_LOGS`,
  `GET_TASKS`, `SET_ACTIVITY_WATCHER`, `WRITE_SECURE_SETTINGS`, `REBOOT`, `SYSTEM_ALERT_WINDOW`...
- Retrofit (`b.d.b.p`), base `http://shzhtxcz.com/`. Cabeçalhos: `serial`, `model`, `opened` (= `persist.sys.txcz.adopen`),
  `lanMac`, `wifiMac`, `versionCode`. O OkHttp usa `TrustAllCerts` + `TrustAllHostnameVerifier` (TLS sem validação).
- Endpoints: `tv/registry` (POST serial, MACs, modelo), `tv/heartbeat`, `apk/all?isAct=1` (lista de APKs),
  `sysPop/getByModel` (pop-ups), `api/modelExtendConfig/getByModel`, `api/appScreenActivate/{all,saveActLog}`,
  `tvMake/creatTvMake`, `tv/upload/problem1` e `tv/upload/problemdate` (envio de `logcat`/`dmesg`, `LogModel`),
  `tv/yaokong/getyaokongurl` (firmware do controle), `api/txDict/getAll`.
- **Instalação/desinstalação silenciosa**: `ApkUtils.downThenInstall(url, pkg, versionCode, ...)` baixa o APK (direto ou
  via Lanzou), instala com `pm install -i <pacote-system> -r <apk>` (ou `PackageInstaller`) e pode desinstalar antes.
  Disparado pela lista do servidor (`AppOperateType.INSTALL`) e por `PreInstallIntentService`.
- Também coleta inventário de apps (`CollectApkInfo`: pacote, versão, instalador, caminho) e consulta qual app está em primeiro plano (`getRunningTasks`/UsageStats em `PqUtils`, `DuoheyiUtils` e `MiepinJiHuoActionDialog`).
- `ExKeyIntentService`: teclas F1..F4 do controle abrem apps configurados **pelo servidor** (`ModelConfig`).
- Motor de foco: `utils/SettingsUtils` (ver `../libfocus/README.md`).

## `com.txcz.update` (FotaUpdate, Adups)

- `/product/app/FotaUpdate/FotaUpdate.apk`; props `ro.fota.*` no `build.prop` (`ro.fota.oem=txcz_RK356X_12.0`,
  `ro.fota.device=rk3566_sgo`, `ro.fota.id=mac`, `ro.fota.type=box`). Overlay `com.txcz.update.overlay`.
- Envia `androidId`, `mac`, `imei1/2`, `esn`, `mid`, `fcmId`, `swFingerprint`, resolução, versão e operadora.
- Baixa `update.zip` para `/data/ota_package/`, `/data/media/0/txczfota/` ou `/cache` e reinicia em recovery
  (`RECOVERY`, `REBOOT`). Também aceita `LocalSdUpdate.zip`.
- O TxczSetting abre `com.adups.fota/.GoogleOtaClient` ou `com.txcz.update/.GoogleOtaClient` pelo botão "Atualizar".
- No `packages.txt` do backup, `com.txcz.update` estava instalado. No `pm list packages` atual ele não aparece (provavelmente desativado).

## `com.android.toofifi` (`/odm/bundled_persist-app/TXCZTVApp_FTZX_V3.2.3.0_...apk`, 78 MB)

App de TV/conteúdo instalado como "persist" a partir do `odm`. Não foi analisado (fora do escopo). `persist.zeasn.customer=TXCZ`
e `persist.zeasn.devicetype=RK3566_Projector` indicam integração com a Zeasn (loja/OS de TV). **Pendente.**

## TxczSetting / launcher

- TxczSetting não faz rede. O launcher só busca layout e playlists (com serial e MACs nos cabeçalhos, em HTTP puro).
  Tem `INSTALL_PACKAGES` no manifest, mas o código só abre e desinstala apps pela UI.
- Componentes exportados perigosos no TxczSetting (`VsReceiver`, `com.vendor.store.MyService`): escrita arbitrária
  no *vendor storage* por qualquer app (ver `../txcz-settings/README.md` §9).

## Recomendações para o app novo / ROM

- Manter `com.shzhtxcz.txbox` removido. Considerar remover `com.txcz.update` (Adups) e bloquear `shzhtxcz.com`,
  `47.113.90.237`, `*.adups.com`, `*.adups.cn`, `mfcopenapi.info`.
- Não depender de `BridgeService`, `VsReceiver` nem `MyService` do app TXCZ. Escrever as props direto (o app novo precisa ser
  uid system/platform-signed ou ter as props liberadas no SELinux).
