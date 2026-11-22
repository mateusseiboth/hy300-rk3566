package io.github.hy300.settings;

import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.widget.Toast;

import androidx.preference.Preference;
import androidx.preference.PreferenceScreen;
import androidx.preference.SwitchPreference;

import java.util.Locale;

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
            Context app = ctx().getApplicationContext();
            Bg.run(() -> {
                SharedPrefsStore.autoKeystone(app).setEnabled(on);
                if (!on) AutoKeystoneService.removeAuto(app);
            });
            if (on) AutoKeystoneService.start(ctx(), false); else AutoKeystoneService.stop(ctx());
            return true;
        });
        calibrate = action(s, "calibrate", R.string.auto_ks_calibrate, null, () -> {
            AutoKeystoneService.start(ctx(), true);
            Toast.makeText(ctx(), R.string.auto_ks_calibrating, Toast.LENGTH_LONG).show();
            // Com o automático desligado, o serviço só calibra e para.
        });
        invert = toggle(s, "invert", R.string.auto_ks_invert, getString(R.string.auto_ks_invert_summary), (p, v) -> {
            boolean on = (Boolean) v;
            SharedPrefsStore.autoKeystone(ctx()).setInverted(on);
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
        show(SharedPrefsStore.autoKeystone(ctx()));
    }

    private void show(AutoKeystoneState st) {
        if (!isAdded()) return;
        enable.setChecked(st.isEnabled());
        invert.setChecked(st.isInverted());
        String calText = st.isCalibrated()
                ? String.format(Locale.ROOT, "%.1f°", st.getAngle())
                : getString(R.string.auto_ks_not_calibrated);
        calibrate.setSummary(getString(R.string.auto_ks_calibrate_summary, calText));
        float pitch = livePitch;
        String run = getString(Float.isNaN(AutoKeystoneService.lastPitch)
                ? R.string.auto_ks_state_off : R.string.auto_ks_state_on);
        status.setSummary(run + ". " + buildTiltText(pitch, st));
    }

    private String buildTiltText(float pitch, AutoKeystoneState st) {
        if (Float.isNaN(pitch)) return getString(R.string.auto_ks_no_sensor);
        if (!st.isCalibrated()) return getString(R.string.auto_ks_tilt_uncalibrated, pitch);
        return getString(R.string.auto_ks_tilt, pitch, pitch - st.getAngle());
    }
}
