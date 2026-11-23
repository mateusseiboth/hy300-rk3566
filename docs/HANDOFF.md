# Handoff — estado do projeto (2026-11-22)

Documento para outro agente/pessoa continuar de onde paramos. Leia também `README.md`,
`reverse-engineering/MAP.md` e `android/bootlog/README.md`.

## Regras do dono do projeto

- **NUNCA** colocar `Co-Authored-By` ou qualquer atribuição de IA em commits/PRs (regra global).
- Repositórios são **públicos**: nada de binários proprietários, nem serial/MAC/IP/SSID do aparelho.
- Fazer backup antes de mexer em partições; preferir mudanças reversíveis.
- O usuário não vai abrir o aparelho (sem console serial). Testes de kernel serão feitos pela
  partição `recovery` (ver abaixo).

## Acesso ao aparelho

- `adb connect 20.0.0.190:5555`, depois `adb root`, esperar 3 s e reconectar. Após qualquer reboot
  é preciso rodar `adb root` de novo. O Wi-Fi (AIC8800) às vezes não volta depois do reboot:
  basta tirar da tomada e ligar de novo.
- `adb disable-verity` já foi aplicado. As alterações em /system, /product e /vendor ficam num
  overlay em `/mnt/scratch/overlay/...`. Depois de cada boot, rodar `adb remount` para escrever.
- SELinux está em permissive. A única porta USB é USB-A host, então adb é só por Wi-Fi.

## Arquivos locais (fora dos repositórios)

| Caminho | Conteúdo |
|---|---|
| `~/hy300-backup/` | backup de fábrica das partições (boot, recovery, super.img.gz, dtbo, misc…) + SHA256SUMS |
| `~/hy300-backup/estado-20261122/` | backup incremental do estado de 22/11 (`scripts/backup-state.sh`): partições que mudaram (boot com a splash, cust, metadata), overlay do remount, props persistentes, estado do sistema e apps de usuário com dados. Contém senhas de Wi-Fi: nunca vai para o repo |
| `~/hy300-backup/recovery-gravadas.txt` | hashes das imagens que o `flash-test-recovery.sh` já gravou na recovery |
| `~/hy300-work/` | material bruto: jadx, system/vendor extraídos, kernel/ (norms, dmesg bruto), tools/dtc (dtc 1.8.1 compilado) |
| `~/hy300-work/toolchain/` | Linaro GCC 6.3.1 2017.05 (cópia da Rockchip no GitHub, `rockchip-android/gcc-linaro-6.3.1-2017.05-x86_64_aarch64-linux-gnu`), idêntica à do kernel de fábrica |
| `~/hy300-work/marco0/recovery-marco0.img` | recovery de fábrica com `hy300.test=marco0` no cmdline (18 bytes diferentes), pronta para o teste do marco 0 |
| `~/hy300-work/display-antes-1024x600.txt` | snapshot de props de display antes do teste de 1024×600 (antigo) |

## Estado atual do aparelho

- Debloat feito: `scripts/debloat-packages.txt`. txbox, launcher TXCZ e Adups foram apagados do
  sistema (`scripts/remove-txcz-system-apps.sh`).
- Launcher: Projectivy, instalado pela Aurora. `android.software.leanback` declarado.
  A Play Store de celular para de funcionar com isso, então o Aurora é usado no lugar.
- Splash do U-Boot com a capivara gravado na partição `boot` (`docs/splash.md`).
- Animação de boot com logcat ao vivo (`android/bootlog`) instalada e funcionando.
- Keystone **aprovado pelo usuário** (ajustado por ele no app novo; conferido em 22/11 depois de cada reboot):
  modo teto frontal (`persist.txcz.install.model=2`), `persist.txcz.trapezoid.zoom=100`, cantos
  `persist.sys.keystone.lt=1135,-720 lb=1280,720 rt=-1170,-720 rb=-1280,720`
  (`*.init.xy`: `lt 1280,-720 lb 1280,720 rt -1280,-720 rb -1280,720`). Antes de qualquer teste que mexa em keystone,
  salvar `getprop | grep -E 'keystone|txcz'` e restaurar exatamente estes valores (com `persist.sys.keystone.update=1`).
- App de configurações novo (`io.github.hy300.settings`) instalado como **priv-app** (overlay do /system) com atualização em /data;
  `TxczSetting` (`com.android.tv.settings`) **desativado** com `pm disable`; overlay do TvSettings (sabor TwoPanel) em `/product/overlay`;
  `persist.txcz.tt.enable=0`; atalho F12 ligado. Como reverter: `android/hy300-settings/README.md`, seção "Compilar e instalar".
