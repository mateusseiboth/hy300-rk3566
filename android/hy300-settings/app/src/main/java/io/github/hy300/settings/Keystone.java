package io.github.hy300.settings;

import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

/**
 * Modelo do keystone do HY300 (SurfaceFlinger + librkgfx_dc, "keystone v5.1").
 *
 * Props do SF: {@code persist.sys.keystone.{lt,lb,rt,rb}="x,y"}, deslocamento em px do painel
 * lógico 1280x720 a partir da posição nativa do canto, x para a direita e y para cima.
 * {@code persist.sys.keystone.update=1} faz o SF reler.
 *
 * O estado é decomposto em:
 * <ul>
 *   <li>base(modo de instalação, zoom, área lógica 16:9/4:3), igual à do app TXCZ
 *       ({@code ProjectUtils.reset/x_mirror/xy_mirror/y_mirror});</li>
 *   <li>ajuste do usuário por canto, em coordenadas "do espectador": o canto é o canto da
 *       IMAGEM (sup. esq. = o que aparece em cima à esquerda na parede), x para a direita, y para cima.
 *       Para cantos espelhados pelo modo de instalação, o sinal é invertido na conversão para a prop
 *       (mesma regra de {@code getXRealValue/getYRealValue} do app TXCZ).</li>
 * </ul>
 * Os cantos gravados são sempre recalculados como base + ajuste. O ajuste é extraído das props
 * atuais (prop - base), então mudanças feitas pelo app TXCZ também são preservadas.
 */
public final class Keystone {
    public static final int W = 1280;
    public static final int H = 720;

    public static final int LT = 0, LB = 1, RT = 2, RB = 3;
    public static final String[] CORNER_KEYS = {"lt", "lb", "rt", "rb"};

    public static final int MODE_DESK_FRONT = 0;
    public static final int MODE_DESK_REAR = 1;
    public static final int MODE_CEIL_FRONT = 2;
    public static final int MODE_CEIL_REAR = 3;

    public static final int ZOOM_MIN = 20;
    public static final int ZOOM_MAX = 100;

    public static final String P_PREFIX = "persist.sys.keystone.";
    public static final String P_UPDATE = "persist.sys.keystone.update";
    /** Espelho nativo da librkgfx_dc e do SF do LineageOS: o modo de instalação espelha pelos cantos. */
    public static final String P_MIRROR_X = "persist.sys.keystone.mirror_x";
    public static final String P_MIRROR_Y = "persist.sys.keystone.mirror_y";
    public static final String P_MODE = "persist.txcz.install.model";
    public static final String P_ZOOM = "persist.txcz.trapezoid.zoom";
    public static final String P_TRAP_MODE = "persist.txcz.trapezoid.mode";
    public static final String P_TRAP_X = "persist.txcz.trapezoid.offsetx";
    public static final String P_TRAP_Y = "persist.txcz.trapezoid.offsety";
    public static final String P_SCREEN_W = "persist.txcz.screen.width";
    public static final String P_SCREEN_H = "persist.txcz.screen.height";
    public static final String P_SCREEN_RATIO = "persist.txcz.screen.ratio";

    public int mode;
    public int zoom;
    /** 0 = 16:9, 1 = 4:3 */
    public int ratio;
    /** Contadores do trapézio (só UI, compatíveis com o app TXCZ). */
    public int trapV, trapH;
    /** Ajuste do usuário por canto, coordenadas do espectador: [canto][0=x,1=y]. */
    public final int[][] user = new int[4][2];

    public Keystone() {
        mode = MODE_DESK_FRONT;
        zoom = 100;
    }

    public Keystone copy() {
        Keystone k = new Keystone();
        k.mode = mode; k.zoom = zoom; k.ratio = ratio; k.trapV = trapV; k.trapH = trapH;
        for (int i = 0; i < 4; i++) { k.user[i][0] = user[i][0]; k.user[i][1] = user[i][1]; }
        return k;
    }

    // ---------- geometria ----------

    public int screenW() { return ratio == 1 ? Math.round(H * 4f / 3f) : W; }
    public int screenH() { return H; }

