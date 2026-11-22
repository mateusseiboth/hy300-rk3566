package com.hy300.bootlog;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.view.Surface;
import android.view.SurfaceControl;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.lang.reflect.Method;
import java.util.ArrayDeque;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Animação de boot que mostra o log real (logcat -b all) ao vivo.
 * Roda via app_process no lugar do serviço "bootanim".
 *
 * Uso: CLASSPATH=bootlog.dex app_process /system/bin com.hy300.bootlog.Main [w h] [logo.png]
 */
public final class Main {
    static int W = 1280, H = 720;
    static final int MAX_LINES = 400;
    static final ArrayDeque<String> lines = new ArrayDeque<>();
    static volatile int progress = 0;          // 0..100
    static volatile String stage = "kernel";
    static final long T0 = System.currentTimeMillis();

    static final String[][] STAGES = {
        {"boot_progress_start", "8", "zygote"},
        {"boot_progress_preload_start", "15", "preload"},
        {"boot_progress_preload_end", "40", "preload ok"},
        {"boot_progress_system_run", "50", "system_server"},
        {"boot_progress_pms_start", "58", "package manager"},
        {"boot_progress_pms_data_scan_start", "68", "scan /data"},
        {"boot_progress_pms_ready", "78", "pms ready"},
        {"boot_progress_ams_ready", "90", "activity manager"},
        {"boot_progress_enable_screen", "100", "enable screen"},
    };

    public static void main(String[] args) throws Exception {
        boolean test = false;
        java.util.List<String> a = new java.util.ArrayList<>();
        for (String s : args) { if ("--test".equals(s)) test = true; else a.add(s); }
        if (a.size() >= 2) { W = Integer.parseInt(a.get(0)); H = Integer.parseInt(a.get(1)); }
        String logoPath = a.size() >= 3 ? a.get(2) : "/system/media/bootlog/logo.png";

        SurfaceControl sc = new SurfaceControl.Builder()
                .setName("hy300-bootlog")
                .setBufferSize(W, H)
                .setFormat(PixelFormat.RGBX_8888)
                .setOpaque(true)
                .build();
        new SurfaceControl.Transaction()
                .setLayer(sc, Integer.MAX_VALUE - 1)
                .setVisibility(sc, true)
                .apply();
        Surface surface = new Surface(sc);

        Thread reader = new Thread(Main::readLog, "logcat");
        reader.setDaemon(true);
        reader.start();

        Bitmap logo = null;
        try { logo = BitmapFactory.decodeFile(logoPath); } catch (Throwable ignored) {}

        // app_process não passa pelo zygote: inicializar o mapa de fontes e o default nativo
        initFonts();
        Typeface mono = font("/system/fonts/DroidSansMono.ttf");
        Typeface bold = font("/system/fonts/DroidSans-Bold.ttf");
        Paint txt = new Paint(Paint.ANTI_ALIAS_FLAG);
        if (mono != null) txt.setTypeface(mono);
        txt.setTextSize(13f);
        Paint hdr = new Paint(Paint.ANTI_ALIAS_FLAG);
        if (bold != null) hdr.setTypeface(bold);
        hdr.setTextSize(18f);
        Paint bar = new Paint(Paint.ANTI_ALIAS_FLAG);
        Paint fade = new Paint();

        float lh = txt.getFontSpacing();
        int top = 48, bottom = H - 40;
        int visible = (int) ((bottom - top) / lh);
        int shownProgress = 0;
        Method getProp = Class.forName("android.os.SystemProperties").getMethod("get", String.class, String.class);
        long deadline = T0 + (test ? 15_000 : 180_000);

        while (true) {
            String exit = (String) getProp.invoke(null, "service.bootanim.exit", "0");
            if ((!test && "1".equals(exit)) || System.currentTimeMillis() > deadline) break;

            Canvas c = surface.lockCanvas(null);
            try {
                c.drawColor(Color.rgb(8, 6, 16));

                // cabeçalho
                hdr.setColor(Color.rgb(190, 140, 255));
                c.drawText("HY300 :: RK3566 :: booting", 16, 30, hdr);
                hdr.setColor(Color.rgb(120, 110, 150));
                String t = String.format("%6.2fs  %s", (System.currentTimeMillis() - T0) / 1000f, stage);
                c.drawText(t, W - 16 - hdr.measureText(t) - (logo != null ? 0 : 0), 30, hdr);
                bar.setColor(Color.rgb(60, 40, 110));
                c.drawRect(0, 40, W, 41, bar);

                // log
                String[] snap;
                synchronized (lines) { snap = lines.toArray(new String[0]); }
                int start = Math.max(0, snap.length - visible);
                float y = top + lh;
                for (int i = start; i < snap.length; i++) {
                    String l = snap[i];
                    txt.setColor(colorFor(l));
                    c.drawText(l, 0, Math.min(l.length(), 190), 12, y, txt);
                    y += lh;
                }

                // capivara no canto
                if (logo != null) {
                    int s = 150;
                    Rect dst = new Rect(W - s - 16, H - s - 52, W - 16, H - 52);
                    fade.setAlpha(235);
                    c.drawBitmap(logo, null, dst, fade);
                }

                // barra de progresso
                if (shownProgress < progress) shownProgress += Math.max(1, (progress - shownProgress) / 6);
                bar.setColor(Color.rgb(35, 25, 60));
                c.drawRoundRect(new RectF(16, H - 26, W - 16, H - 16), 5, 5, bar);
                bar.setColor(Color.rgb(160, 90, 255));
                c.drawRoundRect(new RectF(16, H - 26, 16 + (W - 32) * shownProgress / 100f, H - 16), 5, 5, bar);
            } finally {
                surface.unlockCanvasAndPost(c);
            }
            Thread.sleep(40);
        }
        new SurfaceControl.Transaction().setVisibility(sc, false).apply();
        surface.release();
        sc.release();
        System.exit(0);
    }

