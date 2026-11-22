package io.github.hy300.settings;

import android.accessibilityservice.AccessibilityService;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.provider.Settings;
import android.text.TextUtils;
import android.util.Log;
import android.view.KeyEvent;
import android.view.accessibility.AccessibilityEvent;

/**
 * Redireciona a tecla F12 (keycode 142, "configurações" do controle IR) para este app.
 *
 * No ROM TXCZ, o PhoneWindowManager.interceptKeyBeforeDispatching chama TxczPwd.setExKey, que abre
 * com.android.tv.settings/com.shzhtxcz.txbox.MainActivity. O filtro de teclas da acessibilidade roda
 * antes do interceptKeyBeforeDispatching; consumindo o evento aqui, o framework não o vê.
 * Não altera o services.jar.
 */
public class F12KeyService extends AccessibilityService {
    public static final int KEYCODE_SETTINGS = KeyEvent.KEYCODE_F12; // 142

    @Override
    protected boolean onKeyEvent(KeyEvent e) {
        if (e.getKeyCode() != KEYCODE_SETTINGS) return false;
        if (e.getAction() == KeyEvent.ACTION_UP) {
            Intent i = new Intent(this, MainActivity.class)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            try {
                startActivity(i);
            } catch (Exception ex) {
                Log.e("HY300F12", "falha ao abrir", ex);
            }
        }
        return true;
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {}

    @Override
    public void onInterrupt() {}

    private static String flat(Context c) {
        return new ComponentName(c, F12KeyService.class).flattenToString();
    }

    public static boolean isEnabled(Context c) {
        String s = Settings.Secure.getString(c.getContentResolver(), Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
        if (s == null) return false;
        String me = flat(c);
        for (String part : s.split(":")) {
            ComponentName cn = ComponentName.unflattenFromString(part);
            if (part.equals(me) || (cn != null && cn.equals(new ComponentName(c, F12KeyService.class)))) return true;
        }
        return false;
    }

    /** Requer WRITE_SECURE_SETTINGS (priv-app ou "pm grant"). */
    public static boolean setEnabled(Context c, boolean on) {
        try {
            String s = Settings.Secure.getString(c.getContentResolver(), Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES);
            StringBuilder out = new StringBuilder();
            String me = flat(c);
            if (s != null) {
                for (String part : s.split(":")) {
                    if (part.isEmpty()) continue;
                    ComponentName cn = ComponentName.unflattenFromString(part);
                    if (part.equals(me) || (cn != null && cn.equals(new ComponentName(c, F12KeyService.class)))) continue;
                    if (out.length() > 0) out.append(':');
                    out.append(part);
                }
            }
            if (on) {
                if (out.length() > 0) out.append(':');
                out.append(me);
            }
            Settings.Secure.putString(c.getContentResolver(), Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES, out.toString());
            Settings.Secure.putInt(c.getContentResolver(), Settings.Secure.ACCESSIBILITY_ENABLED,
                    TextUtils.isEmpty(out) ? 0 : 1);
            return true;
        } catch (SecurityException e) {
            return false;
        }
    }
}
