package io.github.hy300.settings;

import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Handler;
import android.os.Looper;
import android.widget.Toast;

import androidx.preference.Preference;
import androidx.preference.PreferenceScreen;
import androidx.preference.SwitchPreference;

import java.util.Locale;
import java.util.Map;

public class AutoKeystoneFragment extends BasePrefs implements SensorEventListener {
    private volatile float livePitch = Float.NaN;
    private SwitchPreference enable, invert;
    private Preference calibrate, status;
    private final Handler h = new Handler(Looper.getMainLooper());
    private final Runnable tick = new Runnable() {
        @Override
        public void run() {
            refresh();
            h.postDelayed(this, 1000);
        }
    };

    @Override
    protected void build(PreferenceScreen s) {
        s.setTitle(R.string.cat_auto_ks);
        enable = toggle(s, "enable", R.string.auto_ks_enable, getString(R.string.auto_ks_enable_summary), (p, v) -> {
            boolean on = (Boolean) v;
            Bg.run(() -> {
                Sys.set(AutoKeystoneService.P_ENABLE, on ? "1" : "0");
                if (!on) AutoKeystoneService.removeAuto(ctx());
            });
            if (on) AutoKeystoneService.start(ctx(), false); else AutoKeystoneService.stop(ctx());
            return true;
        });
        calibrate = action(s, "calibrate", R.string.auto_ks_calibrate, null, () -> {
            AutoKeystoneService.start(ctx(), true);
            Toast.makeText(ctx(), R.string.auto_ks_calibrating, Toast.LENGTH_LONG).show();
            // Se o automático estiver desligado, o serviço calibra e pode ser parado depois.
        });
        invert = toggle(s, "invert", R.string.auto_ks_invert, getString(R.string.auto_ks_invert_summary), (p, v) -> {
            boolean on = (Boolean) v;
            Bg.run(() -> Sys.set(AutoKeystoneService.P_INVERT, on ? "1" : "0"));
            if (enable.isChecked()) AutoKeystoneService.start(ctx(), false);
            return true;
        });
        status = new Preference(ctx());
        status.setTitle(R.string.auto_ks_status);
        status.setSelectable(false);
        status.setPersistent(false);
        s.addPreference(status);
    }

    @Override
    public void onResume() {
        super.onResume();
        h.post(tick);
        SensorManager sm = (SensorManager) ctx().getSystemService(android.content.Context.SENSOR_SERVICE);
        Sensor acc = sm.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
        if (acc != null) sm.registerListener(this, acc, SensorManager.SENSOR_DELAY_NORMAL);
    }

    @Override
    public void onSensorChanged(SensorEvent e) {
        float x = e.values[0], y = e.values[1], z = e.values[2];
        float g = (float) Math.sqrt(x * x + y * y + z * z);
        if (g > 0) livePitch = (float) Math.toDegrees(Math.asin(-y / g));
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {}

    @Override
    public void onPause() {
        ((SensorManager) ctx().getSystemService(android.content.Context.SENSOR_SERVICE)).unregisterListener(this);
        h.removeCallbacks(tick);
        super.onPause();
    }

    private void refresh() {
        Bg.load(Sys::getAll, this::show);
    }

    private void show(Map<String, String> p) {
        if (!isAdded()) return;
        boolean on = Sys.getInt(p, AutoKeystoneService.P_ENABLE, 0) == 1;
        enable.setChecked(on);
        invert.setChecked(Sys.getInt(p, AutoKeystoneService.P_INVERT, 0) == 1);
        boolean cal = Sys.getInt(p, AutoKeystoneService.P_BDSTATE, 0) == 1;
        String calText = cal
                ? String.format(Locale.ROOT, "%.1f°", Sys.getFloat(p, AutoKeystoneService.P_ANGLE, 0))
                : getString(R.string.auto_ks_not_calibrated);
        calibrate.setSummary(getString(R.string.auto_ks_calibrate_summary, calText));
        float pitch = livePitch;
        String run = Float.isNaN(AutoKeystoneService.lastPitch) ? "serviço parado" : "serviço ativo";
        String st = Float.isNaN(pitch) ? "sem leitura do acelerômetro"
                : String.format(Locale.ROOT, "inclinação %.1f°, em relação à calibração %+.1f°", pitch,
                pitch - Sys.getFloat(p, AutoKeystoneService.P_ANGLE, 0));
        status.setSummary(run + " · " + st);
    }
}
