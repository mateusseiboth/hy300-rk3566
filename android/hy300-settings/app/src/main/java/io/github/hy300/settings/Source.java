package io.github.hy300.settings;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;

import java.util.LinkedHashMap;

/** Fonte ao ligar: consumida pelo RootWindowContainer do services.jar TXCZ. */
public final class Source {
    public static final String P_SOURCE = "persist.txcz.source";
    public static final String P_BOOT_APP = "persist.txcz.boot.app";
    public static final String HDMI_PKG = "com.android.rockchip.camera2";
    public static final String HDMI_CLS = "com.android.rockchip.camera2.RockchipCamera2";
    public static final String HDMI_BOOT = HDMI_PKG + "," + HDMI_CLS;

    private Source() {}

    public static boolean openHdmi(Context c) {
        Intent i = new Intent().setComponent(new ComponentName(HDMI_PKG, HDMI_CLS))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            c.startActivity(i);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    public static boolean setHome() { return write("0", ""); }
    public static boolean setHdmi() { return write("1", HDMI_BOOT); }
    /** Só o pacote: o framework abre a activity MAIN/LAUNCHER na hora (sem os 10 s). */
    public static boolean setApp(String pkg) { return write("2", pkg); }

    private static boolean write(String src, String app) {
        LinkedHashMap<String, String> m = new LinkedHashMap<>();
        m.put(P_SOURCE, src);
        m.put(P_BOOT_APP, app);
        return Sys.setAll(m);
    }

    public static String label(Context c, String pkg) {
        PackageManager pm = c.getPackageManager();
        try {
            return pm.getApplicationLabel(pm.getApplicationInfo(pkg, 0)).toString();
        } catch (PackageManager.NameNotFoundException e) {
            return pkg;
        }
    }
}
