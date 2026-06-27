#!/usr/bin/env bash
# Resume training from a saved checkpoint (warm-start) with live viser viewer.
# Args: TASK LOAD_RUN CHECKPOINT EXTRA_ITERS NUM_ENVS VIS
TASK="${1:-Isaac-Velocity-Flat-G1-v0}"
LOAD_RUN="${2}"
CKPT="${3:-model_100.pt}"
EXTRA="${4:-110}"              # iterations to train past the checkpoint (~3 min)
ENVS="${5:-2048}"
VIS="${6:-9}"
cd ~/rl-demo/IsaacLab
export TERM=xterm
export LD_PRELOAD="$LD_PRELOAD:/lib/aarch64-linux-gnu/libgomp.so.1"
export PXR_WORK_THREAD_LIMIT=6 OPENBLAS_NUM_THREADS=6 OMP_NUM_THREADS=6
# checkpoint iter number -> max_iterations = ckpt_iter + EXTRA
CKPT_ITER=$(echo "$CKPT" | grep -oE "[0-9]+")
MAXIT=$(( CKPT_ITER + EXTRA ))
pkill -9 -f "rsl_rl/train.py" 2>/dev/null; sleep 2
LOG=~/rl-demo/train_viz.log
rm -f "$LOG" /tmp/trainviz.done
date +%s > ~/rl-demo/train_start.epoch
echo "[launcher] RESUME $TASK from $LOAD_RUN/$CKPT (iter $CKPT_ITER) -> $MAXIT, viz, visible=$VIS at $(date)" > "$LOG"
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task=$TASK --viz viser --num_envs $ENVS --max_visible_envs $VIS --max_iterations $MAXIT \
    --resume --load_run "$LOAD_RUN" --checkpoint "$CKPT" \
    --kit_args=--/plugins/carb.tasking.plugin/threadCount=6 \
    env.scene.env_spacing=1.0 >> "$LOG" 2>&1
echo "DONE exit=$? at $(date)" >> "$LOG"; echo DONE > /tmp/trainviz.done
