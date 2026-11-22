package io.github.hy300.settings;

/**
 * Estado do keystone automático, guardado só neste app (SharedPreferences "autoks").
 *
 * Liga/desliga, calibração e a contribuição atual nos cantos ficam no MESMO arquivo de
 * propósito: se os dados do app forem apagados, some tudo junto, e o automático volta
 * desligado e sem calibração. Com uma prop persist.*, o "ligado" sobreviveria à perda da
 * contribuição, e a próxima correção seria somada sobre a antiga já gravada nos cantos.
 * Também não usa persist.txcz.tt.*: o TaitouService da TXCZ liga no boot por
 * persist.txcz.tt.enable, e dividir a chave fazia os dois rodarem juntos.
 */
public final class AutoKeystoneState {
    /** Subconjunto do SharedPreferences usado aqui (permite teste na JVM). */
    public interface Store {
        boolean getBoolean(String key, boolean def);
        float getFloat(String key, float def);
        int getInt(String key, int def);
        void putBoolean(String key, boolean value);
        void putFloat(String key, float value);
        void putInt(String key, int value);
    }

    public static final String FILE = "autoks";
    static final String K_ENABLED = "enabled";
    static final String K_CALIBRATED = "calibrated";
    static final String K_ANGLE = "angle";
    static final String K_PRE_ANGLE = "preAngle";
    static final String K_INVERT = "invert";

    private final Store store;

    public AutoKeystoneState(Store store) {
        this.store = store;
    }

    public boolean isEnabled() { return store.getBoolean(K_ENABLED, false); }
    public void setEnabled(boolean on) { store.putBoolean(K_ENABLED, on); }

    public boolean isCalibrated() { return store.getBoolean(K_CALIBRATED, false); }
    public float getAngle() { return store.getFloat(K_ANGLE, 0f); }

    public boolean isInverted() { return store.getBoolean(K_INVERT, false); }
    public void setInverted(boolean on) { store.putBoolean(K_INVERT, on); }

    public float getPreAngle() { return store.getFloat(K_PRE_ANGLE, 0f); }
    public void setPreAngle(float a) { store.putFloat(K_PRE_ANGLE, a); }

    /** Só corrige os cantos com o automático ligado E calibrado. */
    public boolean shouldApply() { return isEnabled() && isCalibrated(); }

    public void calibrate(float angle) {
        store.putFloat(K_ANGLE, angle);
        store.putBoolean(K_CALIBRATED, true);
        store.putFloat(K_PRE_ANGLE, 0f);
    }

    /** Contribuição automática atual por canto, coordenadas do espectador: [canto][x,y]. */
    public int[][] getContribution() {
        int[][] o = new int[4][2];
        for (int c = 0; c < 4; c++) {
            o[c][0] = store.getInt("x" + c, 0);
            o[c][1] = store.getInt("y" + c, 0);
        }
        return o;
    }

    private void saveContribution(int[][] add) {
        for (int c = 0; c < 4; c++) {
            store.putInt("x" + c, add[c][0]);
            store.putInt("y" + c, add[c][1]);
        }
    }

    /** Troca a contribuição anterior pela nova em k (o ajuste manual fica). */
    public void applyContribution(Keystone k, int[][] add) {
        int[][] old = getContribution();
        for (int c = 0; c < 4; c++) {
            k.user[c][0] += add[c][0] - old[c][0];
            k.user[c][1] += add[c][1] - old[c][1];
        }
        k.clamp();
        saveContribution(add);
    }

    /** Ao restaurar o keystone manualmente: a contribuição deixa de existir nos cantos. */
    public void forgetContribution() {
        saveContribution(new int[4][2]);
    }
}
