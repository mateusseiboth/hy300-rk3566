package io.github.hy300.settings;

import android.os.Process;

import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Testes rápidos de capacidade (props e sysfs). Não mexe no keystone nem no motor. */
public final class Diag {
    public enum MotorState { WRITABLE, READ_ONLY, MISSING }

    /** O que foi medido no aparelho; {@link #buildRows} só formata. */
    public static final class Facts {
        int uid;
        boolean setpropOk;
        MotorState motor = MotorState.MISSING;
        String limit;
        String selinux;
        Keystone keystone;
    }

    private static final Map<MotorState, String> MOTOR_TEXT = new HashMap<>();
    private static final Map<String, String> SELINUX_TEXT = new HashMap<>();
    static {
        MOTOR_TEXT.put(MotorState.WRITABLE, "gravável");
        MOTOR_TEXT.put(MotorState.READ_ONLY, "sem permissão");
        MOTOR_TEXT.put(MotorState.MISSING, "ausente");
        SELINUX_TEXT.put("0", "permissive");
        SELINUX_TEXT.put("1", "enforcing");
    }

    private Diag() {}

    public static Facts measure() {
        Facts f = new Facts();
        f.uid = Process.myUid();
        String v = String.valueOf(System.currentTimeMillis() / 1000);
        f.setpropOk = Sys.set("persist.hy300.settings.test", v) && v.equals(Sys.get("persist.hy300.settings.test", ""));
        f.motor = readMotorState(new File(Focus.MOTOR));
        f.limit = Sys.readFile(Focus.LIMIT);
        f.selinux = Sys.readFile("/sys/fs/selinux/enforce");
        f.keystone = Keystone.fromProps(Sys.getAll());
        return f;
    }

    private static MotorState readMotorState(File m) {
        if (!m.exists()) return MotorState.MISSING;
        return m.canWrite() ? MotorState.WRITABLE : MotorState.READ_ONLY;
    }

    /** Uma linha por informação: [título, valor]. */
    public static List<String[]> buildRows(Facts f) {
        List<String[]> rows = new ArrayList<>();
        rows.add(new String[]{"uid", String.valueOf(f.uid)});
        rows.add(new String[]{"Gravar props persist.*", f.setpropOk ? "OK" : "FALHOU"});
        rows.add(new String[]{"Motor de foco", MOTOR_TEXT.get(f.motor)});
        rows.add(new String[]{"Fim de curso (hd_camera_on)", String.valueOf(f.limit)});
        rows.add(new String[]{"SELinux", SELINUX_TEXT.getOrDefault(String.valueOf(f.selinux), "?")});
        for (int c = 0; c < 4; c++) {
            int[] v = f.keystone.corner(c);
            rows.add(new String[]{"Canto " + Keystone.CORNER_KEYS[c], v[0] + "," + v[1]});
        }
        rows.add(new String[]{"Modo e zoom", f.keystone.mode + ", " + f.keystone.zoom + "%"});
        return rows;
    }

    /** Texto corrido (log e DiagActivity). */
    public static String run() {
        StringBuilder sb = new StringBuilder();
        for (String[] r : buildRows(measure())) sb.append(r[0]).append(": ").append(r[1]).append('\n');
        return sb.toString();
    }
}
