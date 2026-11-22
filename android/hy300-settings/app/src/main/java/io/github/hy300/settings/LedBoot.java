package io.github.hy300.settings;

import android.content.Context;
import android.content.SharedPreferences;

import java.util.HashMap;
import java.util.Map;

/** Reaplica no boot os LEDs que o usuário desligou (o kernel liga todos ao iniciar). */
public final class LedBoot {
    public static final String FILE = "leds";

    private LedBoot() {}

    public static void apply(Context c) {
        SharedPreferences sp = c.getSharedPreferences(FILE, Context.MODE_PRIVATE);
        Map<String, Boolean> wanted = new HashMap<>();
        for (String led : Leds.CONTROLLABLE) {
            if (sp.contains(led)) wanted.put(led, sp.getBoolean(led, true));
        }
        for (Map.Entry<String, String> w : Leds.buildBootWrites(wanted).entrySet()) {
            Sys.writeFile(w.getKey(), w.getValue());
        }
    }
}
