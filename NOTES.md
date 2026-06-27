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

## Booth flow: warm-started 4-min G1 demo (2026-06-26)
- `booth_g1.sh booth_seed model_100.pt 140 2048 9` is the booth launcher: resumes G1
  from checkpoint model_100 (clumsy), trains ~140 iters (~4 min) LIVE to a confident
  walk, with a 9-robot crowd + tracking spotlight, then LOOPS for each visitor.
  Self-heals the Isaac boot-hang; keeps dashboard:8800 + tensorboard:6006 up.
- Seed checkpoint copied to logs/rsl_rl/g1_flat/booth_seed/ (stable; from the +9 run).
- `run_resume.sh TASK LOAD_RUN CKPT EXTRA_ITERS ENVS VIS` does the actual --resume launch.
- To change the "before": pick a different model_NNN.pt (lower = more dramatic/rougher,
  higher = cleaner but less change). To change duration: change EXTRA_ITERS (~35 iters/min).
- Note: warm-start framing = "watch it refine its gait live", not "from scratch". First
  ~40 logged iters include a metric-warmup ramp (robot already at checkpoint level visually).

## Instant in-place reset (2026-06-26)
- `booth_instant.sh booth_seed model_100.pt 2048 16` runs ONE long-lived G1 training
  (resume model_100, max_iterations huge). The dashboard "Restart" button hits
  /api/restart which touches /tmp/demo_reset.
- patch_reset_hook.py injects a hook into rsl_rl OnPolicyRunner.learn(): on the flag it
  reloads booth_seed/model_100.pt + resets the robots IN-PLACE (no Isaac Sim reboot) and
  prints DEMO_RESET_MARKER. Reset is ~instant (a few sec) vs ~90s for a sim reboot.
- Dashboard parses metrics only since the last DEMO_RESET_MARKER and shows iteration
  relative to the reset (capped at CYCLE_TARGET=140). Re-apply hook after IsaacLab updates.
- booth_g1.sh (reboot-per-reset, ~90s) is kept as the simpler fallback.
