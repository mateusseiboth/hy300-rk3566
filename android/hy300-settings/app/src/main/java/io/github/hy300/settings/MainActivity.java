package io.github.hy300.settings;

import android.os.Bundle;
import android.widget.FrameLayout;

import androidx.fragment.app.FragmentActivity;

/** Ponto de entrada: painel de configurações no estilo do Android TV. */
public class MainActivity extends FragmentActivity {
    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        FrameLayout root = new FrameLayout(this);
        root.setId(R.id.settings_root);
        setContentView(root);
        if (b == null) {
            getSupportFragmentManager().beginTransaction()
                    .replace(R.id.settings_root, new SettingsFragment())
                    .commit();
        }
    }
}
