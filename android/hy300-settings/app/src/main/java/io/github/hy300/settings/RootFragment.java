package io.github.hy300.settings;

import android.content.Intent;

import androidx.preference.PreferenceScreen;

public class RootFragment extends BasePrefs {
    @Override
    protected void build(PreferenceScreen s) {
        s.setTitle(R.string.app_title);
        icon(link(s, "projection", R.string.cat_projection, getString(R.string.cat_projection_summary), ProjectionFragment.class), R.drawable.ic_projection);
        icon(link(s, "auto_ks", R.string.cat_auto_ks, getString(R.string.cat_auto_ks_summary), AutoKeystoneFragment.class), R.drawable.ic_auto_keystone);
        icon(action(s, "focus", R.string.cat_focus, getString(R.string.cat_focus_summary),
                () -> startActivity(new Intent(ctx(), FocusActivity.class))), R.drawable.ic_focus);
        icon(link(s, "source", R.string.cat_source, getString(R.string.cat_source_summary), SourceFragment.class), R.drawable.ic_source);
        icon(link(s, "image", R.string.cat_image, getString(R.string.cat_image_summary), ImageFragment.class), R.drawable.ic_image);
        icon(link(s, "other", R.string.cat_other, getString(R.string.cat_other_summary), OtherFragment.class), R.drawable.ic_other);
        icon(link(s, "diag", R.string.cat_about, getString(R.string.cat_about_summary), DiagFragment.class), R.drawable.ic_diag);
        icon(action(s, "android_settings", R.string.open_android_settings, null,
                () -> AndroidSettingsActivity.open(ctx())), R.drawable.ic_android_settings);
    }
}
