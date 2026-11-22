#!/usr/bin/env bash
# Ajustes leves de desempenho.
set -euo pipefail
for k in window_animation_scale transition_animation_scale animator_duration_scale; do
  adb shell settings put global "$k" 0.5
done
