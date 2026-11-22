package io.github.hy300.settings;

import android.os.Bundle;

import androidx.annotation.NonNull;
import androidx.fragment.app.Fragment;
import androidx.leanback.preference.LeanbackSettingsFragmentCompat;
import androidx.preference.Preference;
import androidx.preference.PreferenceFragmentCompat;
import androidx.preference.PreferenceScreen;

/** Contêiner leanback que empilha as telas de preferências. */
public class SettingsFragment extends LeanbackSettingsFragmentCompat {
    @Override
    public void onPreferenceStartInitialScreen() {
        startPreferenceFragment(new RootFragment());
    }

    @Override
    public boolean onPreferenceStartFragment(@NonNull PreferenceFragmentCompat caller, @NonNull Preference pref) {
        Fragment f = getChildFragmentManager().getFragmentFactory()
                .instantiate(requireActivity().getClassLoader(), pref.getFragment());
        Bundle args = new Bundle(pref.getExtras());
        f.setArguments(args);
        startPreferenceFragment(f);
        return true;
    }

    @Override
    public boolean onPreferenceStartScreen(@NonNull PreferenceFragmentCompat caller, @NonNull PreferenceScreen pref) {
        return false;
    }
}
