#!/usr/bin/env bash
# Self-healing training launcher: starts a run and, if it hits the intermittent
# Isaac Sim boot-hang (no PPO iteration within ~110s), kills it and retries.
# Args: TASK ITERS ENVS VIS  (defaults: Go2 flat, 200, 2048, 1)
TASK="${1:-Isaac-Velocity-Flat-Unitree-Go2-v0}"
ITERS="${2:-200}"
ENVS="${3:-2048}"
VIS="${4:-1}"
LOG=~/rl-demo/train_viz.log
cd ~/rl-demo

for attempt in 1 2 3 4 5; do
  echo "[watchdog] attempt $attempt: launching ($TASK envs=$ENVS visible=$VIS) $(date)"
  # run_train_viz.sh kills any prior rsl_rl/train.py, clears the log, then boots
  setsid bash ~/rl-demo/run_train_viz.sh "$TASK" "$ITERS" "$ENVS" "$VIS" </dev/null >/dev/null 2>&1 &
  disown
  # watchdog: wait up to ~110s for the first PPO iteration
  booted=0
  for i in $(seq 1 22); do
    sleep 5
    if grep -aq "Learning iteration" "$LOG" 2>/dev/null; then booted=1; break; fi
  done
  if [ "$booted" -eq 1 ]; then
    echo "[watchdog] SUCCESS on attempt $attempt (iterating) $(date)"
    exit 0
  fi
  echo "[watchdog] attempt $attempt HUNG (no iteration in ~110s); killing + retrying"
  pkill -9 -f "rsl_rl/train.py" 2>/dev/null
  pkill -9 -f isaaclab.cli 2>/dev/null
  pkill -9 -f "_isaac_sim/kit/python" 2>/dev/null
  # wait until kit fully dead before retry (avoid lock contention)
  for j in $(seq 1 20); do [ "$(pgrep -f '_isaac_sim/kit/python' | wc -l)" -eq 0 ] && break; sleep 1; done
  sleep 4
done
echo "[watchdog] FAILED after 5 attempts $(date)"
exit 1
