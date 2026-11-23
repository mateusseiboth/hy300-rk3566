package io.github.hy300.settings;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.HashMap;
import java.util.Map;

import org.junit.Test;

public class RkDisplayTest {
    /** ROM de fábrica: as props que o HWC da Rockchip lê. */
    @Test
    public void factoryRomUsesTheRockchipHwcProps() {
        assertEquals("persist.vendor.brightness.main", RkDisplay.prop(0, false));
        assertEquals("persist.vendor.hue.main", RkDisplay.prop(3, false));
    }

    /** LineageOS: props do sistema que o drm_hwcomposer do HY300 lê (o sistema não grava props do vendor). */
    @Test
    public void lineageUsesTheSystemPictureProps() {
        assertEquals("persist.sys.hy300.picture.brightness", RkDisplay.prop(0, true));
        assertEquals("persist.sys.hy300.picture.saturation", RkDisplay.prop(2, true));
    }

    @Test
    public void lineageIsDetectedByItsVersionProp() {
        Map<String, String> props = new HashMap<>();
        assertFalse(RkDisplay.isLineage(props));
        props.put("ro.lineage.version", "24.0-20261123-UNOFFICIAL-hy300");
        assertTrue(RkDisplay.isLineage(props));
    }

    /** Só o HWC da Rockchip precisa do gatilho vendor.display.timeline. */
    @Test
    public void timelineOnlyOnTheFactoryRom() {
        assertTrue(RkDisplay.needsTimeline(false));
        assertFalse(RkDisplay.needsTimeline(true));
    }
}
