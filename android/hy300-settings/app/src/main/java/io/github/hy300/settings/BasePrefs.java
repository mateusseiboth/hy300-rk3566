package io.github.hy300.settings;

import android.content.Context;
import android.os.Bundle;

import androidx.annotation.Nullable;
import androidx.leanback.preference.LeanbackPreferenceFragmentCompat;
import androidx.preference.ListPreference;
import androidx.preference.Preference;
import androidx.preference.PreferenceCategory;
import androidx.preference.PreferenceGroup;
import androidx.preference.PreferenceScreen;
import androidx.preference.SwitchPreference;

/** Base das telas: monta a hierarquia em código (sem persistência em SharedPreferences). */
public abstract class BasePrefs extends LeanbackPreferenceFragmentCompat {

    protected abstract void build(PreferenceScreen screen);

    @Override
    public void onCreatePreferences(@Nullable Bundle savedInstanceState, @Nullable String rootKey) {
        PreferenceScreen s = getPreferenceManager().createPreferenceScreen(requireContext());
        build(s);
        setPreferenceScreen(s);
    }

    protected Preference action(PreferenceGroup g, String key, int title, CharSequence summary, Runnable onClick) {
        Preference p = new Preference(ctx());
        p.setKey(key);
        p.setTitle(title);
        p.setPersistent(false);
        if (summary != null) p.setSummary(summary);
        p.setOnPreferenceClickListener(x -> { onClick.run(); return true; });
        g.addPreference(p);
        return p;
    }

    protected Preference link(PreferenceGroup g, String key, int title, CharSequence summary, Class<?> fragment) {
        Preference p = new Preference(ctx());
        p.setKey(key);
        p.setTitle(title);
        p.setPersistent(false);
        if (summary != null) p.setSummary(summary);
        p.setFragment(fragment.getName());
        g.addPreference(p);
        return p;
    }

    protected ListPreference list(PreferenceGroup g, String key, int title, int entries, int values,
                                  Preference.OnPreferenceChangeListener l) {
        ListPreference p = new ListPreference(ctx());
        p.setKey(key);
        p.setTitle(title);
        p.setDialogTitle(title);
        p.setPersistent(false);
        p.setEntries(entries);
        p.setEntryValues(values);
        p.setSummaryProvider(ListPreference.SimpleSummaryProvider.getInstance());
        p.setOnPreferenceChangeListener(l);
        g.addPreference(p);
        return p;
    }

    protected SwitchPreference toggle(PreferenceGroup g, String key, int title, CharSequence summary,
                                      Preference.OnPreferenceChangeListener l) {
        SwitchPreference p = new SwitchPreference(ctx());
        p.setKey(key);
        p.setTitle(title);
        p.setPersistent(false);
        if (summary != null) p.setSummary(summary);
        p.setOnPreferenceChangeListener(l);
        g.addPreference(p);
        return p;
    }

    protected PreferenceCategory category(PreferenceGroup g, int title) {
        PreferenceCategory c = new PreferenceCategory(ctx());
        c.setTitle(title);
        g.addPreference(c);
        return c;
    }

    protected Context ctx() {
        return getPreferenceManager().getContext();
    }
}
