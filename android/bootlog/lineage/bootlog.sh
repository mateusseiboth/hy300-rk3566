#!/system/bin/sh
# Animação de boot com log ao vivo, versão do LineageOS 24 do HY300 (a do Android 12 é files/bootlog.sh).
# 0) versão nativa (C++, sem ART): se desenhar o 1º quadro em até 5 s, fica com ela até o fim;
# 1) senão, bootanimation mostra o logo (hy300-bootlog.zip de 1 quadro, ro.product.bootanim.file)
#    até o ART estar pronto;
# 2) bootlog Java (app_process) desenha o logcat ao vivo; no 1º quadro, encerra o bootanimation;
# 3) se a VM não subir, tenta de novo; se nada der certo, fica o bootanimation. Nunca segura o boot.
klog() { echo "bootlog: $*" > /dev/kmsg; }
rm -f /dev/.bootlog_ready

# Tamanho real do display: o modo do conector DRM ligado (no HY300, o painel LVDS 1024x600).
W=1280
H=720
for status in /sys/class/drm/card*-*/status; do
    [ "$(cat "$status" 2>/dev/null)" = "connected" ] || continue
    mode=$(head -n 1 "${status%/status}/modes" 2>/dev/null)
    case "$mode" in
        *x*) W=${mode%%x*}; H=${mode#*x}; H=${H%%[!0-9]*}; break ;;
    esac
done
klog "display ${W}x${H}"

NATIVE=/system_ext/bin/hy300-bootlog-native
LOGO=/product/media/bootlog/logo.png
if [ -x $NATIVE ]; then
    $NATIVE "$W" "$H" $LOGO > /dev/kmsg 2>&1 &
    NP=$!
    n=0
    while kill -0 $NP 2>/dev/null && [ ! -e /dev/.bootlog_ready ] && [ $n -lt 100 ]; do
        sleep 0.05
        n=$((n+1))
    done
    if [ -e /dev/.bootlog_ready ]; then
        klog "nativo desenhando"
        wait $NP; klog "nativo terminou rc=$?"
        rm -f /dev/.bootlog_ready
        exit 0
    fi
    kill $NP 2>/dev/null
    klog "nativo não desenhou, seguindo com a versão Java"
fi

/system/bin/bootanimation &
BA=$!
klog "bootanimation pid=$BA"

# O serviço nasce antes do post-fs-data e herda um ambiente SEM BOOTCLASSPATH etc. (gerados
# pelo derive_classpath depois que os APEX ativam). Espera o APEX do ART e o arquivo de exports.
CP=/data/system/environ/classpath
until [ "$(getprop apexd.status)" = "ready" ] && [ -e /apex/com.android.art/lib64/libart.so ] && [ -s $CP ]; do
    kill -0 $BA 2>/dev/null || { klog "boot terminou antes do ART"; exit 0; }
    sleep 0.1
done
while read -r cmd var val; do
    [ "$cmd" = "export" ] && export "$var=$val"
done < $CP
klog "ambiente carregado (BOOTCLASSPATH ${#BOOTCLASSPATH} chars)"

export CLASSPATH=/product/framework/hy300-bootlog.jar
try=0
while kill -0 $BA 2>/dev/null; do
    try=$((try+1))
    klog "tentativa $try de iniciar a VM"
    # -Xdeny-art-apex-data-files: só a boot image do APEX (a de /data pode ainda não estar
    # verificada pelo odsign nesse ponto; mesmo motivo do zygote).
    app_process -Xdeny-art-apex-data-files /system/bin com.hy300.bootlog.Main \
        "$W" "$H" $LOGO > /dev/kmsg 2>&1 &
    APP=$!
    while kill -0 $APP 2>/dev/null && [ ! -e /dev/.bootlog_ready ]; do sleep 0.05; done
    if [ -e /dev/.bootlog_ready ]; then
        klog "desenhando, encerrando bootanimation nativo"
        kill $BA 2>/dev/null
        wait $APP; klog "bootlog terminou rc=$?"
        rm -f /dev/.bootlog_ready
        exit 0
    fi
    wait $APP; klog "VM falhou (rc=$?)"
    [ $try -ge 60 ] && break
    sleep 0.3
done
klog "seguindo com bootanimation nativo"
wait $BA
