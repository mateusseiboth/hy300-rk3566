package io.github.hy300.settings;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.widget.FrameLayout;
import android.widget.TextView;
import android.widget.Toast;

/**
 * Tela cheia com padrão de teste para ajustar o keystone pelo D-pad.
 * Páginas: cantos, trapézio, zoom, só padrão.
 */
public class KeystoneActivity extends Activity {
    public static final String EXTRA_PAGE = "page";
    public static final int PAGE_CORNERS = 0;
    public static final int PAGE_TRAPEZOID = 1;
    public static final int PAGE_ZOOM = 2;
    public static final int PAGE_PATTERN = 3;

    private static final int[] STEPS = {1, 5, 20};
    private static final int[] CORNER_ORDER = {Keystone.LT, Keystone.RT, Keystone.RB, Keystone.LB};

    private TestPatternView pattern;
    private TextView info;
    private Keystone ks;
    private int page;
    private int stepIdx = 1;
    private int cornerPos = 0;

    public static void start(Context c, int page) {
        c.startActivity(new Intent(c, KeystoneActivity.class).putExtra(EXTRA_PAGE, page));
    }

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        page = getIntent().getIntExtra(EXTRA_PAGE, PAGE_CORNERS);
        FrameLayout root = new FrameLayout(this);
        pattern = new TestPatternView(this);
        root.addView(pattern, new FrameLayout.LayoutParams(-1, -1));
        info = new TextView(this);
        info.setTextColor(Color.WHITE);
        info.setTextSize(15);
        info.setBackgroundColor(0xCC000000);
        info.setPadding(28, 16, 28, 16);
        info.setGravity(Gravity.CENTER);
        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(-2, -2, Gravity.CENTER);
        lp.topMargin = 170;
        root.addView(info, lp);
        setContentView(root);
        hideBars();
    }

    private void hideBars() {
        WindowInsetsController c = getWindow().getInsetsController();
        if (c != null) {
            c.hide(WindowInsets.Type.systemBars());
            c.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        info.setText(R.string.loading);
        new Thread(() -> {
            Keystone k = Keystone.fromProps(Sys.getAll());
            runOnUiThread(() -> { ks = k; refresh(); });
        }).start();
    }

    private int step() { return STEPS[stepIdx]; }

    private int selectedCorner() { return CORNER_ORDER[cornerPos]; }

    private void refresh() {
        if (ks == null) return;
        pattern.setSelected(page == PAGE_CORNERS ? selectedCorner() : -1);
        String stepName = getResources().getStringArray(R.array.step_names)[stepIdx];
        String txt;
        switch (page) {
            case PAGE_CORNERS:
                txt = getString(R.string.ks_info_corners,
                        getResources().getStringArray(R.array.corner_names)[selectedCorner()],
                        ks.userDescribe(selectedCorner()), stepName);
                break;
            case PAGE_TRAPEZOID:
                txt = getString(R.string.ks_info_trapezoid, ks.trapV, ks.trapH, stepName);
                break;
            case PAGE_ZOOM:
                txt = getString(R.string.ks_info_zoom, ks.zoom);
                break;
            default:
                txt = getString(R.string.ks_info_pattern);
        }
        info.setText(txt);
    }

    private void apply() {
        KeystoneApplier.applyAsync(ks);
        refresh();
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent e) {
        if (ks == null) return super.onKeyDown(keyCode, e);
        int s = step();
        switch (keyCode) {
            case KeyEvent.KEYCODE_MENU:
            case KeyEvent.KEYCODE_TAB:
            case KeyEvent.KEYCODE_S:
                if (e.getRepeatCount() == 0) {
                    stepIdx = (stepIdx + 1) % STEPS.length;
                    refresh();
                }
                return true;
            case KeyEvent.KEYCODE_DEL:
            case KeyEvent.KEYCODE_0:
            case KeyEvent.KEYCODE_PROG_RED:
            case KeyEvent.KEYCODE_R:
                if (e.getRepeatCount() == 0) {
                    if (page == PAGE_ZOOM) ks.setZoom(100); else ks.resetUser();
                    Toast.makeText(this, R.string.ks_reset_done, Toast.LENGTH_SHORT).show();
                    apply();
                }
                return true;
            case KeyEvent.KEYCODE_DPAD_CENTER:
            case KeyEvent.KEYCODE_ENTER:
            case KeyEvent.KEYCODE_NUMPAD_ENTER:
                if (e.getRepeatCount() == 0 && page == PAGE_CORNERS) {
                    cornerPos = (cornerPos + 1) % CORNER_ORDER.length;
                    refresh();
                }
                return true;
            case KeyEvent.KEYCODE_DPAD_UP:
            case KeyEvent.KEYCODE_DPAD_DOWN:
            case KeyEvent.KEYCODE_DPAD_LEFT:
            case KeyEvent.KEYCODE_DPAD_RIGHT:
                return onArrow(keyCode, s);
            default:
                return super.onKeyDown(keyCode, e);
        }
    }

    private boolean onArrow(int keyCode, int s) {
        int dx = 0, dy = 0;
        if (keyCode == KeyEvent.KEYCODE_DPAD_UP) dy = 1;
        if (keyCode == KeyEvent.KEYCODE_DPAD_DOWN) dy = -1;
        if (keyCode == KeyEvent.KEYCODE_DPAD_LEFT) dx = -1;
        if (keyCode == KeyEvent.KEYCODE_DPAD_RIGHT) dx = 1;
        switch (page) {
            case PAGE_CORNERS:
                ks.moveCorner(selectedCorner(), dx * s, dy * s);
                break;
            case PAGE_TRAPEZOID:
                // ↑ estreita o topo, ↓ estreita a base; ← estreita a esquerda, → a direita
                if (dy != 0) ks.setTrapV(ks.trapV + dy * s);
                if (dx != 0) ks.setTrapH(ks.trapH - dx * s);
                break;
            case PAGE_ZOOM:
                int zs = s == 1 ? 1 : 5;
                ks.setZoom(ks.zoom + (dx != 0 ? dx : dy) * zs);
                break;
            default:
                return true;
        }
        apply();
        return true;
    }
}
