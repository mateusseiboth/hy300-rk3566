package io.github.hy300.settings;

import android.content.Context;
import android.widget.Toast;

import androidx.preference.PreferenceScreen;
import androidx.preference.SwitchPreference;

import java.util.Map;

public class OtherFragment extends BasePrefs {
    private SwitchPreference a2dp, f12;
    private final SwitchPreference[] leds = new SwitchPreference[Leds.CONTROLLABLE.size()];
    private static final int[] LED_TITLES = {R.string.other_led_green, R.string.other_led_red};

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
        for (int i = 0; i < leds.length; i++) {
            String led = Leds.CONTROLLABLE.get(i);
            leds[i] = toggle(s, "led_" + led, LED_TITLES[i], null, (p, v) -> {
                boolean on = (Boolean) v;
                boolean ok = Sys.writeFile(Leds.pathOf(led), Leds.valueOf(on));
                if (!ok) {
                    Toast.makeText(ctx(), R.string.other_led_failed, Toast.LENGTH_LONG).show();
                    return false;
                }
                ctx().getSharedPreferences(LedBoot.FILE, Context.MODE_PRIVATE).edit().putBoolean(led, on).apply();
                return true;
            });
        }
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
        for (int i = 0; i < leds.length; i++) {
            leds[i].setChecked(Leds.isOn(Sys.readFile(Leds.pathOf(Leds.CONTROLLABLE.get(i)))));
        }
    }
}
