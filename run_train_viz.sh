#!/usr/bin/env bash
# RL training WITH live viser web viewer (port 8080) + follow camera.
# Args: TASK MAX_ITERS NUM_ENVS MAX_VISIBLE_ENVS
TASK="${1:-Isaac-Velocity-Flat-Unitree-Go2-v0}"
ITERS="${2:-200}"
ENVS="${3:-2048}"
VIS="${4:-6}"
cd ~/rl-demo/IsaacLab
export TERM=xterm
export LD_PRELOAD="$LD_PRELOAD:/lib/aarch64-linux-gnu/libgomp.so.1"
# --- carb startup-deadlock mitigation: cap worker threads (default = all 20 cores,
#     which intermittently deadlocks carb.dictionary pre-startup on this box) ---
export PXR_WORK_THREAD_LIMIT=6
export OPENBLAS_NUM_THREADS=6
export OMP_NUM_THREADS=6
KIT_ARGS="--/plugins/carb.tasking.plugin/threadCount=6"

pkill -9 -f "rsl_rl/train.py" 2>/dev/null; sleep 2
LOG=~/rl-demo/train_viz.log
rm -f "$LOG" /tmp/trainviz.done
date +%s > ~/rl-demo/train_start.epoch
echo "[launcher] $TASK iters=$ITERS envs=$ENVS visible=$VIS viz=viser threads=6 at $(date)" > "$LOG"
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task=$TASK --viz viser --num_envs $ENVS --max_visible_envs $VIS --max_iterations $ITERS \
    --kit_args="$KIT_ARGS" \
    env.scene.env_spacing=1.0 >> "$LOG" 2>&1
echo "DONE exit=$? at $(date)" >> "$LOG"; echo DONE > /tmp/trainviz.done
