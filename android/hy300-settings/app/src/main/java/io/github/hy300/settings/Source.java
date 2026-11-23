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
    /** LineageOS: a tela da entrada HDMI do TV input do HY300 (device/txcz/hy300 apps/HdmiInput). */
    public static final String LINEAGE_HDMI_PKG = "io.github.hy300.hdmi";
    public static final String LINEAGE_HDMI_CLS = "io.github.hy300.hdmi.HdmiActivity";
    /** Ordem de tentativa para "Abrir HDMI": a do LineageOS, depois o app de câmera da fábrica. */
    public static final String[][] HDMI_TARGETS = {
            {LINEAGE_HDMI_PKG, LINEAGE_HDMI_CLS},
            {HDMI_PKG, HDMI_CLS},
    };

    private Source() {}

    public static boolean openHdmi(Context c) {
        for (String[] target : HDMI_TARGETS) {
            Intent i = new Intent().setComponent(new ComponentName(target[0], target[1]))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            try {
                c.startActivity(i);
                return true;
            } catch (Exception e) {
                // tenta a próxima
            }
        }
        return false;
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
