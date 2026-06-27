#!/usr/bin/env bash
# Atomic demo (re)launcher: kill EVERYTHING (incl. hunters/watchdogs/loops), settle,
# then start dashboard + tensorboard + ONE self-healing training watchdog. No racing.
# Invoke: ssh host 'nohup bash ~/rl-demo/run_demo.sh <TASK> <ITERS> <ENVS> <VIS> >/tmp/demo.out 2>&1 & echo GO'
set -u
TASK="${1:-Isaac-Velocity-Flat-Unitree-Go2-v0}"
ITERS="${2:-200}"
ENVS="${3:-2048}"
VIS="${4:-1}"
cd ~/rl-demo

echo "[demo] sustained kill (hunters, watchdogs, loops, training) $(date)"
for i in $(seq 1 20); do
  pkill -9 -f hang_catch.sh 2>/dev/null
  pkill -9 -f keepwarm.sh 2>/dev/null
  pkill -9 -f train_watchdog.sh 2>/dev/null
  pkill -9 -f booth_solo.sh 2>/dev/null
  pkill -9 -f booth_restart.sh 2>/dev/null
  pkill -9 -f booth_start.sh 2>/dev/null
  pkill -9 -f booth_loop.sh 2>/dev/null
  pkill -9 -f run_train_viz.sh 2>/dev/null
  pkill -9 -f "_isaac_sim/kit/python" 2>/dev/null
  pkill -9 -f isaaclab.cli 2>/dev/null
  pkill -9 -f "python.sh scripts" 2>/dev/null
  pkill -9 -f dashboard_server.py 2>/dev/null
  pkill -9 -f "tensorboard.main" 2>/dev/null
  sleep 1
done
echo "[demo] kit procs left: $(pgrep -f '_isaac_sim/kit/python' | wc -l)"
sleep 5

echo "[demo] start dashboard"
setsid python3 ~/rl-demo/dashboard_server.py --port 8800 --log ~/rl-demo/train_viz.log \
    </dev/null >~/rl-demo/dashboard.log 2>&1 & disown
echo "[demo] start tensorboard"
setsid bash ~/rl-demo/run_tensorboard.sh </dev/null >~/rl-demo/tensorboard.log 2>&1 & disown

echo "[demo] start ONE watchdog: $TASK iters=$ITERS envs=$ENVS visible=$VIS"
setsid bash ~/rl-demo/train_watchdog.sh "$TASK" "$ITERS" "$ENVS" "$VIS" </dev/null >/tmp/watchdog.out 2>&1 & disown
sleep 3
echo "[demo] watchdogs=$(pgrep -fc train_watchdog.sh) dash=$(ss -tln 2>/dev/null|grep -c :8800) done $(date)"
