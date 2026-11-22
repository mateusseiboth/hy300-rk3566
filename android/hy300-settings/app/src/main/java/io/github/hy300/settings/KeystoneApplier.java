package io.github.hy300.settings;

import android.util.Log;

import java.util.LinkedHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Grava o keystone em segundo plano. Pedidos rápidos (tecla segurada) são agrupados:
 * só o estado mais recente é gravado.
 */
public final class KeystoneApplier {
    private static final String TAG = "HY300Keystone";
    private static final ExecutorService EXEC = Executors.newSingleThreadExecutor();
    private static final AtomicReference<Keystone> PENDING = new AtomicReference<>();

    private KeystoneApplier() {}

    public static void applyAsync(Keystone k) {
        if (PENDING.getAndSet(k.copy()) == null) {
            EXEC.execute(() -> {
                Keystone next = PENDING.getAndSet(null);
                if (next != null) applyNow(next);
            });
        }
    }

    /** Grava de forma síncrona (não chamar na thread de UI). */
    public static boolean applyNow(Keystone k) {
        LinkedHashMap<String, String> m = k.toProps();
        // O SF relê os cantos na próxima composição em que update=1 e então zera a prop
        // (com a tela parada ela fica em 1 até o próximo quadro). Basta gravar 1 sempre.
        m.put(Keystone.P_UPDATE, "1");
        boolean ok = Sys.setAll(m);
        Log.i(TAG, (ok ? "aplicado: " : "FALHOU: ") + k.describe() + " modo=" + k.mode + " zoom=" + k.zoom);
        return ok;
    }
}
