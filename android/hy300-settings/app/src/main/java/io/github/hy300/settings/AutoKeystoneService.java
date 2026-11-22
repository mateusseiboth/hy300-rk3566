package io.github.hy300.settings;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;
import android.widget.Toast;


/**
 * Keystone automático pelo acelerômetro. Reimplementa o mecanismo do TaitouService do app TXCZ
 * (ver reverse-engineering/txcz-settings/README.md §2), com duas diferenças:
 * <ul>
 *   <li>a correção automática é SOMADA aos ajustes manuais (a contribuição anterior do automático é
 *       retirada antes de aplicar a nova), em vez de sobrescrever os cantos;</li>
 *   <li>os cantos são recalculados a partir de base(modo, zoom) como no resto do app.</li>
 * </ul>
 * Estado (liga/desliga, calibração, inverter, contribuição) em {@link AutoKeystoneState}, só deste
 * app. Não lê nem grava persist.txcz.tt.*, que é do TaitouService da TXCZ.
 */
public class AutoKeystoneService extends Service implements SensorEventListener {
    private static final String TAG = "HY300AutoKs";
    public static final String EXTRA_CALIBRATE = "calibrate";

    private static final String CHANNEL = "auto_keystone";
    private static final float STABLE = 0.3f;

    /** Último pitch lido (para a UI). NaN se o serviço não estiver rodando. */
    public static volatile float lastPitch = Float.NaN;

    private SensorManager sm;
    private HandlerThread thread;
    private Handler bg;
    private final float[] acc = new float[3];
    private int samples, stableCount;
    private AutoKeystoneState state;
    private float calAngle, preAngle;
    private boolean calibrateRequested, afterMove, invert;
    private int currentRounded = Integer.MIN_VALUE;

    public static void start(Context c, boolean calibrate) {
        Intent i = new Intent(c, AutoKeystoneService.class);
        if (calibrate) i.putExtra(EXTRA_CALIBRATE, true);
        c.startForegroundService(i);
    }

    public static void stop(Context c) {
        c.stopService(new Intent(c, AutoKeystoneService.class));
    }

    @Override
    public void onCreate() {
        super.onCreate();
        state = SharedPrefsStore.autoKeystone(this);
        startForeground(1, buildNotification());
        thread = new HandlerThread("autoks");
        thread.start();
        bg = new Handler(thread.getLooper());
        bg.post(this::loadProps);
        sm = (SensorManager) getSystemService(SENSOR_SERVICE);
        Sensor s = sm.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
        if (s == null) {
            Log.e(TAG, "sem acelerômetro");
            stopSelf();
            return;
        }
        sm.registerListener(this, s, SensorManager.SENSOR_DELAY_NORMAL, bg);
    }

    private void loadProps() {
        calAngle = state.getAngle();
        preAngle = state.getPreAngle();
        invert = state.isInverted();
    }

