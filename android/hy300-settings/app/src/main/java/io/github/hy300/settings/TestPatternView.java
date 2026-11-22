package io.github.hy300.settings;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.util.AttributeSet;
import android.view.View;

/**
 * Padrão de teste em tela cheia: borda, grade, diagonais, círculo central, cantos marcados
 * e uma área de texto fino (útil para o foco). Desenha em coordenadas da imagem, então o que
 * aparece na parede já está com o keystone aplicado pelo SurfaceFlinger.
 */
public class TestPatternView extends View {
    private final Paint grid = new Paint();
    private final Paint border = new Paint();
    private final Paint corner = new Paint();
    private final Paint sel = new Paint();
    private final Paint text = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint fine = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint circle = new Paint(Paint.ANTI_ALIAS_FLAG);
    private int selected = -1;
    private boolean focusDetail;

    private static final String[] LABELS = {"Sup. esq.", "Inf. esq.", "Sup. dir.", "Inf. dir."};

    public TestPatternView(Context c) { this(c, null); }

    public TestPatternView(Context c, AttributeSet a) {
        super(c, a);
        grid.setColor(0xFF4A4A4A);
        grid.setStrokeWidth(1);
        border.setColor(Color.WHITE);
        border.setStyle(Paint.Style.STROKE);
        border.setStrokeWidth(4);
        corner.setColor(0xFF2196F3);
        sel.setColor(0xFFFFC107);
        text.setColor(Color.WHITE);
        text.setTextSize(22);
        fine.setColor(Color.WHITE);
        fine.setTextSize(12);
        circle.setColor(0xFF9E9E9E);
        circle.setStyle(Paint.Style.STROKE);
        circle.setStrokeWidth(2);
        setBackgroundColor(Color.BLACK);
    }

    /** Canto destacado (Keystone.LT..RB) ou -1. */
    public void setSelected(int c) {
        selected = c;
        invalidate();
    }

    public void setFocusDetail(boolean on) {
        focusDetail = on;
        invalidate();
    }

    @Override
    protected void onDraw(Canvas cv) {
        int w = getWidth(), h = getHeight();
        float step = Math.min(w, h) / 9f;
        float cx = w / 2f, cy = h / 2f;
        // grade centrada
        for (float x = cx % step; x < w; x += step) cv.drawLine(x, 0, x, h, grid);
        for (float y = cy % step; y < h; y += step) cv.drawLine(0, y, w, y, grid);
        // diagonais
        cv.drawLine(0, 0, w, h, grid);
        cv.drawLine(w, 0, 0, h, grid);
        // eixos centrais
        Paint axis = new Paint(grid);
        axis.setColor(0xFF8A8A8A);
        axis.setStrokeWidth(2);
        cv.drawLine(cx, 0, cx, h, axis);
        cv.drawLine(0, cy, w, cy, axis);
        // círculo (deve ficar redondo se a proporção estiver certa)
        cv.drawCircle(cx, cy, h * 0.35f, circle);
        // borda
        cv.drawRect(2, 2, w - 2, h - 2, border);

        // cantos
        float s = Math.min(w, h) * 0.12f;
        drawCorner(cv, Keystone.LT, 0, 0, s, 1, 1);
        drawCorner(cv, Keystone.RT, w, 0, s, -1, 1);
        drawCorner(cv, Keystone.LB, 0, h, s, 1, -1);
        drawCorner(cv, Keystone.RB, w, h, s, -1, -1);

        if (focusDetail) {
            float bw = w * 0.36f, bh = h * 0.22f;
            RectF r = new RectF(cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2);
            Paint bg = new Paint();
            bg.setColor(Color.BLACK);
            cv.drawRect(r, bg);
            Paint thin = new Paint();
            thin.setColor(Color.WHITE);
            thin.setStrokeWidth(1);
            for (float x = r.left; x < r.left + bw / 3; x += 2) cv.drawLine(x, r.top, x, r.bottom, thin);
            float ty = r.top + 16;
            for (int i = 0; i < 7; i++) {
                cv.drawText("Foco HY300 AaBbCc 0123456789", r.left + bw / 3 + 8, ty, fine);
                ty += 14 + i;
                fine.setTextSize(12 + i);
            }
            fine.setTextSize(12);
        }
    }

    private void drawCorner(Canvas cv, int c, float x, float y, float s, int dx, int dy) {
        Paint p = c == selected ? sel : corner;
        Paint t = new Paint(p);
        t.setStrokeWidth(c == selected ? 10 : 6);
        cv.drawLine(x, y + dy * 3, x + dx * s, y + dy * 3, t);
        cv.drawLine(x + dx * 3, y, x + dx * 3, y + dy * s, t);
        if (c == selected) cv.drawCircle(x + dx * s * 0.5f, y + dy * s * 0.5f, s * 0.18f, p);
        float tw = text.measureText(LABELS[c]);
        float tx = dx > 0 ? x + s * 0.25f : x - s * 0.25f - tw;
        float ty = dy > 0 ? y + s + 26 : y - s - 10;
        text.setColor(c == selected ? 0xFFFFC107 : Color.WHITE);
        cv.drawText(LABELS[c], tx, ty, text);
        text.setColor(Color.WHITE);
    }
}
