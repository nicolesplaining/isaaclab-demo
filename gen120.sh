#!/usr/bin/env bash
# One-shot: resume booth_seed/model_100 -> train to iter 120, saving every 5 iters
# (105,110,115,120) into a fresh run dir. Headless, no viz.
cd ~/rl-demo/IsaacLab
export TERM=xterm
export LD_PRELOAD="$LD_PRELOAD:/lib/aarch64-linux-gnu/libgomp.so.1"
export PYTHONUNBUFFERED=1
export PXR_WORK_THREAD_LIMIT=16 OPENBLAS_NUM_THREADS=16 OMP_NUM_THREADS=16
LOG=~/rl-demo/gen120.log
rm -f "$LOG" /tmp/gen120.done
echo "[gen120] start $(date)" > "$LOG"
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task=Isaac-Velocity-Flat-G1-v0 --viz none --num_envs 2048 --max_iterations 22 \
    --resume --load_run booth_seed --checkpoint model_100.pt \
    --kit_args=--/plugins/carb.tasking.plugin/threadCount=6 \
    agent.save_interval=5 agent.run_name=gen120 >> "$LOG" 2>&1
echo "GENDONE exit=$? at $(date)" >> "$LOG"; echo DONE > /tmp/gen120.done
