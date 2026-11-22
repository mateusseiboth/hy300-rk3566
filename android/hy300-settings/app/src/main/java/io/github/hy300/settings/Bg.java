package io.github.hy300.settings;

import android.os.Handler;
import android.os.Looper;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.function.Consumer;
import java.util.function.Supplier;

/** Execução em segundo plano com retorno na thread principal. */
public final class Bg {
    private static final ExecutorService EXEC = Executors.newSingleThreadExecutor();
    private static final Handler MAIN = new Handler(Looper.getMainLooper());

    private Bg() {}

    public static void run(Runnable r) { EXEC.execute(r); }

    public static <T> void load(Supplier<T> work, Consumer<T> onMain) {
        EXEC.execute(() -> {
            T v = work.get();
            MAIN.post(() -> onMain.accept(v));
        });
    }
}
