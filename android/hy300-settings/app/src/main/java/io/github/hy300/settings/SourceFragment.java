package io.github.hy300.settings;

import android.os.Bundle;
import android.widget.Toast;

import androidx.preference.Preference;
import androidx.preference.PreferenceCategory;
import androidx.preference.PreferenceScreen;
import androidx.preference.CheckBoxPreference;

import java.util.Map;

public class SourceFragment extends BasePrefs {
    private CheckBoxPreference home, hdmi, app;
    private Preference pick;

    @Override
    protected void build(PreferenceScreen s) {
        s.setTitle(R.string.cat_source);
        action(s, "hdmi_now", R.string.src_open_hdmi, null, () -> {
            if (!Source.openHdmi(ctx())) Toast.makeText(ctx(), R.string.src_hdmi_missing, Toast.LENGTH_SHORT).show();
        });
        PreferenceCategory c = category(s, R.string.src_boot);
        home = radio(c, "home", getString(R.string.src_boot_home));
        hdmi = radio(c, "hdmi", getString(R.string.src_boot_hdmi));
        app = radio(c, "app", getString(R.string.src_boot_app));
        home.setOnPreferenceClickListener(p -> { save(Source::setHome); return true; });
        hdmi.setOnPreferenceClickListener(p -> { save(Source::setHdmi); return true; });
        app.setOnPreferenceClickListener(p -> {
            // abre a lista de apps
            getParentSettings().onPreferenceStartFragment(this, pick);
            return true;
        });
        // Só serve de destino para o clique em "Aplicativo" (abre a lista).
        pick = link(c, "pick", R.string.src_pick_app, null, AppPickerFragment.class);
        pick.setVisible(false);
    }

    private SettingsFragment getParentSettings() {
        return (SettingsFragment) getParentFragment();
    }

    private CheckBoxPreference radio(PreferenceCategory c, String key, String title) {
        CheckBoxPreference p = new CheckBoxPreference(ctx());
        p.setKey(key);
        p.setTitle(title);
        p.setPersistent(false);
        c.addPreference(p);
        return p;
    }

    private interface W { boolean write(); }

    private void save(W w) {
        Bg.load(w::write, ok -> {
            Toast.makeText(ctx(), ok ? R.string.src_saved : R.string.write_failed, Toast.LENGTH_SHORT).show();
            refresh();
        });
    }

    @Override
    public void onResume() {
        super.onResume();
        refresh();
    }

    private void refresh() {
        Bg.load(Sys::getAll, this::show);
    }

    private void show(Map<String, String> p) {
        if (!isAdded()) return;
        String bootApp = p.getOrDefault(Source.P_BOOT_APP, "");
        boolean isHdmi = bootApp.startsWith(Source.HDMI_PKG);
        boolean isHome = bootApp.isEmpty();
        home.setChecked(isHome);
        hdmi.setChecked(isHdmi);
        app.setChecked(!isHome && !isHdmi);
        String pkg = bootApp.split(",")[0];
        app.setSummary((!isHome && !isHdmi) ? Source.label(ctx(), pkg) : getString(R.string.src_boot_app_none));
    }
}
