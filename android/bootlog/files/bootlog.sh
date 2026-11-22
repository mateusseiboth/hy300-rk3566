#!/system/bin/sh
# Mostra o logcat ao vivo durante o boot; se falhar, cai para a animação original.
export CLASSPATH=/system/media/bootlog/bootlog.dex
app_process /system/bin com.hy300.bootlog.Main 1280 720 /system/media/bootlog/logo.png
rc=$?
if [ "$rc" -ne 0 ] && [ "$(getprop service.bootanim.exit)" != "1" ]; then
    exec /system/bin/bootanimation
fi
