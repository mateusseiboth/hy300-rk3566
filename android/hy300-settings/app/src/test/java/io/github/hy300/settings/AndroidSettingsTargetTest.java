package io.github.hy300.settings;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import java.util.Arrays;
import java.util.Collections;

import org.junit.Test;

public class AndroidSettingsTargetTest {
    private static final String OWN = "io.github.hy300.settings";

    @Test
    public void prefersTvSettingsMain() {
        String t = AndroidSettingsTarget.choose(Arrays.asList(
                "com.android.tv.set/com.android.tv.set.connectivity.NetworkActivity",
                "com.android.tv.set/com.android.tv.set.MainSettings"), OWN);
        assertEquals("com.android.tv.set/com.android.tv.set.MainSettings", t);
    }

    @Test
    public void neverPicksTxczOrItself() {
        String t = AndroidSettingsTarget.choose(Arrays.asList(
                "com.android.tv.settings/com.shzhtxcz.txbox.MainActivity",
                OWN + "/" + OWN + ".AndroidSettingsActivity",
                "org.exemplo.tv/org.exemplo.tv.Settings"), OWN);
        assertEquals("org.exemplo.tv/org.exemplo.tv.Settings", t);
    }

    @Test
    public void picksLineageTvSettings() {
        // No LineageOS o pacote com.android.tv.settings é o TvSettings do AOSP, não o da TXCZ.
        String t = AndroidSettingsTarget.choose(Arrays.asList(
                OWN + "/" + OWN + ".AndroidSettingsActivity",
                "com.android.tv.settings/com.android.tv.settings.MainSettings"), OWN);
        assertEquals("com.android.tv.settings/com.android.tv.settings.MainSettings", t);
    }

    @Test
    public void noTargetWhenOnlyBlocked() {
        assertNull(AndroidSettingsTarget.choose(Collections.singletonList(
                "com.android.tv.settings/com.shzhtxcz.txbox.MainActivity"), OWN));
        assertNull(AndroidSettingsTarget.choose(Collections.emptyList(), OWN));
    }

    @Test
    public void defaultIsTvSettingsMain() {
        assertEquals("com.android.tv.set/com.android.tv.set.MainSettings", AndroidSettingsTarget.TV_SETTINGS_MAIN);
    }
}
