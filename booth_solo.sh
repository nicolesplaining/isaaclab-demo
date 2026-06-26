#!/usr/bin/env bash
# Definitive: sustained-kill ALL Isaac training + launchers for 25s (outlasts any
# mid-boot launcher), then start EXACTLY ONE run. Leaves dashboard:8800 + tb:6006 alone.
# Invoke: ssh host 'nohup bash ~/rl-demo/booth_solo.sh >/tmp/solo.out 2>&1 & echo GO'
set -u
TASK="${1:-Isaac-Velocity-Flat-Unitree-Go2-v0}"
ITERS="${2:-200}"
ENVS="${3:-2048}"
VIS="${4:-32}"
cd ~/rl-demo

echo "[solo] sustained kill begin $(date)"
for i in $(seq 1 25); do
  pkill -9 -f booth_restart.sh 2>/dev/null
  pkill -9 -f booth_start.sh 2>/dev/null
  pkill -9 -f run_train_viz.sh 2>/dev/null
  pkill -9 -f "_isaac_sim/kit/python" 2>/dev/null   # every Isaac kit python (only training uses it)
  pkill -9 -f "isaaclab.cli" 2>/dev/null
  pkill -9 -f "python.sh scripts/reinforcement" 2>/dev/null
  sleep 1
done
echo "[solo] kit procs after sustained kill: $(pgrep -f '_isaac_sim/kit/python' | wc -l)"
sleep 4  # settle GPU + shader-cache lock

# ensure dashboard is up (don't disturb a working one)
if ! ss -tln 2>/dev/null | grep -q ":8800\b"; then
  setsid python3 ~/rl-demo/dashboard_server.py --port 8800 --log ~/rl-demo/train_viz.log \
      </dev/null >~/rl-demo/dashboard.log 2>&1 & disown
fi

echo "[solo] starting ONE run task=$TASK envs=$ENVS visible=$VIS"
setsid bash ~/rl-demo/run_train_viz.sh "$TASK" "$ITERS" "$ENVS" "$VIS" </dev/null >/dev/null 2>&1 & disown
sleep 4
echo "[solo] launchers=$(pgrep -fc run_train_viz.sh) done $(date)"
