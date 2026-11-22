package io.github.hy300.settings;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** No boot: religa o keystone automático, se ativado neste app (desligado por padrão). */
public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context c, Intent intent) {
        PendingResult pr = goAsync();
        Context app = c.getApplicationContext();
        new Thread(() -> {
            try {
                if (SharedPrefsStore.autoKeystone(app).isEnabled()) {
                    AutoKeystoneService.start(app, false);
                }
            } finally {
                pr.finish();
            }
        }).start();
    }
}
