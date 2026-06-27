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

## Update: bipedal G1 + hang fix + follow camera (2026-06-26)
- Demo task is now `Isaac-Velocity-Flat-G1-v0` (bipedal). Trains to walk (reward dips
  negative early as episodes lengthen, then climbs to ~+9 by iter ~390).
- **Boot-hang ROOT CAUSE:** carb spawns one worker thread per core (20 on GB10), and
  carb.dictionary plugin pre-startup intermittently deadlocks on a futex (~1/3 boots).
  Confirmed via gdb (main thread stuck in carbOnPluginPreStartup futex wait).
  **FIX:** cap carb threads to 6 via `--kit_args=--/plugins/carb.tasking.plugin/threadCount=6`
  plus env PXR_WORK_THREAD_LIMIT/OMP_NUM_THREADS=6 (in run_train_viz.sh). Note: must use
  `--kit_args=` (equals form) or argparse treats the `--/...` value as a flag.
- **Follow camera:** patch_follow_camera.py patches the viser viewer to keep the tracked
  robot centered (apply to IsaacLab/source/isaaclab_visualizers/.../viser/viser_visualizer.py).
- **Self-healing:** train_watchdog.sh retries the boot-hang; run_demo.sh / booth_start.sh use it.
