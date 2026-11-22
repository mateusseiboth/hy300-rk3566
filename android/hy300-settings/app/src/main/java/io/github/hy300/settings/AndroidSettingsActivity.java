package io.github.hy300.settings;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ResolveInfo;
import android.os.Bundle;
import android.util.Log;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.List;

/**
 * Trata android.settings.SETTINGS (Projectivy, atalhos "Configurações") e abre as Configurações
 * reais do Android TV. Sem interface: repassa e fecha.
 */
public class AndroidSettingsActivity extends Activity {
    private static final String TAG = "HY300Settings";
    /** Categoria do TvSettings (Intent.CATEGORY_LEANBACK_SETTINGS é @hide no SDK). */
    private static final String CATEGORY_LEANBACK_SETTINGS = "android.intent.category.LEANBACK_SETTINGS";

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        open(this);
        finish();
    }

    /** Abre as Configurações do Android TV. Retorna false se não houver destino. */
    public static boolean open(Context c) {
        String target = AndroidSettingsTarget.choose(findCandidates(c), c.getPackageName());
        if (target == null) {
            Toast.makeText(c, R.string.android_settings_missing, Toast.LENGTH_SHORT).show();
            return false;
        }
        Intent i = new Intent(Intent.ACTION_MAIN)
                .setComponent(ComponentName.unflattenFromString(target))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            c.startActivity(i);
            return true;
        } catch (RuntimeException e) {
            Log.e(TAG, "falha ao abrir " + target, e);
            Toast.makeText(c, R.string.android_settings_missing, Toast.LENGTH_SHORT).show();
            return false;
        }
    }

    private static List<String> findCandidates(Context c) {
        Intent q = new Intent(Intent.ACTION_MAIN).addCategory(CATEGORY_LEANBACK_SETTINGS);
        List<String> out = new ArrayList<>();
        for (ResolveInfo ri : c.getPackageManager().queryIntentActivities(q, 0)) {
            out.add(ri.activityInfo.packageName + "/" + ri.activityInfo.name);
        }
        return out;
    }
}
