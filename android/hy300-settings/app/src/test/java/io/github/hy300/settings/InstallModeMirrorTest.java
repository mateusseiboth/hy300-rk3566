package io.github.hy300.settings;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;

import java.util.Map;

import org.junit.Test;

/**
 * Modo de instalação (persist.txcz.install.model 0..3) virando espelho da imagem. O espelho vai
 * nos cantos, como no app TXCZ: o canto da imagem é levado ao canto oposto do painel, e a
 * homografia do SurfaceFlinger (e a malha da librkgfx_dc) desenha a imagem espelhada.
 * persist.sys.keystone.mirror_x/mirror_y ficam em 0, senão o espelho seria aplicado duas vezes.
 */
public class InstallModeMirrorTest {
    /** Onde o canto c da imagem cai no painel 1280x720 (y para baixo), sem zoom nem ajuste. */
    private static int[] landing(int mode, int c) {
        Keystone k = new Keystone();
        k.mode = mode;
        int[] v = k.corner(c);
        int x = (Keystone.isLeft(c) ? 0 : Keystone.W) + v[0];
        int y = (Keystone.isTop(c) ? 0 : Keystone.H) - v[1];
        return new int[]{x, y};
    }

    @Test
    public void deskFrontKeepsTheImage() {
        assertArrayEquals(new int[]{0, 0}, landing(Keystone.MODE_DESK_FRONT, Keystone.LT));
        assertArrayEquals(new int[]{1280, 720}, landing(Keystone.MODE_DESK_FRONT, Keystone.RB));
    }

    @Test
    public void deskRearMirrorsHorizontally() {
        assertArrayEquals(new int[]{1280, 0}, landing(Keystone.MODE_DESK_REAR, Keystone.LT));
        assertArrayEquals(new int[]{0, 720}, landing(Keystone.MODE_DESK_REAR, Keystone.RB));
    }

    @Test
    public void ceilingFrontTurnsUpsideDown() {
        assertArrayEquals(new int[]{1280, 720}, landing(Keystone.MODE_CEIL_FRONT, Keystone.LT));
        assertArrayEquals(new int[]{0, 0}, landing(Keystone.MODE_CEIL_FRONT, Keystone.RB));
    }

    @Test
    public void ceilingRearMirrorsVertically() {
        assertArrayEquals(new int[]{0, 720}, landing(Keystone.MODE_CEIL_REAR, Keystone.LT));
        assertArrayEquals(new int[]{1280, 0}, landing(Keystone.MODE_CEIL_REAR, Keystone.RB));
    }

    @Test
    public void nativeMirrorPropsAreAlwaysCleared() {
        for (int mode = 0; mode <= 3; mode++) {
            Keystone k = new Keystone();
            k.mode = mode;
            Map<String, String> props = k.toProps();
            assertEquals("0", props.get("persist.sys.keystone.mirror_x"));
            assertEquals("0", props.get("persist.sys.keystone.mirror_y"));
            assertEquals(String.valueOf(mode), props.get(Keystone.P_MODE));
        }
    }
}
