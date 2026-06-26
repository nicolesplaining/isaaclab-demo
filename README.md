# Live RL Training Demo — DGX Spark (GB10 / Blackwell)

A booth showpiece: a Unitree Go2 quadruped learns to walk **from scratch in ~3 minutes**,
fully on-device on the Spark. Visitors watch the robot go from random flailing to a clean
gait, with the reward curve climbing live alongside the 3D view.

Built on **NVIDIA Isaac Sim 6.0 + Isaac Lab 3.0-beta2** (compiled from source for aarch64),
rsl_rl PPO, task `Isaac-Velocity-Flat-Unitree-Go2-v0`. GPU PhysX, ~2048 parallel robots.

## Quick start (booth)
```bash
ssh sp9@100.97.64.41
bash ~/rl-demo/booth_start.sh           # one fresh run, prints the two URLs
# or, unattended cycling every 4 min:
bash ~/rl-demo/booth_loop.sh 240
```
Then open the SINGLE client-facing page (booth machine or over Tailscale @ 100.97.64.41):
- **Booth dashboard:** http://<spark-ip>:8800/   <-- the one URL to show visitors

The dashboard embeds the live 3D robot view (viser) and renders clean live charts:
reward (up), episode length (up), velocity tracking error (down), plus iteration/steps-per-sec.
Engineer views remain available: viser http://<spark-ip>:8080 , TensorBoard http://<spark-ip>:6006 .

To restart for the next visitor, just re-run `booth_start.sh` (it kills the prior run
and starts fresh from iteration 0 — robot flails again, then learns).

## What converges (measured on GB10)
| envs | iter time | ~time to clean walk | notes |
|------|-----------|---------------------|-------|
| 2048 | ~1.0 s    | ~3 min (180 iters)  | booth default; reward -0.6 -> +20 |
| 4096 | ~1.1 s    | ~3 min (150 iters)  | headless, fastest/most stable convergence |
| 64   | ~0.6 s    | does NOT converge   | too few envs for clean locomotion |

## Scripts
- `booth_start.sh [TASK] [ITERS] [ENVS]` — ensure TensorBoard up + fresh viser training run.
- `booth_loop.sh [CYCLE_S] [ITERS] [ENVS]` — restart the demo every CYCLE seconds, forever.
- `run_train_viz.sh TASK ITERS ENVS` — training with live viser web viewer (port 8080).
- `run_train.sh TASK ITERS` — true-headless training (fastest; `--viz none`).
- `run_tensorboard.sh` — TensorBoard on 0.0.0.0:6006 over the rsl_rl logs.

## Other tasks to try (swap into booth_start.sh)
`Isaac-Velocity-Flat-Anymal-C-v0`, `Isaac-Velocity-Flat-G1-v0` (humanoid),
`Isaac-Velocity-Flat-Spot-v0`, `Isaac-Velocity-Flat-H1-v0` (humanoid).

See NOTES.md for build details and the gotchas that matter (version pairing, --viz none).
