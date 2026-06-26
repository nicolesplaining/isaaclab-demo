# RL Demo on DGX Spark (GB10 / Blackwell / aarch64) — Build Notes

Live reinforcement-learning booth demo: a quadruped (Unitree Go2) learns to walk
from scratch in ~3 minutes on the Spark, with live reward curves.

## Stack (verified working 2026-06-26)
- Isaac Sim **6.0.1-rc.7** built from source (default branch of isaac-sim/IsaacSim).
- Isaac Lab **release/3.0.0-beta2** (targets "Isaac Sim :: 6.0.0").
- RL: rsl_rl PPO. Task: `Isaac-Velocity-Flat-Unitree-Go2-v0`.
- torch 2.10.0+cu130, GPU = NVIDIA GB10, sm_121 (capability 12,1).

## CRITICAL GOTCHAS (cost real time — do not repeat)
1. **Version pairing.** Default clones mismatch: IsaacSim default = 6.0.x, but
   IsaacLab `main` targets Isaac Sim 5.1.0 -> `ModuleNotFoundError: omni.physics.tensors.impl`
   and ZERO tasks register. Fix: checkout IsaacLab `release/3.0.0-beta2` (the 6.0
   branch) and re-run `./isaaclab.sh --install`.
2. **`--viz none` for headless.** In beta2 the old `--headless` flag is deprecated and
   config visualizers are ON by default. Over SSH (no display) the Kit app HANGS at
   ~75ms loading `isaaclab_visualizers`. Use `--viz none` to force true headless.
3. **TTY required.** isaaclab.sh runs `tabs`; needs a pty. Use `ssh -tt` or run inside tmux/setsid.
4. **libgomp preload.** `export LD_PRELOAD=\$LD_PRELOAD:/lib/aarch64-linux-gnu/libgomp.so.1`

## Performance (GB10, Go2 flat, 4096 envs)
- ~1.1 s / PPO iteration. Boot to first iter ~24s (warm). 150 iters ~= 3 min wall-clock.
- GPU PhysX active (~50% GPU util during training).

## Run headless training
    bash ~/rl-demo/run_train.sh Isaac-Velocity-Flat-Unitree-Go2-v0 150
