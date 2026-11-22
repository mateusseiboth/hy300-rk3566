package io.github.hy300.settings;

import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.widget.Toast;

import androidx.preference.Preference;
import androidx.preference.PreferenceScreen;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Lista de apps abríveis (launcher comum e leanback) para abrir ao ligar. */
public class AppPickerFragment extends BasePrefs {
    @Override
    protected void build(PreferenceScreen s) {
        s.setTitle(R.string.src_pick_app);
        PackageManager pm = ctx().getPackageManager();
        List<ResolveInfo> all = new ArrayList<>();
        all.addAll(pm.queryIntentActivities(new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LEANBACK_LAUNCHER), 0));
        all.addAll(pm.queryIntentActivities(new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER), 0));
        Set<String> seen = new HashSet<>();
        List<Preference> items = new ArrayList<>();
        for (ResolveInfo ri : all) {
            String pkg = ri.activityInfo.packageName;
            if (pkg.equals(ctx().getPackageName()) || !seen.add(pkg)) continue;
            Preference p = new Preference(ctx());
            p.setPersistent(false);
            p.setTitle(ri.loadLabel(pm));
            p.setSummary(pkg);
            p.setIcon(ri.loadIcon(pm));
            p.setOnPreferenceClickListener(x -> {
                Bg.load(() -> Source.setApp(pkg), ok -> {
                    Toast.makeText(ctx(), ok ? R.string.src_saved : R.string.write_failed, Toast.LENGTH_SHORT).show();
                    if (isAdded()) getParentFragmentManager().popBackStack();
                });
                return true;
            });
            items.add(p);
        }
        items.sort((a, b) -> a.getTitle().toString().compareToIgnoreCase(b.getTitle().toString()));
        for (Preference p : items) s.addPreference(p);
    }
}
