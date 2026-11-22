package io.github.hy300.settings;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

import org.junit.Test;

public class KeystoneTest {
    private static Map<String, String> props(int mode, int zoom, String lt, String lb, String rt, String rb) {
        Map<String, String> p = new HashMap<>();
        p.put(Keystone.P_MODE, String.valueOf(mode));
        p.put(Keystone.P_ZOOM, String.valueOf(zoom));
        p.put("persist.sys.keystone.lt", lt);
        p.put("persist.sys.keystone.lb", lb);
        p.put("persist.sys.keystone.rt", rt);
        p.put("persist.sys.keystone.rb", rb);
        return p;
    }

    @Test
    public void basesMatchTxcz() {
        Keystone k = new Keystone();
        k.mode = 2; k.zoom = 100;
        assertArrayEquals(new int[]{1280, -720}, k.base(Keystone.LT));
        assertArrayEquals(new int[]{1280, 720}, k.base(Keystone.LB));
        assertArrayEquals(new int[]{-1280, -720}, k.base(Keystone.RT));
        assertArrayEquals(new int[]{-1280, 720}, k.base(Keystone.RB));
        // valor real do aparelho: teto frontal, zoom 70 -> init 1088,-612
        k.zoom = 70;
        assertArrayEquals(new int[]{1088, -612}, k.base(Keystone.LT));
        // mesa frontal zoom 90 (MAP.md)
        k.mode = 0; k.zoom = 90;
        assertArrayEquals(new int[]{64, -36}, k.base(Keystone.LT));
        assertArrayEquals(new int[]{-64, 36}, k.base(Keystone.RB));
        // 4:3 zoom 100
        k.ratio = 1; k.zoom = 100;
        assertArrayEquals(new int[]{160, 0}, k.base(Keystone.LT));
        // y_mirror / x_mirror
        k.ratio = 0; k.mode = 3;
        assertArrayEquals(new int[]{0, -720}, k.base(Keystone.LT));
        k.mode = 1;
        assertArrayEquals(new int[]{1280, 0}, k.base(Keystone.LT));
    }

    @Test
    public void roundTripPreservesUserAdjustments() {
        Map<String, String> p = props(2, 100, "1260,-700", "1270,710", "-1265,-705", "-1280,720");
        Keystone k = Keystone.fromProps(p);
        // lt deslocado 20 px para dentro (espectador: direita e para baixo)
        assertEquals(20, k.user[Keystone.LT][0]);
        assertEquals(-20, k.user[Keystone.LT][1]);
        LinkedHashMap<String, String> out = k.toProps();
        assertEquals("1260,-700", out.get("persist.sys.keystone.lt"));
        assertEquals("1270,710", out.get("persist.sys.keystone.lb"));
        assertEquals("-1265,-705", out.get("persist.sys.keystone.rt"));
        assertEquals("-1280,720", out.get("persist.sys.keystone.rb"));
        assertEquals("1280,-720", out.get("persist.sys.keystone.lt.init.xy"));
    }

    @Test
    public void zoomKeepsAdjustments() {
        Keystone k = Keystone.fromProps(props(2, 100, "1260,-700", "1280,720", "-1280,-720", "-1280,720"));
        k.setZoom(90);
        // base lt em zoom 90 (teto): 1216,-684 ; ajuste (-20,+20) em prop
        assertArrayEquals(new int[]{1196, -664}, k.corner(Keystone.LT));
        k.setZoom(100);
        assertArrayEquals(new int[]{1260, -700}, k.corner(Keystone.LT));
    }

    @Test
    public void modeChangeKeepsViewerAdjustment() {
        Keystone k = Keystone.fromProps(props(0, 100, "20,-20", "0,0", "0,0", "0,0"));
        assertEquals(20, k.user[Keystone.LT][0]);
        k.mode = 2;
        assertArrayEquals(new int[]{1260, -700}, k.corner(Keystone.LT));
    }

