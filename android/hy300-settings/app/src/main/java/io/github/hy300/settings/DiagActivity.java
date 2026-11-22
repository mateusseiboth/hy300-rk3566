package io.github.hy300.settings;

import android.app.Activity;
import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;

/** Diagnóstico: verifica se este app consegue gravar props persist.* e o nó do motor. */
public class DiagActivity extends Activity {
    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        TextView tv = new TextView(this);
        tv.setTextSize(20);
        tv.setPadding(48, 48, 48, 48);
        setContentView(tv);
        new Thread(() -> {
            String report = Diag.run();
            Log.i("HY300Diag", report);
            runOnUiThread(() -> tv.setText(report));
        }).start();
    }
}