    public int zoomW() { return screenW() * zoom / 100; }
    public int zoomH() { return screenH() * zoom / 100; }
    public int minX() { return (W - zoomW()) / 2; }
    public int minY() { return (H - zoomH()) / 2; }
    public int maxX() { return minX() + zoomW(); }
    public int maxY() { return minY() + zoomH(); }

    public static boolean isLeft(int c) { return c == LT || c == LB; }
    public static boolean isTop(int c) { return c == LT || c == RT; }

    public boolean mirrorX() { return mode == MODE_DESK_REAR || mode == MODE_CEIL_FRONT; }
    public boolean mirrorY() { return mode == MODE_CEIL_FRONT || mode == MODE_CEIL_REAR; }

    /** Posição-base (prop) do canto c para o modo/zoom/proporção atuais. */
    public int[] base(int c) {
        int bx = mirrorX() ? maxX() : minX();
        int by = mirrorY() ? maxY() : minY();
        int x = isLeft(c) ? bx : -bx;
        int y = isTop(c) ? -by : by;
        return new int[]{x, y};
    }

    private int sx() { return mirrorX() ? -1 : 1; }
    private int sy() { return mirrorY() ? -1 : 1; }

    /** Valor final da prop do canto c. */
    public int[] corner(int c) {
        int[] b = base(c);
        return new int[]{b[0] + sx() * user[c][0], b[1] + sy() * user[c][1]};
    }

    /** "Para dentro" do canto c em coordenadas do espectador: (+1/-1, +1/-1). */
    public static int inX(int c) { return isLeft(c) ? 1 : -1; }
    public static int inY(int c) { return isTop(c) ? -1 : 1; }

    /** Limita o ajuste: até 1/3 da área para dentro e sem sair do painel para fora. */
    public void clamp() {
        int maxInX = zoomW() / 3, maxInY = zoomH() / 3;
        int maxOutX = minX(), maxOutY = minY();
        for (int c = 0; c < 4; c++) {
            int inx = user[c][0] * inX(c);
            int iny = user[c][1] * inY(c);
            inx = Math.max(-maxOutX, Math.min(maxInX, inx));
            iny = Math.max(-maxOutY, Math.min(maxInY, iny));
            user[c][0] = inx * inX(c);
            user[c][1] = iny * inY(c);
        }
    }

    // ---------- operações ----------

    public void moveCorner(int c, int dx, int dy) {
        user[c][0] += dx;
        user[c][1] += dy;
        clamp();
    }

    /**
     * Trapézio vertical (contador {@code persist.txcz.trapezoid.offsetx}, mesma regra do TXCZ):
     * positivo estreita a borda de cima, negativo a de baixo. Cada unidade move os dois cantos
     * da borda 1 px para dentro em x e 1 px em y. Aplica o delta em relação ao contador atual,
     * então um contador deixado pelo app TXCZ é desfeito corretamente.
     */
    public void setTrapV(int v) {
        int lim = zoomW() / 3;
        v = Math.max(-lim, Math.min(lim, v));
        applyTrapEdge(trapV, v, VERTICAL_EDGES);
        trapV = v;
    }

    /**
     * Trapézio horizontal ({@code persist.txcz.trapezoid.offsety}): positivo estreita a borda
     * direita, negativo a esquerda. Mesma regra de 1 px em x e 1 px em y por unidade.
     */
    public void setTrapH(int v) {
        int lim = zoomH() / 3;
        v = Math.max(-lim, Math.min(lim, v));
        applyTrapEdge(trapH, v, HORIZONTAL_EDGES);
        trapH = v;
    }

    /** Cantos da borda estreitada: [0] para contador positivo, [1] para negativo. */
    private static final int[][] VERTICAL_EDGES = {{LT, RT}, {LB, RB}};
    private static final int[][] HORIZONTAL_EDGES = {{RT, RB}, {LT, LB}};

    private void applyTrapEdge(int oldV, int newV, int[][] edges) {
        // remove a contribuição antiga e aplica a nova
        trapContribution(oldV, edges, -1);
        trapContribution(newV, edges, +1);
        clamp();
    }

