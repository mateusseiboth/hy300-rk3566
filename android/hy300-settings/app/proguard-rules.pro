# Telas de preferência são instanciadas pelo nome (Preference.setFragment).
-keep public class * extends androidx.fragment.app.Fragment { public <init>(); }
# Usado em testes por reflexão/estático
-keep class io.github.hy300.settings.Keystone { *; }