- Painel físico é 1024×600, mas o HWC ignora `persist.vendor.framebuffer.main`. O teste de
  renderizar em 1024×600 foi revertido (`docs/debloat.md`).
- **Media Center da Rockchip (`com.rockchips.mediacenter`) e toofifi (`com.android.toofifi`, espelhamento da TXCZ)
  removidos** pelo overlay (`scripts/remove-mediacenter-toofifi.sh`, reverter com `restore-mediacenter-toofifi.sh`).
  Os dois rodavam com `android.uid.system`; o Media Center tinha INSTALL/DELETE_PACKAGES, MASTER_CLEAR, READ_LOGS, DLNA e subia no boot.
  No lugar: VLC 3.7.1 armeabi-v7a (site oficial, SHA-256 e assinatura VideoLAN conferidos) e AirScreen (instalado pelo usuário pela Aurora;
  AirPlay, Google Cast e DLNA). O Miracast de fábrica se perdeu: receptor Miracast exige privilégio de sistema. O usuário aceitou.

## Frentes em andamento

### 1. App de configurações novo — `android/hy300-settings/`

Commitado (o README do app tem a tabela de estado com [testado]/[não testado] e os TODOs). Estado em 22/11:

- **"Configurações do Android" traziam a tela da TXCZ de volta.** Causa: `android.settings.SETTINGS` só era tratada por
  `com.android.tv.settings/com.shzhtxcz.txbox.MainActivity` (TxczSetting); o TvSettings real `com.android.tv.set/.MainSettings` não declara a ação.
  O Projectivy usa essa ação. Correção: o app trata a ação e repassa para o `MainSettings`, e o TxczSetting foi desativado
  (`system/disable-txcz-settings.sh`, reversível). Nada que ele fazia no boot é necessário para keystone ou fonte.
- **TvSettings "pobre"**: o build usa o sabor "Classic", enxugado pela TXCZ. Um overlay estático (`tvsettings-overlay`) troca para "TwoPanel"
  (AOSP 12/LineageOS): voltaram Privacidade, Ecrã e som, Armazenamento, Proteção de ecrã, Poupança de energia, Acessibilidade e Reiniciar.
  O sabor "X" fecha o TvSettings (bug da Rockchip no `NetworkFragment`).
- Item "Projetor" no menu principal do TvSettings: funcionando (app de sistema + ação `com.android.tv.set.SOUND`).
- Keystone automático com estado próprio (SharedPreferences), desligado; o serviço subia no boot por causa de `persist.txcz.tt.enable=1`.
- Vendor storage id 50: o leitor é o U-Boot (gira o logo de boot 180° nos modos de teto). O app não grava o id 50 (TODO 6 do README).
- Falta o usuário validar na projeção: foco, BCSH, modos de instalação, 4:3, trapézio, LEDs, segurar a tecla no foco e o automático.
- Build: JDK 17 do sistema + Android SDK em `~/Android/Sdk` (commandline-tools, platform 35, build-tools 35.0.0).
  A chave debug mudou em relação ao primeiro APK (o primeiro foi desinstalado e reinstalado).

### 2. Kernel — `git@github.com:mateusseiboth/kernel-hy300-rk3566.git`

- O repositório é um fork do `rockchip-linux/kernel` com todos os branches. Clone local em
  `~/hy300-handoff/kernel-hy300-rk3566` (branches `develop-4.19` e `hy300`; o `develop-6.1` é buscado sob demanda).
- Commit `46d22e0` no branch `hy300`: `arch/arm64/boot/dts/rockchip/rk3566-hy300.dts`
  (inclui `rk3566-box-demo-v10.dts`) + `rk3566-hy300-overrides.dtsi` (gerado), já no Makefile.
  O DTB compilado é **estruturalmente idêntico** ao de fábrica (verificado com `tools/dtnorm.py`).
- Pipeline para regenerar/validar:
  ```
  cpp -nostdinc -I include -I arch/arm64/boot/dts -I arch/arm64/boot/dts/rockchip -undef -D__DTS__ \
      -x assembler-with-cpp <dts> -o x.pp.dts && ~/hy300-work/tools/dtc/dtc -q -@ -I dts -O dtb -o x.dtb x.pp.dts
  python dtnorm.py x.dtb > x.norm   # (precisa de pip fdt; venv em /tmp foi temporário)
  python3 dtoverride.py base.norm alvo.norm > overrides.dtsi
  ```
