package io.github.hy300.settings;

import android.content.pm.ApplicationInfo;

import androidx.preference.Preference;
import androidx.preference.PreferenceScreen;

public class DiagFragment extends BasePrefs {
    private Preference result;

    @Override
    protected void build(PreferenceScreen s) {
        s.setTitle(R.string.cat_about);
        boolean system = (ctx().getApplicationInfo().flags & ApplicationInfo.FLAG_SYSTEM) != 0;
        Preference sys = new Preference(ctx());
        sys.setTitle(R.string.diag_system);
        sys.setSummary(system ? "sim (aparece nas Configurações do Android)" : "não (app comum em /data)");
        sys.setSelectable(false);
        s.addPreference(sys);
        result = action(s, "diag", R.string.diag_run, null, this::run);
    }

    private void run() {
        result.setSummary(R.string.loading);
        Bg.load(Diag::run, r -> { if (isAdded()) result.setSummary(r); });
    }
}
