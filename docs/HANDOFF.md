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
| `~/hy300-backup/` | backup completo das partições (boot, recovery, super.img.gz, dtbo…) + SHA256SUMS |
| `~/hy300-work/` | material bruto: jadx, system/vendor extraídos, kernel/ (norms, dmesg bruto), tools/dtc (dtc 1.8.1 compilado) |
| `~/hy300-work/display-antes-1024x600.txt` | snapshot de props de display antes do teste de 1024×600 (antigo) |

## Estado atual do aparelho

- Debloat feito: `scripts/debloat-packages.txt`. txbox, launcher TXCZ e Adups foram apagados do
  sistema (`scripts/remove-txcz-system-apps.sh`).
- Launcher: Projectivy, instalado pela Aurora. `android.software.leanback` declarado.
  A Play Store de celular para de funcionar com isso, então o Aurora é usado no lugar.
- Splash do U-Boot com a capivara gravado na partição `boot` (`docs/splash.md`).
- Animação de boot com logcat ao vivo (`android/bootlog`) instalada e funcionando.
- Keystone **aprovado pelo usuário**: modo teto frontal (`persist.txcz.install.model=2`),
  `persist.txcz.trapezoid.zoom=100`, cantos
  `lt=1280,-720 lb=1280,720 rt=-1280,-720 rb=-1280,720` (iguais aos `*.init.xy`).
- Painel físico é 1024×600, mas o HWC ignora `persist.vendor.framebuffer.main`. O teste de
  renderizar em 1024×600 foi revertido (`docs/debloat.md`).

## Frentes em andamento

### 1. App de configurações novo — `android/hy300-settings/`

Um worker estava construindo o app (Gradle, leanback-preference, setprop via `Runtime.exec`
por causa do SELinux permissive). O usuário já viu telas funcionando. **O código ainda não foi
commitado.** Revisar, conferir o `.gitignore` (sem `build/` nem APK) e commitar. O README do app
(escrito pelo worker) lista o que funciona e os TODOs. A especificação está em
`reverse-engineering/MAP.md`.

### 2. Kernel — `git@github.com:mateusseiboth/kernel-hy300-rk3566.git`

- O repositório é um fork do `rockchip-linux/kernel` com todos os branches. Clone local em
  `~/kernel-hy300-rk3566` (só o branch `develop-4.19`, mais o branch nosso `hy300`).
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
- **Próximos passos do marco 0** (kernel 4.19 reproduzindo o de fábrica, só para validar o fluxo):
  1. Toolchain: o de fábrica usou **Linaro GCC 6.3.1 2017.05** (aarch64-linux-gnu).
     `releases.linaro.org` foi desativado, e o `snapshots.linaro.org`/S3 devolvem HTML ou 403.
     Achar um espelho (ex.: prebuilts do SDK da Rockchip no GitHub) ou usar outro GCC aarch64
     (depois verificar o vermagic dos módulos do vendor: `kernel/vendor-modules.txt`).
  2. `arch/arm64/configs/rk3566_hy300_defconfig` a partir de `hy300-rk3566/kernel/config-4.19.232-txcz`
     (`make ARCH=arm64 savedefconfig`, que precisa do cross-compiler). Ligar `CONFIG_KEXEC`.
  3. Script para montar o `boot.img` (header v2, page 2048): kernel novo + ramdisk de fábrica +
     `second`=resource.img com o DTB. Ver `tools/rk_resource.py` e `tools/make_splash.py`
     (`boot_parts`/`calc_id` sabem calcular o SHA1 do header).
  4. **Slot de teste = partição `recovery`:** gravar a imagem de teste na `recovery`
     (o backup está em `~/hy300-backup/recovery.img`) e rodar `adb reboot recovery`.
     Se travar, tirar da tomada: o boot normal segue pela `boot`. O log fica em
     `/sys/fs/pstore/console-ramoops-0` (ramoops já ativo).
     **ANTES** do primeiro kernel nosso, validar com a recovery de fábrica se o U-Boot grava
     "boot-recovery" na `misc` nesse caminho (risco de loop de boot). Para isso, comparar dumps
     da `misc` antes e depois.
- **Marcos seguintes** (decididos com o usuário): marco 1 = BSP `develop-6.1`/`6.6` bootando com
  o DT portado. Marco 2 = userspace novo (port do LineageOS com vendor 64 bits; o alvo é
  Android 17). Riscos: keystone (`librkgfx_dc.so`, proprietária e 32 bits), PQ (`libpq`) e
  HAL do RK628. U-Boot: só refazer se for necessário (sem SD, sem serial, MaskROM só pela OTG).

### 3. Pendências menores

- `bootlog` nativo em C++ (log desde ~6 s, boot mais rápido): ver o TODO em `android/bootlog/README.md`.
- Áudio do HDMI-in: falta o serviço `com.rockchip.rkhdmiinaudio` (`docs/hdmi-audio.md`).
- Renderização nativa 1024×600: investigar `persist.vendor.resolution.*` no HWC.
- Bloquear domínios de telemetria no hosts (`reverse-engineering/telemetria/README.md`).
- `com.android.toofifi` (espelhamento): a parte de rede não foi analisada.