- **O 4.19 foi abandonado (decisão de 22/11).** O kernel de fábrica vem do SDK **Android 12** da Rockchip
  (4.19.232 com `DMABUF_HEAPS`, `MPP_VDPP`, `RGA_ASYNC`, RK628) mais drivers da TXCZ (AIC8800, SeekWave, QMI8658).
  Essa variante não é pública: o `develop-4.19` (congelado em 2022-08) e as cópias achadas no GitHub são do SDK Linux.
  Compilado dali com a config de fábrica, somem 25 opções, e com `MODVERSIONS=y` os módulos do vendor (Wi-Fi incluso)
  não carregariam. Como o objetivo é o Android novo, o marco 0 valida só o fluxo, usando a própria `Image` de fábrica.
- **U-Boot de fábrica** (`U-Boot 2017.09-gf21494d #txcz`, strings do `uboot.img`): tem código de `vendor bootconfig`
  (header v4), então deve aceitar boot.img v3/v4 e `vendor_boot` sem troca. Decide a recovery por cmd/env/tecla/**misc**/usb.
  Fastboot existe (USB e UDP), mas sem porta OTG e sem rede cabeada não serve. U-Boot novo (boot pela USB-A) só em falha
  catastrófica, depois de todo teste possível, e só é gravável enquanto o aparelho ainda boota por algum caminho.
- **Marco 0 (validar o fluxo de teste): pronto, falta executar com o usuário presente** (ele precisa do controle):
  - `tools/mkboot.py` monta/desmonta boot.img v2; `tests/test_mkboot.py` (12 testes, `python3 -m unittest discover -s tests`)
    remonta `boot.img` e `recovery.img` de fábrica idênticos byte a byte. As imagens não têm footer AVB.
  - Teste: `scripts/flash-test-recovery.sh ~/hy300-work/marco0/recovery-marco0.img` → `adb reboot recovery` → o usuário
    escolhe "Reboot system now" (reboot quente, sem tirar da tomada) → `scripts/check-test-boot.sh hy300.test=marco0`
    (marca no pstore, argumentos da recovery no `/cache/recovery/last_log`, hash da `misc`) →
    `scripts/flash-test-recovery.sh ~/hy300-backup/recovery.img` para voltar.
  - A recovery de fábrica roda inteira nesse teste e limpa a `misc` ao sair: sem risco de loop.
- **Marco 0 e marco 1: feitos em 22/11.** O 6.1 sobe no aparelho pelo slot `recovery` com o
  próprio DT embutido no kernel (o U-Boot de fábrica não funciona com o DT do 6.1 no resource e
  recebe o de fábrica), relatório no pstore e reboot quente sozinho. Resultado, lições (sinal da
  ventoinha, watchdog que desliga) em `docs/kernel-6.1.md`. **A tela funciona no 6.1** (o painel
  precisa de uma configuração SPI em bit-bang que veio do kernel de fábrica). A recovery de
  fábrica foi regravada depois do teste.
