#!/usr/bin/env bash
# BOOTH: G1 humanoid warm-started from a checkpoint, trains ~4 min LIVE (crowd +
# tracking spotlight), then loops for the next visitor. Self-healing (retries the
# Isaac Sim boot-hang). Leaves dashboard:8800 + tensorboard:6006 up across loops.
#   Args: SEED_RUN CHECKPOINT EXTRA_ITERS NUM_ENVS VIS
SEED_RUN="${1:-booth_seed}"
CKPT="${2:-model_100.pt}"
EXTRA="${3:-140}"     # iterations past the checkpoint (~4 min at ~1.7s/iter)
ENVS="${4:-2048}"
VIS="${5:-9}"
cd ~/rl-demo

echo "[booth_g1] full reset $(date)"
for i in $(seq 1 18); do
  pkill -9 -f hang_catch.sh 2>/dev/null
  pkill -9 -f train_watchdog.sh 2>/dev/null
  pkill -9 -f run_resume.sh 2>/dev/null
  pkill -9 -f run_train_viz.sh 2>/dev/null
  pkill -9 -f booth_solo.sh 2>/dev/null
  pkill -9 -f "_isaac_sim/kit/python" 2>/dev/null
  pkill -9 -f isaaclab.cli 2>/dev/null
  pkill -9 -f "python.sh scripts" 2>/dev/null
  sleep 1
done
sleep 4

# dashboard + tensorboard (persist across loops)
ss -tln 2>/dev/null | grep -q ":8800\b" || { setsid python3 ~/rl-demo/dashboard_server.py --port 8800 --log ~/rl-demo/train_viz.log </dev/null >~/rl-demo/dashboard.log 2>&1 & disown; }
ss -tln 2>/dev/null | grep -q ":6006\b" || { setsid bash ~/rl-demo/run_tensorboard.sh </dev/null >~/rl-demo/tensorboard.log 2>&1 & disown; }
sleep 2

# booth replay loop: each pass = one full warm-started 4-min demo
while true; do
  echo "[booth_g1] === new demo cycle: resume $SEED_RUN/$CKPT +$EXTRA iters $(date) ==="
  booted=0
  for attempt in 1 2 3 4 5; do
    setsid bash ~/rl-demo/run_resume.sh Isaac-Velocity-Flat-G1-v0 "$SEED_RUN" "$CKPT" "$EXTRA" "$ENVS" "$VIS" </dev/null >/dev/null 2>&1 & disown
    for i in $(seq 1 22); do          # ~110s watchdog window for boot-hang
      sleep 5
      grep -aq "Learning iteration" ~/rl-demo/train_viz.log 2>/dev/null && { booted=1; break; }
    done
    [ "$booted" -eq 1 ] && { echo "[booth_g1] booted (attempt $attempt)"; break; }
    echo "[booth_g1] boot-hang attempt $attempt, retrying"
    pkill -9 -f "rsl_rl/train.py" 2>/dev/null; pkill -9 -f isaaclab.cli 2>/dev/null
    for j in $(seq 1 20); do [ "$(pgrep -f '_isaac_sim/kit/python'|wc -l)" -eq 0 ] && break; sleep 1; done
    sleep 3
  done
  # wait for this demo to finish (reaches max iters)
  while [ ! -f /tmp/trainviz.done ]; do sleep 5; done
  echo "[booth_g1] cycle complete $(date); looping for next visitor"
  sleep 4
done
