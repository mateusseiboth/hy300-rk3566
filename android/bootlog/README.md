# bootlog — animação de boot com log ao vivo

Substitui a animação de boot por um terminal que mostra o **`logcat -b all` real**, ao vivo
(kernel, main, system, events), com cores por prioridade, tempo desde o boot, etapa atual,
barra de progresso guiada pelos eventos `boot_progress_*` e um logo no canto.

## Como funciona

1. `files/bootanim.rc` sobrescreve o serviço `bootanim` (iniciado pelo SurfaceFlinger) para rodar
   `files/bootlog.sh` como root.
2. O script inicia o `bootanimation` nativo com um `bootanimation.zip` de **1 quadro** (o logo),
   cobrindo o intervalo em que Java ainda não pode rodar.
3. Espera `apexd.status=ready` + `/data/system/environ/classpath` e **carrega esse arquivo**:
   o serviço nasce antes do `post-fs-data` e herda um ambiente **sem `BOOTCLASSPATH`** (no
   Android 12 ele é gerado pelo `derive_classpath`). Sem isso, `JNI_CreateJavaVM failed`.
4. Sobe `app_process -Xdeny-art-apex-data-files … com.hy300.bootlog.Main`, que cria uma camada
   `SurfaceControl` no topo e desenha com `Canvas`. No 1º quadro cria `/dev/.bootlog_ready` e o
   script mata o nativo.
5. Termina quando vê `boot_progress_enable_screen` no log ou quando `service.bootanim.exit` muda
   de 0→1 (nesta ROM ela pode já começar em 1). Limite de segurança: 180 s (relógio monotônico).
6. Se a VM não subir, tenta de novo; se o boot acabar antes, sai — nunca segura o boot.

### Armadilhas encontradas (app_process fora do zygote)

| Sintoma | Causa | Solução |
|---|---|---|
| `NullPointerException` em `Typeface.create` / abort `gDefaultTypeface == nullptr` | mapa de fontes é carregado pelo zygote | `Typeface.loadPreinstalledSystemFontMap()` + `setDefault()` via reflexão |
| `JNI_CreateJavaVM failed` no boot | ambiente sem `BOOTCLASSPATH`/`DEX2OATBOOTCLASSPATH`/`SYSTEMSERVERCLASSPATH` | `export` do `/data/system/environ/classpath` |
| ART indisponível antes de ~10 s | APEX `com.android.art` só ativa após `/data` | esperar `apexd.status=ready` |
| terminava sozinho no meio do boot | `System.currentTimeMillis()` salta quando a hora é acertada | `SystemClock.uptimeMillis()` |
| saía na hora | `service.bootanim.exit` já em `1` | só aceitar transição 0→1 / `enable_screen` |

Limitação: o log aparece por volta de 20 s (VM sobe junto com o preload do zygote); antes disso
fica o logo. Uma versão nativa em C++ (`libgui`) eliminaria esse intervalo.

## Uso

```bash
./build.sh          # requer Android SDK (platform android-32 + build-tools)
./install.sh        # requer adb root + disable-verity (overlay do adb remount)
adb reboot
./uninstall.sh      # restaura bootanim.rc e bootanimation.zip originais
```

Testar sem reiniciar (desenha por 15 s por cima da tela):

```bash
adb push out/bootlog.dex /data/local/tmp/
adb shell 'CLASSPATH=/data/local/tmp/bootlog.dex app_process /system/bin com.hy300.bootlog.Main 1280 720 /system/media/bootlog/logo.png --test'
```

Depuração: o script escreve em `/dev/kmsg` → `adb shell dmesg | grep bootlog`.

## TODO: versão nativa (C++)

Objetivo: log desde ~6 s (quando o SurfaceFlinger sobe) e boot ~10–15 s mais rápido, sem a VM
Java disputando CPU com o zygote.

Avaliação (nov/2026):

- Precisa da API **C++ privada** do `libgui` (`SurfaceComposerClient`, `Transaction`, `Surface`).
  O `libgui.so` do aparelho exporta os símbolos (ex.:
  `_ZN7android21SurfaceComposerClient13createSurfaceERKNS_7String8EjjijRKNS_2spINS_7IBinderEEENS_13LayerMetadataEPj`).
- **ABI:** a plataforma usa a libc++ `std::__1`; o NDK usa `std::__ndk1` → compilar com clang do
  NDK mas com `-nostdinc++` + headers da libc++ e de `frameworks/native`, `system/core`
  (libutils/libcutils/liblog), `system/libbase`, `hardware/libhardware` da tag AOSP
  `android-12.1.0_rX` correspondente a `SQ3A.220705.003`, linkando contra as `.so` puxadas do
  aparelho (`libgui`, `libui`, `libutils`, `libbinder`, `libc++`, `liblog`, `libcutils`, `libbase`).
- Texto: sem `Canvas` → fonte bitmap embutida (ou FreeType) desenhando direto no buffer
  (`Surface::lock`/`unlockAndPost`).
- Risco: ABI do `libgui` alterado pela TXCZ/Rockchip → crash. Manter a versão Java como fallback
  no `bootlog.sh`.
- Rust não simplifica: o obstáculo é a API C++ privada, não a linguagem.
- Estimativa: 2–3 h de tentativa e erro.
