package io.github.hy300.settings;

import android.content.Context;
import android.content.SharedPreferences;

/** {@link AutoKeystoneState.Store} sobre SharedPreferences. */
public final class SharedPrefsStore implements AutoKeystoneState.Store {
    private final SharedPreferences sp;

    private SharedPrefsStore(SharedPreferences sp) {
        this.sp = sp;
    }

    public static AutoKeystoneState autoKeystone(Context c) {
        return new AutoKeystoneState(new SharedPrefsStore(
                c.getApplicationContext().getSharedPreferences(AutoKeystoneState.FILE, Context.MODE_PRIVATE)));
    }

    @Override public boolean getBoolean(String key, boolean def) { return sp.getBoolean(key, def); }
    @Override public float getFloat(String key, float def) { return sp.getFloat(key, def); }
    @Override public int getInt(String key, int def) { return sp.getInt(key, def); }
    // commit(): o serviço e a tela leem o mesmo arquivo em threads diferentes logo em seguida.
    @Override public void putBoolean(String key, boolean value) { sp.edit().putBoolean(key, value).commit(); }
    @Override public void putFloat(String key, float value) { sp.edit().putFloat(key, value).commit(); }
    @Override public void putInt(String key, int value) { sp.edit().putInt(key, value).commit(); }
}
