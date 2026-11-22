#!/system/bin/sh
# Animação de boot com log ao vivo (hy300-rk3566/android/bootlog).
# 1) bootanimation nativo mostra a capivara (bootanimation.zip de 1 quadro) até o ART estar pronto
# 2) bootlog (app_process) desenha o logcat ao vivo; no 1º quadro, encerra o nativo
# 3) se a VM não subir, tenta de novo; nunca segura o boot
klog() { echo "bootlog: $*" > /dev/kmsg; }
rm -f /dev/.bootlog_ready
/system/bin/bootanimation &
BA=$!
klog "start, bootanimation pid=$BA"

# O serviço nasce antes do post-fs-data, então herda um ambiente SEM BOOTCLASSPATH etc.
# (no Android 12 elas são geradas pelo derive_classpath após os APEX ativarem).
# Espera o APEX do ART + o arquivo de exports e carrega as variáveis.
CP=/data/system/environ/classpath
until [ "$(getprop apexd.status)" = "ready" ] && [ -e /apex/com.android.art/lib/libart.so ] && [ -s $CP ]; do
    kill -0 $BA 2>/dev/null || { klog "boot terminou antes do ART"; exit 0; }
    sleep 0.1
done
while read -r cmd var val; do
    [ "$cmd" = "export" ] && export "$var=$val"
done < $CP
klog "ambiente carregado (BOOTCLASSPATH ${#BOOTCLASSPATH} chars)"

export CLASSPATH=/system/media/bootlog/bootlog.dex
try=0
while kill -0 $BA 2>/dev/null; do
    try=$((try+1))
    klog "tentativa $try de iniciar a VM"
    # -Xdeny-art-apex-data-files: usa só a boot image do APEX (a de /data ainda pode não estar
    # verificada pelo odsign nesse ponto — mesmo motivo do zygote usar essa opção)
    app_process -Xdeny-art-apex-data-files /system/bin com.hy300.bootlog.Main \
        1280 720 /system/media/bootlog/logo.png > /dev/kmsg 2>&1 &
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
