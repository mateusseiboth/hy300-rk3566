package io.github.hy300.settings;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class SourceTest {
    /** No LineageOS a entrada HDMI é a tela do TV input do HY300; na fábrica, o app de câmera. */
    @Test
    public void lineageHdmiScreenComesBeforeTheFactoryCamera() {
        assertEquals("io.github.hy300.hdmi", Source.HDMI_TARGETS[0][0]);
        assertEquals("io.github.hy300.hdmi.HdmiActivity", Source.HDMI_TARGETS[0][1]);
        assertEquals(Source.HDMI_PKG, Source.HDMI_TARGETS[1][0]);
    }
}