- **Wi-Fi no 6.1 (22/11, testado e funcionando: telnet no 6.1 pela rede):** driver AIC8800D80 (SDK AICSemi V3.0 2023_1107, cópia GPL da Radxa) em `drivers/net/wireless/aic8800` do `hy300-6.1`; `WIFI=1 kernel/build-marco1.sh` gera a recovery com `hy300.wifi=1`, que conecta com IP fixo e abre `telnetd` na porta 23 por até 15 min. Firmware sai do `vendor.img` e a rede de `~/hy300-work/wifi/credenciais.conf` (fora do repo). Roteiro em `docs/kernel-6.1.md`, "Wi-Fi no 6.1".
- **Alpine de recuperação (22/11, não testado no aparelho):** repositório [`hy300-alpine`](https://github.com/mateusseiboth/hy300-alpine): kernel `hy300-6.1` (`Image.gz`) e núcleo de resgate na `boot`/`recovery`, Alpine completo na partição `backup`, SSH só por chave, Wi-Fi de casa ou ponto de acesso `HY300-6bot-recovery`, kexec e autoboot para o Android pelo registrador; gravação e roteiro de teste no README de lá.
- **Kernel na base Android (22/11, build pronto, falta bootar no aparelho):** branch `hy300-ack-6.1` (ACK `android14-6.1` + BSP Rockchip do Lineage-Rockchip `lineage-23.2`, 6.1.172), todos os patches do `hy300-6.1` portados, clang 20, 0 diferenças contra `u/android-6.1`; `kernel/build-marco1.sh` agora compila essa base por padrão (`KBASE=bsp` para o `hy300-6.1`), imagem em `~/hy300-work/marco1-ack/recovery-marco1.img`. Ver `docs/kernel-6.1.md`, "Base Android". **Bootou; o Wi-Fi falhou duas vezes** (respostas do AIC8800 cada vez mais lentas até estourar; o chip fica travado até tirar da tomada): diagnóstico, hipóteses e a imagem de teste com polling e religamento do `WL_REG_ON` em `docs/kernel-6.1.md`, "Falha do Wi-Fi no kernel ACK". Na mesma branch: reinício sozinho em panic/travamento (watchdog do SoC passa a reiniciar em vez de desligar) e DVFS de CPU (até 1,8 GHz), DDR e GPU com throttling, ainda sem teste no aparelho.
- **Marco 1 (histórico):** branch `hy300-6.1` do kernel (6.1.172) com o DT do HY300 portado, imagem em `~/hy300-work/marco1/recovery-marco1.img` (`kernel/build-marco1.sh`). Entrar no slot de teste com `scripts/reboot-to-test-slot.sh` (só o registrador de reboot-mode, sem BCB: tirar da tomada sempre volta ao Android), nunca com `adb reboot recovery`. Initramfs de teste que limpa a `misc` (só se tiver
  `boot-recovery`), registra um relatório no pstore e reinicia sozinho em ~20 s. Detalhes em `docs/kernel-6.1.md`.
- **Marco 2:** vendor 64 bits + LineageOS (o branch mais novo disponível; Android 17 quando o Lineage chegar lá).
  Base possível: GloDroid (mainline, Mesa/Panfrost, já roda em placas RK3566) ou árvores LineageOS de outros RK356x (BSP + blobs 64 bits).
  Trabalho próprio: keystone (hoje no SurfaceFlinger com `librkgfx_dc.so`, fechada e 32 bits; reimplementar como passo final de
  composição), HDMI-in (RK628), driver do motor de foco (reescrito a partir da RE, **mantendo `/sys/class/motor_cc`** para o app
  continuar funcionando), Wi-Fi AIC8800 (driver aberto, portar), QMI8658.
  Risco: sem fastboot por USB, a `super` nova terá de ser gravada de dentro do aparelho; ela só é tocada quando o sistema novo
  já bootar pelo slot `recovery`.
- **LineageOS 24.0 (22/11, só planejamento):** inventário, decisões (Lineage TV, FCM 8 para o 6.1, kernel Rockchip ACK 6.1.172 recomendado, header v2 com resource de fábrica e `Image.gz`, Panfrost, teste pelo pendrive), riscos e marcos em `docs/lineageos.md`; esqueleto da árvore em `~/android/device-hy300` (GitHub `mateusseiboth/android_device_hy300_rk3566`, branch `lineage-24.0`); `tools/kconfig_check.py` mede o `.config` contra o `kernel/configs`.

- **Partições desde 22/11/2026 ~20h: `boot` = Alpine (repo `hy300-alpine`, imagem `boot-alpine.img`
  16f66e67…), `recovery` = Android de fábrica com `androidboot.init_fatal_panic=true`
  (`android-recovery.img` cb460d08…, kernel/ramdisk/resource iguais ao boot do backup
  `estado-20261122`), `backup` = rootfs completo do Alpine.** Ligar/tirar da tomada cai no Alpine,
  que segue sozinho para o Android em 5 s. Do PC: `hy300-alpine/scripts/reboot-to-alpine.sh`
  (marca de uso único em 0x10000 da `misc`) leva ao Alpine e o mantém no ar com SSH; no Alpine,
  `hy300-android` volta ao Android. Provado no aparelho: 3 boots, ida e volta, panic → reinício no
  Alpine. Instalado no Android (overlay): `hy300-clear-bcb` (apaga `boot-recovery` da `misc`).
  **Limitação conhecida:** o reset de hardware do watchdog (travamento sem panic) ainda DESLIGA o
  aparelho mesmo com o `CRU_GLB_RST_CON` em 0x113; volta pelo botão de energia. O pré-timeout
  (panic aos 30 s) cobre os travamentos em que o kernel ainda roda. O ajuste do CRU não sobrevive
  ao reboot (chega 0x103), então cada kernel precisa aplicá-lo.

### 3. Pendências menores

- `bootlog` nativo em C++ (log desde ~6 s, boot mais rápido): ver o TODO em `android/bootlog/README.md`.
- Áudio do HDMI-in: falta o serviço `com.rockchip.rkhdmiinaudio` (`docs/hdmi-audio.md`).
- Renderização nativa 1024×600: investigar `persist.vendor.resolution.*` no HWC.
- Telemetria bloqueada em 22/11 (`scripts/block-telemetry.sh`, reverter com `unblock-telemetry.sh`): hosts + iptables para o IP fixo. Conferir no próximo boot se o `.rc` reaplica a regra (`iptables -S OUTPUT | grep 47.113`).