    private Notification buildNotification() {
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel(CHANNEL,
                getString(R.string.auto_ks_title), NotificationManager.IMPORTANCE_MIN));
        PendingIntent pi = PendingIntent.getActivity(this, 0,
                new Intent(this, MainActivity.class), PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this, CHANNEL)
                .setSmallIcon(R.drawable.ic_projector)
                .setContentTitle(getString(R.string.auto_ks_title))
                .setContentText(getString(R.string.auto_ks_running))
                .setContentIntent(pi)
                .setOngoing(true)
                .build();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && intent.getBooleanExtra(EXTRA_CALIBRATE, false)) {
            bg.post(() -> calibrateRequested = true);
        }
        bg.post(this::loadProps);
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        if (sm != null) sm.unregisterListener(this);
        lastPitch = Float.NaN;
        if (thread != null) thread.quitSafely();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {}

    @Override
    public void onSensorChanged(SensorEvent e) {
        float x = e.values[0], y = e.values[1], z = e.values[2];
        if (samples < 2) {
            acc[0] += x; acc[1] += y; acc[2] += z;
            samples++;
            return;
        }
        float ax = acc[0] / 2, ay = acc[1] / 2, az = acc[2] / 2;
        boolean stable = Math.abs(ax - x) < STABLE && Math.abs(ay - y) < STABLE && Math.abs(az - z) < STABLE;
        float g = (float) Math.sqrt(x * x + y * y + z * z);
        float pitch = (float) Math.toDegrees(Math.asin(-y / g));
        lastPitch = pitch;
        acc[0] = acc[1] = acc[2] = 0;
        samples = 0;
        if (stable) {
            if (++stableCount >= 3) {
                stableCount = 0;
                onStable(pitch);
            }
        } else {
            stableCount = 0;
            onMoving(pitch);
        }
    }

    private void onMoving(float pitch) {
        if (!state.shouldApply()) return;
        float a = pitch - calAngle;
        if (Math.abs(preAngle - a) >= 4f) {
            apply(Math.round(a));
            afterMove = true;
        }
    }

    private void onStable(float pitch) {
        if (calibrateRequested) {
            calibrate(pitch);
        }
        if (!state.shouldApply()) {
            stopIfDisabled();
            return;
        }
        float a = pitch - calAngle;
        if (Math.abs(preAngle - a) >= 2f || afterMove) {
            afterMove = false;
            preAngle = a;
            state.setPreAngle(a);
            apply(Math.round(a));
        }
    }

    private void calibrate(float pitch) {
        calAngle = pitch;
        calibrateRequested = false;
        preAngle = 0;
        currentRounded = Integer.MIN_VALUE;
        state.calibrate(pitch);
        Log.i(TAG, "calibrado em " + pitch);
        new Handler(Looper.getMainLooper()).post(() ->
                Toast.makeText(this, getString(R.string.auto_ks_calibrated, pitch), Toast.LENGTH_SHORT).show());
        afterMove = true;
    }

    /** Calibrar com o automático desligado: calibra e para, sem mexer nos cantos. */
    private void stopIfDisabled() {
        if (state.isEnabled() || calibrateRequested) return;
        stopSelf();
    }

    /** Offsets automáticos (coordenadas do espectador) para o ângulo a. [canto][x,y] */
    static int[][] offsetsFor(int a, int mode, boolean invert, float calAngle) {
        if (calAngle > 60) a = -a;          // apontado para o teto (mesma regra do TXCZ)
        if (mode == Keystone.MODE_CEIL_FRONT || mode == Keystone.MODE_CEIL_REAR) a = -a;
        if (invert) a = -a;
        int[][] o = new int[4][2];
        int v;
        boolean top;
        if (a >= 45 && a <= 135) {         // projetando no teto
            int d = 90 - a;
            v = (int) Math.floor(Math.abs(d * 3.9));
            top = d < 0;
        } else {
            v = (int) Math.floor(Math.abs(a * 4.2));
            top = a >= 0;
        }
        int vH = Math.floorDiv(Keystone.H * v * 2, Keystone.W);
        if (v == 0) return o;
        int[] cs = top ? new int[]{Keystone.LT, Keystone.RT} : new int[]{Keystone.LB, Keystone.RB};
        for (int c : cs) {
            o[c][0] = v * Keystone.inX(c);
            o[c][1] = vH * Keystone.inY(c);
        }
        return o;
    }

    private void apply(int a) {
        if (a == currentRounded) return;
        currentRounded = a;
        Keystone k = Keystone.fromProps(Sys.getAll());
        int[][] add = offsetsFor(a, k.mode, invert, calAngle);
        replaceAuto(this, k, add);
        Log.i(TAG, "a=" + a + " -> " + k.describe());
    }

    /** Troca a contribuição automática anterior pela nova e grava. */
    static void replaceAuto(Context c, Keystone k, int[][] add) {
        SharedPrefsStore.autoKeystone(c).applyContribution(k, add);
        KeystoneApplier.applyNow(k);
    }

    /** Ao desligar: retira a contribuição automática (mantém o ajuste manual). */
    static void removeAuto(Context c) {
        Keystone k = Keystone.fromProps(Sys.getAll());
        replaceAuto(c, k, new int[4][2]);
    }

    /** Ao restaurar o keystone manualmente: esquece a contribuição automática. */
    static void forgetAuto(Context c) {
        SharedPrefsStore.autoKeystone(c).forgetContribution();
    }
}
