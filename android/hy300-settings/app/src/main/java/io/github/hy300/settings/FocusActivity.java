package io.github.hy300.settings;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Foco manual: segure ←/→ (ou ↓/↑) para girar o motor; solte para parar. */
public class FocusActivity extends Activity {
    private Focus focus;
    private TextView info;
    private int activeKey = 0;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        focus = new Focus();
        focus.setListener(() -> runOnUiThread(() -> info.setText(R.string.focus_limit)));

        FrameLayout root = new FrameLayout(this);
        TestPatternView pattern = new TestPatternView(this);
        pattern.setFocusDetail(true);
        root.addView(pattern, new FrameLayout.LayoutParams(-1, -1));

        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setBackgroundColor(0xCC000000);
        bar.setPadding(24, 12, 24, 12);
        Button minus = makeButton("−", -1);
        Button plus = makeButton("+", 1);
        info = new TextView(this);
        info.setTextColor(Color.WHITE);
        info.setTextSize(15);
        info.setPadding(24, 0, 24, 0);
        info.setText(Focus.available() ? R.string.focus_help : R.string.focus_unavailable);
        bar.addView(minus);
        bar.addView(info);
        bar.addView(plus);
        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(-2, -2, Gravity.CENTER_HORIZONTAL | Gravity.BOTTOM);
        lp.bottomMargin = 120;
        root.addView(bar, lp);
        setContentView(root);

        WindowInsetsController c = getWindow().getInsetsController();
        if (c != null) c.hide(WindowInsets.Type.systemBars());
    }

    @SuppressLint("ClickableViewAccessibility")
    private Button makeButton(String label, int dir) {
        Button bt = new Button(this);
        bt.setText(label);
        bt.setTextSize(26);
        bt.setFocusable(false);
        bt.setOnTouchListener((v, ev) -> {
            if (ev.getAction() == MotionEvent.ACTION_DOWN) {
                focus.start(dir);
                info.setText(R.string.focus_moving);
            } else if (ev.getAction() == MotionEvent.ACTION_UP || ev.getAction() == MotionEvent.ACTION_CANCEL) {
                focus.stop();
                info.setText(R.string.focus_help);
            }
            return false;
        });
        return bt;
    }

    private static int dirFor(int keyCode) {
        switch (keyCode) {
            case KeyEvent.KEYCODE_DPAD_RIGHT:
            case KeyEvent.KEYCODE_DPAD_UP:
            case KeyEvent.KEYCODE_PLUS:
            case KeyEvent.KEYCODE_NUMPAD_ADD:
                return 1;
            case KeyEvent.KEYCODE_DPAD_LEFT:
            case KeyEvent.KEYCODE_DPAD_DOWN:
            case KeyEvent.KEYCODE_MINUS:
            case KeyEvent.KEYCODE_NUMPAD_SUBTRACT:
                return -1;
            default:
                return 0;
        }
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent e) {
        int d = dirFor(e.getKeyCode());
        if (d == 0) return super.dispatchKeyEvent(e);
        if (e.getAction() == KeyEvent.ACTION_DOWN) {
            if (e.getRepeatCount() == 0 || activeKey != e.getKeyCode()) {
                activeKey = e.getKeyCode();
                focus.start(d);
                info.setText(R.string.focus_moving);
            }
        } else if (e.getAction() == KeyEvent.ACTION_UP && activeKey == e.getKeyCode()) {
            activeKey = 0;
            focus.stop();
            info.setText(R.string.focus_help);
        }
        return true;
    }

    @Override
    protected void onPause() {
        super.onPause();
        activeKey = 0;
        focus.stop();
    }

    @Override
    protected void onDestroy() {
        focus.release();
        super.onDestroy();
    }
}
