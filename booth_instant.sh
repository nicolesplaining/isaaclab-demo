#!/usr/bin/env bash
# BOOTH (instant-reset): ONE long-lived G1 training warm-started from model_100.
# The dashboard "Restart" button touches /tmp/demo_reset, and the training loop's
# hook reloads the checkpoint + resets the robots IN-PLACE (no sim reboot = instant).
# This script just keeps that one training alive (retries the Isaac boot-hang) and
# keeps dashboard:8800 + tensorboard:6006 up.
#   Args: SEED_RUN CHECKPOINT NUM_ENVS VIS
SEED_RUN="${1:-booth_seed}"
CKPT="${2:-model_100.pt}"
ENVS="${3:-2048}"
VIS="${4:-16}"
HUGE=999900          # effectively never-ending; resets are in-place
cd ~/rl-demo

echo "[booth_instant] full reset $(date)"
for i in $(seq 1 18); do
  pkill -9 -f booth_g1.sh 2>/dev/null
  pkill -9 -f hang_catch.sh 2>/dev/null
  pkill -9 -f train_watchdog.sh 2>/dev/null
  pkill -9 -f run_resume.sh 2>/dev/null
  pkill -9 -f run_train_viz.sh 2>/dev/null
  pkill -9 -f "_isaac_sim/kit/python" 2>/dev/null
  pkill -9 -f isaaclab.cli 2>/dev/null
  pkill -9 -f "python.sh scripts" 2>/dev/null
  sleep 1
done
sleep 4
rm -f /tmp/demo_reset

ss -tln 2>/dev/null | grep -q ":8800\b" || { setsid python3 ~/rl-demo/dashboard_server.py --port 8800 --log ~/rl-demo/train_viz.log </dev/null >~/rl-demo/dashboard.log 2>&1 & disown; }
ss -tln 2>/dev/null | grep -q ":6006\b" || { setsid bash ~/rl-demo/run_tensorboard.sh </dev/null >~/rl-demo/tensorboard.log 2>&1 & disown; }
sleep 2

# keepalive: ensure the single long-lived training is running; restart if it dies/hangs
while true; do
  if ! pgrep -f "_isaac_sim/kit/python.*train.py" >/dev/null 2>&1; then
    echo "[booth_instant] launching long-lived training (resume $SEED_RUN/$CKPT) $(date)"
    booted=0
    for attempt in 1 2 3 4 5; do
      setsid bash ~/rl-demo/run_resume.sh Isaac-Velocity-Flat-G1-v0 "$SEED_RUN" "$CKPT" "$HUGE" "$ENVS" "$VIS" </dev/null >/dev/null 2>&1 & disown
      for i in $(seq 1 22); do
        sleep 5
        grep -aq "Learning iteration" ~/rl-demo/train_viz.log 2>/dev/null && { booted=1; break; }
      done
      [ "$booted" -eq 1 ] && { echo "[booth_instant] booted (attempt $attempt)"; break; }
      echo "[booth_instant] boot-hang attempt $attempt, retrying"
      pkill -9 -f "rsl_rl/train.py" 2>/dev/null; pkill -9 -f isaaclab.cli 2>/dev/null
      for j in $(seq 1 20); do [ "$(pgrep -f '_isaac_sim/kit/python'|wc -l)" -eq 0 ] && break; sleep 1; done
      sleep 3
    done
  fi
  sleep 10
done
