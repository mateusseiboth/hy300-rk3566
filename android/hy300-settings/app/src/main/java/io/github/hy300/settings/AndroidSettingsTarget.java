package io.github.hy300.settings;

import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Destino das "Configurações do Android": o TvSettings AOSP/Rockchip do aparelho
 * ({@code com.android.tv.set}, renomeado porque o app da TXCZ ocupa com.android.tv.settings).
 * Ele não declara android.settings.SETTINGS, então este app trata a ação e repassa.
 * Candidatos no formato "pacote/classe" (ComponentName.flattenToString sem abreviar).
 */
public final class AndroidSettingsTarget {
    public static final String TV_SETTINGS_MAIN = "com.android.tv.set/com.android.tv.set.MainSettings";
    /** App de configurações da TXCZ: nunca é destino. */
    public static final String TXCZ_PKG = "com.android.tv.settings";

    private AndroidSettingsTarget() {}

    /** Escolhe o destino entre os que tratam MAIN + LEANBACK_SETTINGS; null se não houver. */
    public static String choose(List<String> candidates, String ownPkg) {
        if (candidates.contains(TV_SETTINGS_MAIN)) return TV_SETTINGS_MAIN;
        Set<String> blocked = new HashSet<>(Arrays.asList(TXCZ_PKG, ownPkg));
        for (String c : candidates) {
            if (!blocked.contains(packageOf(c))) return c;
        }
        return null;
    }

    private static String packageOf(String flat) {
        int i = flat.indexOf('/');
        return i < 0 ? flat : flat.substring(0, i);
    }
}
