#!/usr/bin/env python3
"""Inject a booth instant-reset hook into rsl_rl's OnPolicyRunner.learn() loop.
On each iteration, if /tmp/demo_reset exists, reload the seed checkpoint (snap the
policy back to 'clumsy') and reset the robots -- no Isaac Sim reboot, so it's
instant. Emits 'DEMO_RESET_MARKER' so the dashboard can restart its charts.
Idempotent + fully defensive (failure leaves training untouched)."""
import sys
P = "/home/sp9/rl-demo/IsaacLab/_isaac_sim/kit/python/lib/python3.12/site-packages/rsl_rl/runners/on_policy_runner.py"
src = open(P).read()
if "DEMO_RESET_MARKER" in src:
    print("already patched"); sys.exit(0)

anchor = "        for it in range(start_it, total_it):\n            start = time.time()\n"
if anchor not in src:
    print("ANCHOR NOT FOUND"); sys.exit(1)

hook = (
    "        for it in range(start_it, total_it):\n"
    "            # --- booth instant-reset hook ---\n"
    "            import os as _os\n"
    "            if _os.path.exists('/tmp/demo_reset'):\n"
    "                try:\n"
    "                    _os.remove('/tmp/demo_reset')\n"
    "                    self.load('/home/sp9/rl-demo/IsaacLab/logs/rsl_rl/g1_flat/booth_seed/model_100.pt')\n"
    "                    _r = self.env.reset()\n"
    "                    obs = _r[0] if isinstance(_r, tuple) else _r\n"
    "                    print('DEMO_RESET_MARKER', flush=True)\n"
    "                except Exception as _e:\n"
    "                    print('[booth-reset-hook]', _e, flush=True)\n"
    "            start = time.time()\n"
)
src = src.replace(anchor, hook, 1)
open(P, "w").write(src)
print("reset hook injected")
