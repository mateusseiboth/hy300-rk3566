package io.github.hy300.settings;

import android.content.Intent;

import androidx.preference.PreferenceScreen;

public class RootFragment extends BasePrefs {
    @Override
    protected void build(PreferenceScreen s) {
        s.setTitle(R.string.app_title);
        link(s, "projection", R.string.cat_projection, getString(R.string.cat_projection_summary), ProjectionFragment.class);
        link(s, "auto_ks", R.string.cat_auto_ks, null, AutoKeystoneFragment.class);
        action(s, "focus", R.string.cat_focus, getString(R.string.cat_focus_summary),
                () -> startActivity(new Intent(ctx(), FocusActivity.class)));
        link(s, "source", R.string.cat_source, null, SourceFragment.class);
        link(s, "image", R.string.cat_image, getString(R.string.cat_image_summary), ImageFragment.class);
        link(s, "other", R.string.cat_other, null, OtherFragment.class);
        link(s, "diag", R.string.cat_about, getString(R.string.cat_about_summary), DiagFragment.class);
        action(s, "android_settings", R.string.open_android_settings, null, () -> {
            Intent i = new Intent(android.provider.Settings.ACTION_SETTINGS);
            i.setPackage("com.android.tv.set");
            try { startActivity(i); } catch (Exception e) {
                startActivity(new Intent(android.provider.Settings.ACTION_SETTINGS));
            }
        });
    }
}
