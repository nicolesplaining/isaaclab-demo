#!/usr/bin/env bash
# RL training WITH live viser web viewer (port 8080).
# Args: TASK MAX_ITERS NUM_ENVS MAX_VISIBLE_ENVS
#   NUM_ENVS         = robots used for training (more = better/faster convergence)
#   MAX_VISIBLE_ENVS = robots actually rendered in viser (keep small so the browser stays smooth)
TASK="${1:-Isaac-Velocity-Flat-Unitree-Go2-v0}"
ITERS="${2:-200}"
ENVS="${3:-2048}"
VIS="${4:-32}"
cd ~/rl-demo/IsaacLab
export TERM=xterm
export LD_PRELOAD="$LD_PRELOAD:/lib/aarch64-linux-gnu/libgomp.so.1"
pkill -9 -f "rsl_rl/train.py" 2>/dev/null; sleep 2
LOG=~/rl-demo/train_viz.log
rm -f "$LOG" /tmp/trainviz.done
echo "[launcher] $TASK iters=$ITERS envs=$ENVS visible=$VIS viz=viser at $(date)" > "$LOG"
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task=$TASK --viz viser --num_envs $ENVS --max_visible_envs $VIS --max_iterations $ITERS >> "$LOG" 2>&1
echo "DONE exit=$? at $(date)" >> "$LOG"; echo DONE > /tmp/trainviz.done
