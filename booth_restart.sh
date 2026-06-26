#!/usr/bin/env bash
# Atomic full restart of the booth demo. Safe to invoke via:
#   ssh host 'nohup bash ~/rl-demo/booth_restart.sh >/tmp/restart.out 2>&1 & echo GO'
# Kills everything, waits, then starts dashboard + tensorboard + fresh training.
set -u
TASK="${1:-Isaac-Velocity-Flat-Unitree-Go2-v0}"
ITERS="${2:-200}"
ENVS="${3:-2048}"
VIS="${4:-32}"
DASH_PORT=8800
cd ~/rl-demo

echo "[restart] killing old procs $(date)"
pkill -9 -f dashboard_server.py 2>/dev/null
pkill -9 -f run_train_viz.sh 2>/dev/null
# loop until ALL kit training processes are truly gone (avoids shader-cache lock
# contention that hangs a new Isaac Sim boot if an old one is still dying)
for i in $(seq 1 30); do
  pkill -9 -f "rsl_rl/train.py" 2>/dev/null
  pkill -9 -f isaaclab.cli 2>/dev/null
  pkill -9 -f "python.sh scripts/reinforcement" 2>/dev/null
  n=$(pgrep -f "kit/python.*train.py" | wc -l)
  [ "$n" -eq 0 ] && { echo "[restart] kit procs gone after $((i*1))s"; break; }
  sleep 1
done
sleep 4   # extra settle so the GPU/shader-cache lock is released

echo "[restart] starting dashboard on :$DASH_PORT"
setsid python3 ~/rl-demo/dashboard_server.py --port "$DASH_PORT" --log ~/rl-demo/train_viz.log \
    </dev/null >~/rl-demo/dashboard.log 2>&1 &
disown
sleep 2

if ! ss -tln 2>/dev/null | grep -q ":6006\b"; then
  echo "[restart] starting tensorboard"
  setsid bash ~/rl-demo/run_tensorboard.sh </dev/null >~/rl-demo/tensorboard.log 2>&1 &
  disown
  sleep 4
fi

echo "[restart] starting training task=$TASK envs=$ENVS visible=$VIS iters=$ITERS"
setsid bash ~/rl-demo/run_train_viz.sh "$TASK" "$ITERS" "$ENVS" "$VIS" </dev/null >/dev/null 2>&1 &
disown
sleep 2
echo "[restart] launched. dash=$(ss -tln 2>/dev/null|grep -c :$DASH_PORT) tb=$(ss -tln 2>/dev/null|grep -c :6006)"
echo "[restart] done $(date)"
