package io.github.hy300.settings;

import java.util.List;

/**
 * Destino das "Configurações do Android". Na ROM de fábrica é o TvSettings AOSP/Rockchip
 * ({@code com.android.tv.set}, renomeado porque o app da TXCZ ocupa com.android.tv.settings), que
 * não declara android.settings.SETTINGS, então este app trata a ação e repassa. No LineageOS o
 * com.android.tv.settings é o próprio TvSettings: a TXCZ é reconhecida pela classe, não pelo pacote.
 * Candidatos no formato "pacote/classe" (ComponentName.flattenToString sem abreviar).
 */
public final class AndroidSettingsTarget {
    public static final String TV_SETTINGS_MAIN = "com.android.tv.set/com.android.tv.set.MainSettings";
    /** Classes do app de configurações da TXCZ (pacote com.android.tv.settings): nunca são destino. */
    public static final String TXCZ_CLASS_PREFIX = "com.shzhtxcz.";

    private AndroidSettingsTarget() {}

    /** Escolhe o destino entre os que tratam MAIN + LEANBACK_SETTINGS; null se não houver. */
    public static String choose(List<String> candidates, String ownPkg) {
        if (candidates.contains(TV_SETTINGS_MAIN)) return TV_SETTINGS_MAIN;
        for (String c : candidates) {
            if (!ownPkg.equals(packageOf(c)) && !classOf(c).startsWith(TXCZ_CLASS_PREFIX)) return c;
        }
        return null;
    }

    private static String packageOf(String flat) {
        int i = flat.indexOf('/');
        return i < 0 ? flat : flat.substring(0, i);
    }

    private static String classOf(String flat) {
        return flat.substring(flat.indexOf('/') + 1);
    }
}
