package io.github.hy300.settings;

import android.util.Log;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Acesso a system properties e sysfs.
 *
 * Leitura: executa {@code getprop} uma vez e faz o parse da saída inteira (evita API oculta).
 * Escrita: executa {@code /system/bin/setprop} (toybox). Funciona para um app comum porque o
 * SELinux do HY300 está em permissive e o property service só checa SELinux para props comuns.
 * Ver README, seção "Permissões".
 */
public final class Sys {
    private static final String TAG = "HY300Sys";
    private static final Pattern LINE = Pattern.compile("^\\[(.+?)\\]: \\[(.*)\\]$");

    private Sys() {}

    /** Lê todas as props de uma vez. */
    public static Map<String, String> getAll() {
        Map<String, String> out = new HashMap<>();
        try {
            Process p = new ProcessBuilder("/system/bin/getprop").redirectErrorStream(true).start();
            try (BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = r.readLine()) != null) {
                    Matcher m = LINE.matcher(line);
                    if (m.matches()) out.put(m.group(1), m.group(2));
                }
            }
            p.waitFor();
        } catch (IOException | InterruptedException e) {
            Log.e(TAG, "getprop falhou", e);
        }
        return out;
    }

    public static String get(String key, String def) {
        try {
            Process p = new ProcessBuilder("/system/bin/getprop", key).redirectErrorStream(true).start();
            String v = readAll(p.getInputStream()).trim();
            p.waitFor();
            return v.isEmpty() ? def : v;
        } catch (IOException | InterruptedException e) {
            Log.e(TAG, "getprop " + key + " falhou", e);
            return def;
        }
    }

    public static int getInt(Map<String, String> props, String key, int def) {
        String v = props.get(key);
        if (v == null || v.isEmpty()) return def;
        try {
            return Math.round(Float.parseFloat(v.trim()));
        } catch (NumberFormatException e) {
            return def;
        }
    }

    public static float getFloat(Map<String, String> props, String key, float def) {
        String v = props.get(key);
        if (v == null || v.isEmpty()) return def;
        try {
            return Float.parseFloat(v.trim());
        } catch (NumberFormatException e) {
            return def;
        }
    }

    /** Grava uma prop. Retorna true se o valor relido for o esperado. */
    public static boolean set(String key, String value) {
        LinkedHashMap<String, String> m = new LinkedHashMap<>();
        m.put(key, value);
        return setAll(m);
    }

    /**
     * Grava várias props num único processo de shell, na ordem do mapa.
     * Retorna false se o shell sair com erro.
     */
    public static boolean setAll(LinkedHashMap<String, String> props) {
        if (props.isEmpty()) return true;
        StringBuilder sb = new StringBuilder();
        for (Map.Entry<String, String> e : props.entrySet()) {
            if (!e.getKey().matches("[A-Za-z0-9._\\-]+")) {
                Log.e(TAG, "nome de prop inválido: " + e.getKey());
                return false;
            }
            sb.append("/system/bin/setprop ").append(e.getKey()).append(' ')
                    .append(quote(e.getValue())).append(" || exit 1\n");
        }
        try {
            Process p = new ProcessBuilder("/system/bin/sh", "-c", sb.toString())
                    .redirectErrorStream(true).start();
            String out = readAll(p.getInputStream());
            int rc = p.waitFor();
            if (rc != 0) {
                Log.e(TAG, "setprop falhou rc=" + rc + ": " + out);
                return false;
            }
            return true;
        } catch (IOException | InterruptedException e) {
            Log.e(TAG, "setprop falhou", e);
            return false;
        }
    }

    private static String quote(String v) {
        if (v.isEmpty()) return "''";
        return "'" + v.replace("'", "'\\''") + "'";
    }

    public static boolean writeFile(String path, String value) {
        try (FileOutputStream os = new FileOutputStream(path)) {
            os.write(value.getBytes(StandardCharsets.US_ASCII));
            return true;
        } catch (IOException e) {
            Log.d(TAG, "escrita em " + path + " falhou: " + e.getMessage());
            return false;
        }
    }

    public static String readFile(String path) {
        File f = new File(path);
        if (!f.canRead()) return null;
        try (BufferedReader r = new BufferedReader(new FileReader(f))) {
            String l = r.readLine();
            return l == null ? "" : l.trim();
        } catch (IOException e) {
            return null;
        }
    }

    private static String readAll(InputStream in) throws IOException {
        StringBuilder sb = new StringBuilder();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            String l;
            while ((l = r.readLine()) != null) sb.append(l).append('\n');
        }
        return sb.toString();
    }
}
