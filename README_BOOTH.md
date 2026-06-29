# DGX Spark — RL Booth Demo

Live reinforcement-learning demo: a crowd of **Unitree G1 humanoids** learns to walk
in real time (Isaac Sim + Isaac Lab, rsl_rl PPO), shown in a browser with a 3D viewer,
a "spotlight" close-up that tracks one robot, and live reward / episode-length /
tracking-error curves. Everything runs **on the Spark** — no other machine required.

---

## Quick start

The demo is a **systemd user service** and **auto-starts on boot** (no login needed).

- After a reboot: wait ~90s, then open **http://localhost:8080**. Nothing to run.
- To (re)start by hand and print the URLs:

  ```bash
  ~/rl-demo/start_demo.sh
  ```

---

## Where to open it

Services bind `0.0.0.0`, so they're reachable at any of the Spark's addresses.

| What                | Local (on the Spark)      | From another machine        |
|---------------------|---------------------------|-----------------------------|
| 3D viewer (viser)   | http://localhost:8080     | http://<SPARK-IP>:8080      |
| Dashboard (curves)  | http://localhost:8800     | http://<SPARK-IP>:8800      |
| TensorBoard         | http://localhost:6006     | http://<SPARK-IP>:6006      |

`<SPARK-IP>`: LAN = `10.229.38.187` (check with `hostname -I`).

**The booth display is the dashboard at :8800** — it embeds the viewer plus the curves
and the **Restart** button. (Viewer-only is :8080.)

### Remote access caveat (important for handoff)
Internet/remote access currently works **only through the owner's Tailscale tailnet**
(Spark = `100.97.64.41`, owner `nicolesplaining@`). Someone who is **not** on that
tailnet must either be on the **same LAN** or have **local/console** access. To give a
new person remote access, add them to the tailnet (or set up their own networking).

---

## Managing the service

```bash
systemctl --user status  booth-demo        # is it running?
journalctl --user -u booth-demo -f         # live logs
systemctl --user restart booth-demo        # full restart (~90s sim reboot)
systemctl --user stop    booth-demo        # take it down
systemctl --user start   booth-demo        # bring it up
```

- Auto-start on boot is already enabled (`systemctl --user is-enabled booth-demo` → `enabled`)
  and **linger is on** (`loginctl show-user sp9 | grep Linger` → `Linger=yes`), which is
  what lets it start at boot without anyone logging in.
- `Restart=always`: if the keepalive dies it relaunches automatically.

---

## The Restart button (instant reset)

The dashboard's **Restart** button gives an **instant** reset (no ~90s sim reboot): it
touches `/tmp/demo_reset`; the training loop reloads the checkpoint and resets the robots
in place. The on-screen iteration counter starts fresh at 1 and climbs to the cycle target;
the episode counter tracks the spotlight robot's falls/resets.

---

## Tuning knobs

| Want to change            | Where                                                            | Takes effect |
|---------------------------|-----------------------------------------------------------------|--------------|
| **Start checkpoint**      | `booth-demo.service` ExecStart arg + `on_policy_runner.py` hook* | service restart |
| **Iterations per arc**    | `dashboard_server.py` → `CYCLE_TARGET` (currently **135**)       | restart dashboard |
| **Robot count (visible)** | service ExecStart last arg `VIS` (currently **48**)              | service restart |
| **Robot spacing**         | `run_resume.sh` → `env.scene.env_spacing=` (currently **0.65**)  | service restart |

\* The checkpoint is set in **two** places and both must match:
1. `~/.config/systemd/user/booth-demo.service` → `ExecStart=... booth_instant.sh booth_seed model_110.pt 2048 48`
2. The instant-reset hook in
   `~/rl-demo/IsaacLab/_isaac_sim/kit/python/lib/python3.12/site-packages/rsl_rl/runners/on_policy_runner.py`
   (search for `booth_seed/model_`).

After editing the service file: `systemctl --user daemon-reload && systemctl --user restart booth-demo`.

Available checkpoints live in
`~/rl-demo/IsaacLab/logs/rsl_rl/g1_flat/booth_seed/` (e.g. `model_100/105/110/115/120/150/200…`).

### Generating a new checkpoint
`~/rl-demo/gen120.sh` shows the pattern: resume from an existing checkpoint, set
`agent.save_interval=N` and `--max_iterations` (relative to the loaded iter), run headless
(`--viz none`), then copy the resulting `model_*.pt` from the new timestamped run dir under
`logs/rsl_rl/g1_flat/` into `booth_seed/`. Free the GPU first (`systemctl --user stop booth-demo`).

---

## File map (`~/rl-demo/`)

| File                       | Role                                                                 |
|----------------------------|----------------------------------------------------------------------|
| `start_demo.sh`            | One-command start; ensures the service is up and prints URLs.        |
| `booth_instant.sh`         | Foreground self-healing keepalive (dashboard + TB + training loop).  |
| `run_resume.sh`            | Launches one warm-started training with the viser viewer.            |
| `dashboard_server.py`      | The booth dashboard (:8800): embeds viewer + live curves + Restart.  |
| `gen120.sh`                | Example checkpoint-generation job.                                   |
| `IsaacLab/`, `IsaacSim/`   | Built-from-source engines (huge; **not** in git).                    |

Two source patches live **inside the engine tree**, not in the repo:
- `IsaacLab/source/isaaclab_visualizers/.../viser/viser_visualizer.py` — spotlight follow,
  static main camera, ~24 Hz render cap.
- `…/site-packages/rsl_rl/runners/on_policy_runner.py` — instant-reset hook + spotlight
  episode counter.

---

## Gotchas / notes

- **Not reproducible from the GitHub repo alone.** `nicolesplaining/isaaclab-demo` has the
  scripts, but the Isaac Sim/Lab build, the checkpoints (`logs/` is gitignored), and the two
  engine-tree patches above are **not** in it. The working demo only exists on **this Spark**.
- **Isaac boot-hang workaround:** training must run with
  `--kit_args=--/plugins/carb.tasking.plugin/threadCount=6` (already in `run_resume.sh`).
  Without it the sim deadlocks on startup. The keepalive retries boot automatically.
- **Version pairing:** Isaac Sim 6.0 ↔ Isaac Lab `release/3.0.0-beta2`. Don't switch Isaac
  Lab to `main` (task registration breaks).
- `PYTHONUNBUFFERED=1` is required (set in `run_resume.sh`) so the dashboard reads the log
  promptly and the on-screen counter starts at iteration 1.
- Working over SSH? Tailscale sessions drop often; run long commands detached
  (`setsid … & disown`) and re-check state rather than holding the connection.

---

## Troubleshooting

- **Nothing at :8080 after a reboot:** give it ~90s (sim boot). Then
  `systemctl --user status booth-demo` and `journalctl --user -u booth-demo -f`.
- **Service active but no 3D view:** check training booted —
  `grep -c "Learning iteration" ~/rl-demo/train_viz.log` should be increasing; if not,
  `systemctl --user restart booth-demo`.
- **Curves look frozen:** the dashboard reads `~/rl-demo/train_viz.log`; if training died the
  keepalive should relaunch it within ~10s.
- **Want a totally clean slate:** `systemctl --user restart booth-demo` (kills stale training
  + sim and reboots from the configured checkpoint).
