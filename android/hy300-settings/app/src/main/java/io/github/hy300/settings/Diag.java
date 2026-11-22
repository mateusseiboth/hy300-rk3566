package io.github.hy300.settings;

import android.os.Process;

import java.io.File;

/** Testes rápidos de capacidade (props e sysfs). Não mexe no keystone nem no motor. */
public final class Diag {
    private Diag() {}

    public static String run() {
        StringBuilder sb = new StringBuilder();
        sb.append("uid=").append(Process.myUid()).append('\n');
        String v = String.valueOf(System.currentTimeMillis() / 1000);
        boolean ok = Sys.set("persist.hy300.settings.test", v);
        String back = Sys.get("persist.hy300.settings.test", "");
        sb.append("setprop persist.*: ").append(ok && v.equals(back) ? "OK" : "FALHOU").append('\n');
        File m = new File(Focus.MOTOR);
        sb.append("motor: ").append(m.exists() ? (m.canWrite() ? "gravável" : "sem permissão") : "ausente").append('\n');
        sb.append("fim de curso (hd_camera_on)=").append(Sys.readFile(Focus.LIMIT)).append('\n');
        String enf = Sys.readFile("/sys/fs/selinux/enforce");
        sb.append("SELinux: ").append("0".equals(enf) ? "permissive" : "1".equals(enf) ? "enforcing" : "?").append('\n');
        sb.append(Keystone.fromProps(Sys.getAll()).describe());
        return sb.toString();
    }
}
