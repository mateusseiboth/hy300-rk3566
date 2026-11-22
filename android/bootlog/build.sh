#!/usr/bin/env bash
# Compila bootlog.dex. Requer Android SDK (platform android-32 e build-tools).
set -euo pipefail
cd "$(dirname "$0")"
SDK="${ANDROID_HOME:-$HOME/Android/Sdk}"
BT="$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)"
JAR="$SDK/platforms/android-32/android.jar"
rm -rf out && mkdir -p out/classes
javac --release 11 -classpath "$JAR" -d out/classes $(find src -name '*.java') 2>/dev/null \
  || javac -source 11 -target 11 -bootclasspath "$JAR" -classpath "$JAR" -d out/classes $(find src -name '*.java')
"$BT/d8" --min-api 32 --lib "$JAR" --output out $(find out/classes -name '*.class')
mv out/classes.dex out/bootlog.dex
echo "ok: out/bootlog.dex"
