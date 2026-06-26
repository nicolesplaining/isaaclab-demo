#!/usr/bin/env bash
# Booth one-shot: start the full single-page demo from scratch.
#   - dashboard web page  (port 8800)  <-- the client-facing URL
#   - viser 3D viewer      (port 8080)  embedded inside the dashboard
#   - TensorBoard          (port 6006)  optional, for engineers
# Re-run to restart fresh (robot flails -> walks again).
# Usage: ./booth_start.sh [TASK] [ITERS] [ENVS]
set -u
TASK="${1:-Isaac-Velocity-Flat-Unitree-Go2-v0}"
ITERS="${2:-200}"
ENVS="${3:-2048}"
DASH_PORT=8800
cd ~/rl-demo

start_bg () {  # start_bg <pattern-to-check> <command...>
  setsid bash -c "$1" </dev/null >>"$2" 2>&1 &
  disown
}

# 1) Dashboard web server (single client-facing page)
if ! ss -tln 2>/dev/null | grep -q ":${DASH_PORT}\b"; then
  setsid python3 ~/rl-demo/dashboard_server.py --port "$DASH_PORT" --log ~/rl-demo/train_viz.log \
      </dev/null >~/rl-demo/dashboard.log 2>&1 & disown
  sleep 1
fi

# 2) TensorBoard (start if not already up)
if ! ss -tln 2>/dev/null | grep -q ":6006\b"; then
  setsid bash ~/rl-demo/run_tensorboard.sh </dev/null >~/rl-demo/tensorboard.log 2>&1 & disown
  sleep 4
fi

# 3) Fresh training run WITH live viser viewer (launcher kills any prior train.py)
setsid bash ~/rl-demo/run_train_viz.sh "$TASK" "$ITERS" "$ENVS" </dev/null >/dev/null 2>&1 & disown

IPS=$(hostname -I)
echo "=================================================="
echo " BOOTH DEMO STARTED: $TASK ($ENVS envs, $ITERS iters)"
echo ""
echo "  >>> OPEN THIS ONE PAGE (booth display / any tailnet browser): <<<"
for ip in $IPS localhost; do echo "        http://$ip:${DASH_PORT}/"; done
echo "  (Spark Tailscale IP is typically 100.97.64.41 -> http://100.97.64.41:${DASH_PORT}/)"
echo ""
echo "  It embeds the live 3D robot view + reward/length/error curves."
echo "  ~3 minutes: robot flails -> walks. Re-run this script to restart."
echo "=================================================="
