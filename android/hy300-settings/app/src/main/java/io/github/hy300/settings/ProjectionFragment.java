package io.github.hy300.settings;

import android.widget.Toast;

import androidx.preference.ListPreference;
import androidx.preference.Preference;
import androidx.preference.PreferenceScreen;

public class ProjectionFragment extends BasePrefs {
    private Preference corners, trapezoid, zoom;
    private ListPreference ratio, mode;
    private Keystone ks;

    @Override
    protected void build(PreferenceScreen s) {
        s.setTitle(R.string.cat_projection);
        mode = list(s, "mode", R.string.ks_mode, R.array.mode_entries, R.array.mode_values, (p, v) -> {
            change(k -> k.mode = Integer.parseInt((String) v));
            return true;
        });
        corners = action(s, "corners", R.string.ks_corners, getString(R.string.ks_corners_summary),
                () -> KeystoneActivity.start(ctx(), KeystoneActivity.PAGE_CORNERS));
        trapezoid = action(s, "trapezoid", R.string.ks_trapezoid, null,
                () -> KeystoneActivity.start(ctx(), KeystoneActivity.PAGE_TRAPEZOID));
        zoom = action(s, "zoom", R.string.ks_zoom, null,
                () -> KeystoneActivity.start(ctx(), KeystoneActivity.PAGE_ZOOM));
        ratio = list(s, "ratio", R.string.ks_ratio, R.array.ratio_entries, R.array.ratio_values, (p, v) -> {
            change(k -> { k.ratio = Integer.parseInt((String) v); k.clamp(); });
            return true;
        });
        action(s, "pattern", R.string.ks_pattern, null,
                () -> KeystoneActivity.start(ctx(), KeystoneActivity.PAGE_PATTERN));
        action(s, "reset", R.string.ks_reset, getString(R.string.ks_reset_summary), () -> {
            change(k -> { k.resetUser(); k.setZoom(100); });
            AutoKeystoneService.forgetAuto(ctx());
            Toast.makeText(ctx(), R.string.ks_reset_done, Toast.LENGTH_SHORT).show();
        });
    }

    private interface Edit { void apply(Keystone k); }

    private void change(Edit e) {
        Bg.load(() -> {
            Keystone k = Keystone.fromProps(Sys.getAll());
            e.apply(k);
            KeystoneApplier.applyNow(k);
            return k;
        }, this::show);
    }

    @Override
    public void onResume() {
        super.onResume();
        Bg.load(() -> Keystone.fromProps(Sys.getAll()), this::show);
    }

    private void show(Keystone k) {
        ks = k;
        if (!isAdded()) return;
        mode.setValue(String.valueOf(k.mode));
        ratio.setValue(String.valueOf(k.ratio));
        trapezoid.setSummary(getString(R.string.ks_trapezoid_summary, k.trapV, k.trapH));
        zoom.setSummary(getString(R.string.ks_zoom_summary, k.zoom));
    }
}
