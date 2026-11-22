package io.github.hy300.settings;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * LEDs indicadores do gpio-leds (green, red). Os nós são 0644 system; o
 * system/hy300-settings.rc (instalado por install-system.sh) dá 0666 no boot.
 *
 * Fan_h (ventoinha) e Lcd_power (fonte de luz) ficam de fora de propósito: desligar a
 * ventoinha com a luz acesa aquece o projetor, e a TXCZ só fazia isso no modo caixa de som,
 * com a luz apagada. O valor volta para "ligado" a cada boot (default-state do DT), então o
 * BootReceiver reaplica o que o usuário desligou.
 */
public final class Leds {
    public static final String GREEN = "green";
    public static final String RED = "red";
    public static final List<String> CONTROLLABLE = Collections.unmodifiableList(Arrays.asList(GREEN, RED));

    private Leds() {}

    public static String pathOf(String led) {
        if (!CONTROLLABLE.contains(led)) throw new IllegalArgumentException("LED não controlável: " + led);
        return "/sys/class/leds/" + led + "/brightness";
    }

    public static String valueOf(boolean on) {
        return on ? "255" : "0";
    }

    /** Leitura do nó; sem leitura, vale o padrão do device tree (ligado). */
    public static boolean isOn(String brightness) {
        if (brightness == null) return true;
        return !"0".equals(brightness.trim());
    }

    /** Escritas do boot: só os LEDs controláveis que o usuário desligou. */
    public static Map<String, String> buildBootWrites(Map<String, Boolean> wanted) {
        Map<String, String> out = new LinkedHashMap<>();
        for (String led : CONTROLLABLE) {
            if (Boolean.FALSE.equals(wanted.get(led))) out.put(pathOf(led), valueOf(false));
        }
        return out;
    }
}
