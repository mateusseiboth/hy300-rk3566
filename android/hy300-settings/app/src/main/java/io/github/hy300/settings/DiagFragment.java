package io.github.hy300.settings;

import android.content.pm.ApplicationInfo;

import androidx.preference.Preference;
import androidx.preference.PreferenceCategory;
import androidx.preference.PreferenceScreen;

import java.util.List;

public class DiagFragment extends BasePrefs {
    private PreferenceCategory results;

    @Override
    protected void build(PreferenceScreen s) {
        s.setTitle(R.string.cat_about);
        boolean system = (ctx().getApplicationInfo().flags & ApplicationInfo.FLAG_SYSTEM) != 0;
        addRow(s, getString(R.string.diag_system), getString(system ? R.string.diag_system_yes : R.string.diag_system_no));
        action(s, "diag", R.string.diag_run, null, this::run);
        results = category(s, R.string.diag_results);
    }

    private void run() {
        results.removeAll();
        addRow(results, getString(R.string.loading), null);
        Bg.load(() -> Diag.buildRows(Diag.measure()), this::show);
    }

    private void show(List<String[]> rows) {
        if (!isAdded()) return;
        results.removeAll();
        for (String[] r : rows) addRow(results, r[0], r[1]);
    }

    private void addRow(androidx.preference.PreferenceGroup g, String title, String value) {
        Preference p = new Preference(ctx());
        p.setTitle(title);
        p.setSummary(value);
        p.setPersistent(false);
        p.setSelectable(false);
        g.addPreference(p);
    }
}
