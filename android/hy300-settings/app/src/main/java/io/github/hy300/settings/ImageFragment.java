package io.github.hy300.settings;

import androidx.preference.PreferenceScreen;
import androidx.preference.SeekBarPreference;

import java.util.Map;

/**
 * BCSH do HWC Rockchip: persist.vendor.{brightness,contrast,saturation,hue}.main, 0..100,
 * padrão 50 (ver README e RkDisplay).
 */
public class ImageFragment extends BasePrefs {
    static final String[] KEYS = {"brightness", "contrast", "saturation", "hue"};
    static final int[] TITLES = {R.string.img_brightness, R.string.img_contrast, R.string.img_saturation, R.string.img_hue};
    public static final int DEFAULT = 50;

    private final SeekBarPreference[] bars = new SeekBarPreference[4];

    static String prop(int i) { return "persist.vendor." + KEYS[i] + ".main"; }

    @Override
    protected void build(PreferenceScreen s) {
        s.setTitle(R.string.cat_image);
        for (int i = 0; i < 4; i++) {
            final int idx = i;
            SeekBarPreference b = new SeekBarPreference(ctx());
            b.setKey(KEYS[i]);
            b.setTitle(TITLES[i]);
            b.setPersistent(false);
            b.setMin(0);
            b.setMax(100);
            b.setSeekBarIncrement(1);
            b.setShowSeekBarValue(true);
            b.setUpdatesContinuously(true);
            b.setAdjustable(true);
            b.setValue(DEFAULT);
            b.setOnPreferenceChangeListener((p, v) -> {
                int val = (Integer) v;
                Bg.run(() -> RkDisplay.set(idx, val));
                return true;
            });
            s.addPreference(b);
            bars[i] = b;
        }
        action(s, "img_reset", R.string.img_reset, null, () -> {
            for (SeekBarPreference b : bars) b.setValue(DEFAULT);
            Bg.run(() -> {
                for (int i = 0; i < 4; i++) RkDisplay.set(i, DEFAULT);
            });
        });
    }

    @Override
    public void onResume() {
        super.onResume();
        Bg.load(() -> {
            Map<String, String> p = Sys.getAll();
            int[] v = new int[4];
            for (int i = 0; i < 4; i++) v[i] = RkDisplay.get(i, p);
            return v;
        }, this::show);
    }

    private void show(int[] v) {
        if (!isAdded()) return;
        for (int i = 0; i < 4; i++) bars[i].setValue(v[i]);
    }

}