    static void initFonts() {
        try {
            Method m = Typeface.class.getDeclaredMethod("loadPreinstalledSystemFontMap");
            m.setAccessible(true);
            m.invoke(null);
        } catch (Throwable ignored) {}
        try {
            Typeface def = Typeface.createFromFile("/system/fonts/Roboto-Regular.ttf");
            Method m = Typeface.class.getDeclaredMethod("setDefault", Typeface.class);
            m.setAccessible(true);
            m.invoke(null, def);
        } catch (Throwable ignored) {}
    }

    static Typeface font(String path) {
        try { return Typeface.createFromFile(path); } catch (Throwable t) { return null; }
    }

    static int colorFor(String l) {
        if (l.length() > 1 && l.charAt(1) == '/') {   // brief: "P/Tag(pid): msg"
            char p = l.charAt(0);
            if (p == 'E' || p == 'F') return Color.rgb(255, 95, 110);
            if (p == 'W') return Color.rgb(255, 200, 90);
        }
        if (l.contains(" kernel") || l.startsWith("[k]")) return Color.rgb(110, 220, 140);
        if (l.contains("boot_progress")) return Color.rgb(200, 150, 255);
        if (l.contains("Zygote") || l.contains("SystemServer")) return Color.rgb(120, 190, 255);
        return Color.rgb(170, 170, 185);
    }

    static final Pattern TIME = Pattern.compile("^\\d\\d-\\d\\d (\\d\\d:\\d\\d:\\d\\d\\.\\d+)\\s+");

    static void readLog() {
        try {
            Process p = new ProcessBuilder("logcat", "-b", "all", "-v", "brief")
                    .redirectErrorStream(true).start();
            BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream()), 1 << 16);
            String l;
            while ((l = r.readLine()) != null) {
                for (String[] s : STAGES) {
                    if (l.contains(s[0])) { progress = Integer.parseInt(s[1]); stage = s[2]; }
                }
                if (progress == 0 && l.contains("SurfaceFlinger")) { progress = 4; stage = "surfaceflinger"; }
                synchronized (lines) {
                    lines.addLast(l.replace('\t', ' '));
                    while (lines.size() > MAX_LINES) lines.removeFirst();
                }
            }
        } catch (Throwable t) {
            synchronized (lines) { lines.addLast("bootlog: " + t); }
        }
    }
}
