#!/usr/bin/env bash
# Headless RL training launcher (true headless via --viz none). Args: TASK MAX_ITERS
TASK="${1:-Isaac-Velocity-Flat-Unitree-Go2-v0}"
ITERS="${2:-150}"
cd ~/rl-demo/IsaacLab
export TERM=xterm
export LD_PRELOAD="$LD_PRELOAD:/lib/aarch64-linux-gnu/libgomp.so.1"
# kill only prior python training procs (NOT this launcher)
pkill -9 -f "rsl_rl/train.py" 2>/dev/null; sleep 2
LOG=~/rl-demo/train_run.log
rm -f "$LOG" /tmp/train.done
echo "[launcher] starting $TASK iters=$ITERS at $(date)" > "$LOG"
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py --task=$TASK --viz none --max_iterations $ITERS >> "$LOG" 2>&1
echo "DONE exit=$? at $(date)" >> "$LOG"; echo "DONE" > /tmp/train.done
