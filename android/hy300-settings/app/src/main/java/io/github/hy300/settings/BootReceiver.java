package io.github.hy300.settings;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** No boot: religa o keystone automático (se ativado). */
public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context c, Intent intent) {
        PendingResult pr = goAsync();
        Context app = c.getApplicationContext();
        new Thread(() -> {
            try {
                if ("1".equals(Sys.get(AutoKeystoneService.P_ENABLE, "0"))) {
                    AutoKeystoneService.start(app, false);
                }
            } finally {
                pr.finish();
            }
        }).start();
    }
}
