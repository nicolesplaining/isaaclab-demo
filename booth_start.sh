#!/usr/bin/env bash
# Booth one-shot: (re)start a fresh RL training run from scratch with live viewer.
# Ensures TensorBoard is up, kills any prior training, launches viser training.
# Usage: ./booth_start.sh [TASK] [ITERS] [ENVS]
set -u
TASK="${1:-Isaac-Velocity-Flat-Unitree-Go2-v0}"
ITERS="${2:-200}"
ENVS="${3:-2048}"
IPS=$(hostname -I)
cd ~/rl-demo

# 1) TensorBoard (start if not listening on 6006)
if ! ss -tln 2>/dev/null | grep -q :6006; then
  setsid bash ~/rl-demo/run_tensorboard.sh </dev/null >~/rl-demo/tensorboard.log 2>&1 & disown
  sleep 6
fi

# 2) Fresh training run with live viser viewer (launcher kills any prior train.py)
setsid bash ~/rl-demo/run_train_viz.sh "$TASK" "$ITERS" "$ENVS" </dev/null >/dev/null 2>&1 & disown

echo "=================================================="
echo " BOOTH DEMO STARTED: $TASK ($ENVS envs, $ITERS iters)"
echo "  Open in a browser on the booth machine or over Tailscale:"
for ip in $IPS localhost; do echo "    viser 3D : http://$ip:8080    |  TensorBoard : http://$ip:6006"; done
echo "  (Spark Tailscale IP is typically 100.97.64.41)"
echo "  ~3 minutes: robot flails -> walks. Re-run this script to restart."
echo "=================================================="