    private void trapContribution(int v, int[][] edges, int sign) {
        if (v == 0) return;
        int a = Math.abs(v);
        for (int c : edges[v > 0 ? 0 : 1]) {
            user[c][0] += sign * a * inX(c);
            user[c][1] += sign * a * inY(c);
        }
    }

    /**
     * Setas na tela do trapézio, como no TXCZ: cima/baixo somam/subtraem no vertical,
     * direita/esquerda no horizontal.
     */
    public void nudgeTrapezoid(int dx, int dy, int step) {
        if (dy != 0) setTrapV(trapV + dy * step);
        if (dx != 0) setTrapH(trapH + dx * step);
    }

    public void setZoom(int z) {
        zoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, z));
        clamp();
    }

    public void resetUser() {
        for (int[] u : user) { u[0] = 0; u[1] = 0; }
        trapV = 0; trapH = 0;
    }

    // ---------- props ----------

    public static int[] parseXY(String s) {
        if (s == null) return null;
        String[] p = s.split(",");
        if (p.length != 2) return null;
        try {
            return new int[]{Integer.parseInt(p[0].trim()), Integer.parseInt(p[1].trim())};
        } catch (NumberFormatException e) {
            return null;
        }
    }

    public static Keystone fromProps(Map<String, String> p) {
        Keystone k = new Keystone();
        k.mode = clampInt(Sys.getInt(p, P_MODE, 0), 0, 3);
        k.zoom = clampInt(Sys.getInt(p, P_ZOOM, 100), ZOOM_MIN, ZOOM_MAX);
        k.ratio = Sys.getInt(p, P_SCREEN_RATIO, 0) == 1 ? 1 : 0;
        k.trapV = Sys.getInt(p, P_TRAP_X, 0);
        k.trapH = Sys.getInt(p, P_TRAP_Y, 0);
        for (int c = 0; c < 4; c++) {
            int[] v = parseXY(p.get(P_PREFIX + CORNER_KEYS[c]));
            if (v == null) continue;
            int[] b = k.base(c);
            k.user[c][0] = k.sx() * (v[0] - b[0]);
            k.user[c][1] = k.sy() * (v[1] - b[1]);
        }
        return k;
    }

    private static int clampInt(int v, int lo, int hi) { return Math.max(lo, Math.min(hi, v)); }

    /** Props a gravar (sem o update). Mantém coerentes as props do app TXCZ. */
    public LinkedHashMap<String, String> toProps() {
        LinkedHashMap<String, String> m = new LinkedHashMap<>();
        for (int c = 0; c < 4; c++) {
            int[] b = base(c);
            m.put(P_PREFIX + CORNER_KEYS[c] + ".init.xy", b[0] + "," + b[1]);
        }
        for (int c = 0; c < 4; c++) {
            int[] v = corner(c);
            m.put(P_PREFIX + CORNER_KEYS[c], v[0] + "," + v[1]);
        }
        // O espelho do modo de instalação já está nos cantos (base); o nativo fica desligado para
        // não espelhar duas vezes.
        m.put(P_MIRROR_X, "0");
        m.put(P_MIRROR_Y, "0");
        m.put(P_MODE, String.valueOf(mode));
        m.put(P_ZOOM, String.valueOf(zoom));
        m.put(P_TRAP_X, String.valueOf(trapV));
        m.put(P_TRAP_Y, String.valueOf(trapH));
        m.put(P_SCREEN_RATIO, String.valueOf(ratio));
        m.put(P_SCREEN_W, String.valueOf(screenW()));
        m.put(P_SCREEN_H, String.valueOf(screenH()));
        return m;
    }

    public String describe() {
        StringBuilder sb = new StringBuilder();
        for (int c = 0; c < 4; c++) {
            int[] v = corner(c);
            sb.append(CORNER_KEYS[c]).append('=').append(v[0]).append(',').append(v[1]).append("  ");
        }
        return sb.toString().trim();
    }

    public String userDescribe(int c) {
        return String.format(Locale.ROOT, "%+d, %+d", user[c][0], user[c][1]);
    }
}
