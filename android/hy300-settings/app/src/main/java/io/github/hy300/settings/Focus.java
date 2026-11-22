package io.github.hy300.settings;

import android.os.Handler;
import android.os.HandlerThread;
import android.util.Log;

/**
 * Motor de foco (driver de kernel "usb-cam-gpio", nó sysfs 0777).
 *
 * O {@code motor_store} do kernel compara a string inteira com strcmp (sem tolerar '\n'):
 * {@code user_cw}/{@code user_ccw} = 10 passos síncronos em cada sentido; {@code aacw}/{@code aaccw}
 * = movimento contínuo; {@code aastop} = parar; {@code aacw_end}/{@code aaccw_end} = até o fim.
 * Depois de tratar o comando, a função tenta {@code kstrtoint} no buffer e devolve -EINVAL
 * para qualquer string não numérica, então a escrita "falha" mesmo quando o motor andou.
 * "stop" (sem prefixo) não é reconhecido. Ver README.
 */
public final class Focus {
    public static final String MOTOR = "/sys/class/motor_cc/motor_cc/motor";
    public static final String LIMIT = "/sys/class/motor_cc/motor_cc/hd_camera_on";
    public static final long REPEAT_MS = 60;
    private static final String TAG = "HY300Focus";

    public interface Listener {
        void onLimit();
    }

    private final HandlerThread thread = new HandlerThread("focus");
    private final Handler handler;
    private volatile int dir; // +1 = cw, -1 = ccw, 0 = parado
    private Listener listener;

    public Focus() {
        thread.start();
        handler = new Handler(thread.getLooper());
    }

    public void setListener(Listener l) { listener = l; }

    private final Runnable stepper = new Runnable() {
        @Override
        public void run() {
            int d = dir;
            if (d == 0) return;
            if ("1".equals(Sys.readFile(LIMIT))) {
                Log.i(TAG, "fim de curso");
                dir = 0;
                write("aastop");
                Listener l = listener;
                if (l != null) l.onLimit();
                return;
            }
            write(d > 0 ? "user_cw" : "user_ccw");
            handler.postDelayed(this, REPEAT_MS);
        }
    };

    /** Começa a girar (repete a cada 60 ms até {@link #stop()}). */
    public void start(int direction) {
        if (dir == direction) return;
        dir = direction;
        handler.removeCallbacks(stepper);
        handler.post(stepper);
    }

    /** Um único pulso (10 passos do driver). */
    public void stepOnce(int direction) {
        handler.post(() -> write(direction > 0 ? "user_cw" : "user_ccw"));
    }

    public void stop() {
        dir = 0;
        handler.removeCallbacks(stepper);
        handler.post(() -> write("aastop"));
    }

    public void release() {
        stop();
        thread.quitSafely();
    }

    public static boolean available() {
        return new java.io.File(MOTOR).exists();
    }

    private static void write(String cmd) {
        // EINVAL é esperado (ver comentário da classe); não dá para distinguir de erro real.
        Sys.writeFile(MOTOR, cmd);
    }
}
