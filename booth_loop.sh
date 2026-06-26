#!/usr/bin/env bash
# Unattended booth loop: restart the demo from scratch every CYCLE seconds, forever.
# Usage: ./booth_loop.sh [CYCLE_SECONDS] [ITERS] [ENVS]
CYCLE="${1:-240}"; ITERS="${2:-200}"; ENVS="${3:-2048}"
while true; do
  bash ~/rl-demo/booth_start.sh Isaac-Velocity-Flat-Unitree-Go2-v0 "$ITERS" "$ENVS"
  echo "[booth_loop] next restart in ${CYCLE}s ($(date))"
  sleep "$CYCLE"
done
