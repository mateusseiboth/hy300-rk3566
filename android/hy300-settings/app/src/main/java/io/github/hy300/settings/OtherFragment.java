package io.github.hy300.settings;

import android.content.ComponentName;
import android.content.Intent;
import android.widget.Toast;

import androidx.preference.PreferenceScreen;
import androidx.preference.SwitchPreference;

import java.util.Map;

public class OtherFragment extends BasePrefs {
    private SwitchPreference a2dp, f12;

    @Override
    protected void build(PreferenceScreen s) {
        s.setTitle(R.string.cat_other);
        a2dp = toggle(s, "a2dp", R.string.other_a2dp, getString(R.string.other_a2dp_summary), (p, v) -> {
            boolean on = (Boolean) v;
            Bg.run(() -> Sys.set("persist.bluetooth.rka2dpsink", on ? "true" : "false"));
            return true;
        });
        f12 = toggle(s, "f12", R.string.other_f12, getString(R.string.other_f12_summary), (p, v) -> {
            boolean ok = F12KeyService.setEnabled(ctx(), (Boolean) v);
            if (!ok) Toast.makeText(ctx(), R.string.other_f12_need_perm, Toast.LENGTH_LONG).show();
            return ok;
        });
        action(s, "txcz", R.string.other_txcz, null, () -> {
            try {
                startActivity(new Intent().setComponent(new ComponentName("com.android.tv.settings",
                        "com.shzhtxcz.txbox.MainActivity")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            } catch (Exception e) {
                Toast.makeText(ctx(), "App TXCZ não encontrado", Toast.LENGTH_SHORT).show();
            }
        });
    }

    @Override
    public void onResume() {
        super.onResume();
        f12.setChecked(F12KeyService.isEnabled(ctx()));
        Bg.load(Sys::getAll, this::show);
    }

    private void show(Map<String, String> p) {
        if (!isAdded()) return;
        a2dp.setChecked("true".equals(p.get("persist.bluetooth.rka2dpsink")));
    }
}
