package io.github.hy300.settings;

import android.util.Log;

import java.lang.reflect.Method;

/**
 * BCSH (brilho/contraste/saturação/matiz) do display, escala 0..100, padrão 50.
 *
 * Caminho preferido: {@code android.os.RkDisplayOutputManager} (classe Rockchip no framework,
 * a mesma que o TvSettings RK usa em display/AdvancedDisplaySettingsActivity), por reflexão.
 * Fallback: grava {@code persist.vendor.<item>.main} e incrementa {@code vendor.display.timeline},
 * que é o gatilho que o HWC ({@code HwcDisplay::UpdateBCSH}) observa.
 * No LineageOS do HY300 o drm_hwcomposer lê {@code persist.sys.hy300.picture.<item>} (o sistema não
 * pode gravar props do vendor com o SELinux do Treble) e não precisa de gatilho.
 */
public final class RkDisplay {
    private static final String TAG = "HY300RkDisplay";
    public static final String[] ITEMS = {"brightness", "contrast", "saturation", "hue"};
    private static final String[] SETTERS = {"setBrightness", "setContrast", "setSaturation", "setHue"};
    private static final String[] GETTERS = {"getBrightness", "getContrast", "getSaturation", "getHue"};
    private static Object mgr;
    private static boolean tried;
    public static String lastPath = "?";

    private RkDisplay() {}

    private static synchronized Object mgr() {
        if (!tried) {
            tried = true;
            try {
                mgr = Class.forName("android.os.RkDisplayOutputManager").newInstance();
            } catch (Throwable t) {
                Log.w(TAG, "RkDisplayOutputManager indisponível: " + t);
            }
        }
        return mgr;
    }

    private static Boolean lineage;

    public static String prop(int i, boolean lineage) {
        return lineage ? "persist.sys.hy300.picture." + ITEMS[i] : "persist.vendor." + ITEMS[i] + ".main";
    }

    public static boolean isLineage(java.util.Map<String, String> props) {
        String version = props.get("ro.lineage.version");
        return version != null && !version.isEmpty();
    }

    public static boolean needsTimeline(boolean lineage) { return !lineage; }

    private static synchronized boolean lineage() {
        if (lineage == null) lineage = !Sys.get("ro.lineage.version", "").isEmpty();
        return lineage;
    }

    public static String prop(int i) { return prop(i, lineage()); }

    public static boolean set(int i, int value) {
        Object m = mgr();
        if (m != null) {
            try {
                Method me = m.getClass().getMethod(SETTERS[i], int.class, int.class);
                Object r = me.invoke(m, 0, value);
                lastPath = "RkDisplayOutputManager (ret=" + r + ")";
                Log.i(TAG, SETTERS[i] + "(0," + value + ") -> " + r);
                return true;
            } catch (Throwable t) {
                Log.w(TAG, SETTERS[i] + " falhou: " + t);
            }
        }
        boolean ok = Sys.set(prop(i), String.valueOf(value));
        if (!needsTimeline(lineage())) {
            lastPath = "persist.sys.hy300.picture (drm_hwcomposer)";
            return ok;
        }
        lastPath = "props + vendor.display.timeline";
        int t = 0;
        try { t = Integer.parseInt(Sys.get("vendor.display.timeline", "0")); } catch (NumberFormatException ignored) { }
        return ok & Sys.set("vendor.display.timeline", String.valueOf(t + 1));
    }

    public static int get(int i, java.util.Map<String, String> props) {
        Object m = mgr();
        if (m != null) {
            try {
                Method me = m.getClass().getMethod(GETTERS[i], int.class);
                Object r = me.invoke(m, 0);
                if (r instanceof Integer) return (Integer) r;
            } catch (Throwable t) {
                Log.w(TAG, GETTERS[i] + " falhou: " + t);
            }
        }
        return Sys.getInt(props, prop(i), 50);
    }
}
