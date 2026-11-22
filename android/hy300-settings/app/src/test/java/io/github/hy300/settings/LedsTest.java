package io.github.hy300.settings;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.HashMap;
import java.util.Map;

import org.junit.Test;

public class LedsTest {
    @Test
    public void pathOfIndicatorLeds() {
        assertEquals("/sys/class/leds/green/brightness", Leds.pathOf(Leds.GREEN));
        assertEquals("/sys/class/leds/red/brightness", Leds.pathOf(Leds.RED));
    }

    /** Lcd_power é a fonte de luz e Fan_h a ventoinha: o app nunca escreve nesses nós. */
    @Test(expected = IllegalArgumentException.class)
    public void lightSourceIsNeverControllable() {
        Leds.pathOf("Lcd_power");
    }

    @Test(expected = IllegalArgumentException.class)
    public void fanIsNeverControllable() {
        Leds.pathOf("Fan_h");
    }

    @Test
    public void valueOfState() {
        assertEquals("255", Leds.valueOf(true));
        assertEquals("0", Leds.valueOf(false));
    }

    @Test
    public void bootRewritesOnlyLedsTurnedOff() {
        Map<String, Boolean> wanted = new HashMap<>();
        wanted.put(Leds.GREEN, false);
        wanted.put(Leds.RED, true);
        wanted.put("Lcd_power", false);
        Map<String, String> writes = Leds.buildBootWrites(wanted);
        assertEquals(1, writes.size());
        assertEquals("0", writes.get("/sys/class/leds/green/brightness"));
        assertFalse(writes.containsKey("/sys/class/leds/Lcd_power/brightness"));
    }

    @Test
    public void isOnReadsBrightness() {
        assertTrue(Leds.isOn("255"));
        assertTrue(Leds.isOn("1"));
        assertFalse(Leds.isOn("0"));
        assertTrue(Leds.isOn(null));   // padrão do device tree: ligado
    }
}
