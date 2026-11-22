package io.github.hy300.settings;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.HashMap;
import java.util.Map;

import org.junit.Test;

public class AutoKeystoneStateTest {
    /** Store em memória, no lugar do SharedPreferences. */
    static final class MapStore implements AutoKeystoneState.Store {
        final Map<String, Object> values = new HashMap<>();

        @Override public boolean getBoolean(String k, boolean d) { return (Boolean) values.getOrDefault(k, d); }
        @Override public float getFloat(String k, float d) { return (Float) values.getOrDefault(k, d); }
        @Override public int getInt(String k, int d) { return (Integer) values.getOrDefault(k, d); }
        @Override public void putBoolean(String k, boolean v) { values.put(k, v); }
        @Override public void putFloat(String k, float v) { values.put(k, v); }
        @Override public void putInt(String k, int v) { values.put(k, v); }
    }

    @Test
    public void startsDisabledAndUncalibrated() {
        AutoKeystoneState s = new AutoKeystoneState(new MapStore());
        assertFalse(s.isEnabled());
        assertFalse(s.isCalibrated());
        assertFalse(s.isInverted());
        assertFalse(s.shouldApply());
    }

    @Test
    public void enableUsesOwnKeyOnly() {
        MapStore store = new MapStore();
        AutoKeystoneState s = new AutoKeystoneState(store);
        s.setEnabled(true);
        assertTrue(s.isEnabled());
        assertEquals(1, store.values.size());
        assertTrue(store.values.containsKey(AutoKeystoneState.K_ENABLED));
        assertFalse(AutoKeystoneState.K_ENABLED.contains("txcz"));
    }

    @Test
    public void appliesOnlyWhenEnabledAndCalibrated() {
        AutoKeystoneState s = new AutoKeystoneState(new MapStore());
        s.calibrate(12.5f);
        assertFalse(s.shouldApply());
        s.setEnabled(true);
        assertTrue(s.shouldApply());
        s.setEnabled(false);
        assertFalse(s.shouldApply());
    }

    @Test
    public void calibrationResetsLastAngle() {
        AutoKeystoneState s = new AutoKeystoneState(new MapStore());
        s.setPreAngle(7f);
        s.calibrate(30f);
        assertTrue(s.isCalibrated());
        assertEquals(30f, s.getAngle(), 0f);
        assertEquals(0f, s.getPreAngle(), 0f);
    }

    @Test
    public void contributionIsSwappedKeepingManualAdjustment() {
        AutoKeystoneState s = new AutoKeystoneState(new MapStore());
        Keystone k = new Keystone();
        k.user[Keystone.LT][0] = 10;           // ajuste manual
        int[][] first = new int[4][2];
        first[Keystone.LT][0] = 42;
        first[Keystone.LT][1] = -47;
        s.applyContribution(k, first);
        assertArrayEquals(new int[]{52, -47}, k.user[Keystone.LT]);
        assertArrayEquals(first, s.getContribution());

        s.applyContribution(k, new int[4][2]); // retira
        assertArrayEquals(new int[]{10, 0}, k.user[Keystone.LT]);
        assertArrayEquals(new int[4][2], s.getContribution());
    }

    @Test
    public void forgetContributionKeepsCorners() {
        AutoKeystoneState s = new AutoKeystoneState(new MapStore());
        Keystone k = new Keystone();
        int[][] add = new int[4][2];
        add[Keystone.LB][0] = 8;
        s.applyContribution(k, add);
        s.forgetContribution();
        assertArrayEquals(new int[4][2], s.getContribution());
        assertArrayEquals(new int[]{8, 0}, k.user[Keystone.LB]);
    }
}
