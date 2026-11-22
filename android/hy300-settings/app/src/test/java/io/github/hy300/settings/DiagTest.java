package io.github.hy300.settings;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.List;

import org.junit.Test;

public class DiagTest {
    private static Diag.Facts facts() {
        Diag.Facts f = new Diag.Facts();
        f.uid = 10073;
        f.setpropOk = true;
        f.motor = Diag.MotorState.WRITABLE;
        f.limit = "0";
        f.selinux = "0";
        f.keystone = new Keystone();
        return f;
    }

    /** O layout leanback corta o resumo em poucas linhas: cada informação vira uma linha própria. */
    @Test
    public void everyRowIsSingleLine() {
        for (String[] r : Diag.buildRows(facts())) {
            assertEquals(2, r.length);
            assertFalse(r[0].contains("\n"));
            assertFalse(r[1].contains("\n"));
        }
    }

    @Test
    public void showsSelinuxAndEveryCorner() {
        List<String[]> rows = Diag.buildRows(facts());
        assertTrue(rows.stream().anyMatch(r -> r[0].equals("SELinux") && r[1].equals("permissive")));
        for (String c : new String[]{"lt", "lb", "rt", "rb"}) {
            assertTrue(c, rows.stream().anyMatch(r -> r[0].equals("Canto " + c) && r[1].equals("0,0")));
        }
    }

    @Test
    public void mapsMotorAndSelinuxStates() {
        Diag.Facts f = facts();
        f.motor = Diag.MotorState.MISSING;
        f.selinux = "1";
        List<String[]> rows = Diag.buildRows(f);
        assertTrue(rows.stream().anyMatch(r -> r[0].equals("Motor de foco") && r[1].equals("ausente")));
        assertTrue(rows.stream().anyMatch(r -> r[0].equals("SELinux") && r[1].equals("enforcing")));
    }
}