    @Test
    public void trapezoidIsReversible() {
        Keystone k = Keystone.fromProps(props(2, 100, "1280,-720", "1280,720", "-1280,-720", "-1280,720"));
        k.setTrapV(10);
        assertArrayEquals(new int[]{1270, -710}, k.corner(Keystone.LT));
        assertArrayEquals(new int[]{-1270, -710}, k.corner(Keystone.RT));
        k.setTrapV(-10);
        assertArrayEquals(new int[]{1280, -720}, k.corner(Keystone.LT));
        assertArrayEquals(new int[]{1270, 710}, k.corner(Keystone.LB));
        k.setTrapV(0);
        k.setTrapH(5);
        k.setTrapH(0);
        for (int c = 0; c < 4; c++) assertArrayEquals(new int[]{0, 0}, k.user[c]);
    }

    /**
     * Mesma regra do ProjectorVerticalActivity do TXCZ (bytecode): offsetx é o trapézio vertical
     * (positivo estreita o topo), offsety é o horizontal (positivo estreita a direita), e cada
     * unidade move os dois cantos 1 px em x e 1 px em y.
     */
    @Test
    public void trapezoidFollowsTxczCounters() {
        Keystone k = Keystone.fromProps(props(0, 100, "0,0", "0,0", "0,0", "0,0"));
        k.setTrapV(5);
        assertArrayEquals(new int[]{5, -5}, k.corner(Keystone.LT));
        assertArrayEquals(new int[]{-5, -5}, k.corner(Keystone.RT));
        k.setTrapV(0);
        k.setTrapH(5);
        assertArrayEquals(new int[]{-5, -5}, k.corner(Keystone.RT));
        assertArrayEquals(new int[]{-5, 5}, k.corner(Keystone.RB));
        assertArrayEquals(new int[]{0, 0}, k.corner(Keystone.LT));
        k.setTrapH(-5);
        assertArrayEquals(new int[]{5, -5}, k.corner(Keystone.LT));
        assertArrayEquals(new int[]{5, 5}, k.corner(Keystone.LB));
        assertArrayEquals(new int[]{0, 0}, k.corner(Keystone.RT));
    }

    @Test
    public void trapezoidLeftByTxczIsUndone() {
        Map<String, String> p = props(0, 100, "5,-5", "0,0", "-5,-5", "0,0");
        p.put(Keystone.P_TRAP_X, "5");
        Keystone k = Keystone.fromProps(p);
        k.setTrapV(0);
        for (int c = 0; c < 4; c++) assertArrayEquals(new int[]{0, 0}, k.corner(c));
    }

    @Test
    public void arrowsMoveTrapezoidLikeTxcz() {
        Keystone k = Keystone.fromProps(props(0, 100, "0,0", "0,0", "0,0", "0,0"));
        k.nudgeTrapezoid(0, 1, 5);   // cima
        assertEquals(5, k.trapV);
        k.nudgeTrapezoid(0, -1, 5);  // baixo
        assertEquals(0, k.trapV);
        k.nudgeTrapezoid(1, 0, 5);   // direita estreita a borda direita
        assertEquals(5, k.trapH);
        assertArrayEquals(new int[]{-5, -5}, k.corner(Keystone.RT));
        k.nudgeTrapezoid(-1, 0, 20); // esquerda
        assertEquals(-15, k.trapH);
    }

    @Test
    public void clampKeepsInsidePanel() {
        Keystone k = Keystone.fromProps(props(0, 100, "0,0", "0,0", "0,0", "0,0"));
        k.moveCorner(Keystone.LT, -50, 50); // para fora: não pode
        assertArrayEquals(new int[]{0, 0}, k.corner(Keystone.LT));
        k.moveCorner(Keystone.LT, 2000, 0); // para dentro além de 1/3
        assertEquals(1280 / 3, k.corner(Keystone.LT)[0]);
    }

    @Test
    public void autoOffsetsMatchTaitou() {
        // a=10° parede, mesa frontal: v=42, vH=47 no topo (README §2)
        int[][] o = AutoKeystoneService.offsetsFor(10, 0, false, 0f);
        assertArrayEquals(new int[]{42, -47}, o[Keystone.LT]);
        assertArrayEquals(new int[]{-42, -47}, o[Keystone.RT]);
        assertArrayEquals(new int[]{0, 0}, o[Keystone.LB]);
        int[][] n = AutoKeystoneService.offsetsFor(-10, 0, false, 0f);
        assertArrayEquals(new int[]{42, 47}, n[Keystone.LB]);
    }
}
