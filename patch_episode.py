#!/usr/bin/env python3
"""Track the spotlight robot's (env 0) episode count: increment whenever env 0
terminates (falls / times out) during the rollout, and reset to 1 on demo-restart.
Written to /dev/shm/spotlight_episode for the dashboard to read. Idempotent."""
import sys
R = "/home/sp9/rl-demo/IsaacLab/_isaac_sim/kit/python/lib/python3.12/site-packages/rsl_rl/runners/on_policy_runner.py"
s = open(R).read()
if "spotlight_episode" in s:
    print("already has episode tracking"); sys.exit(0)

# 1) count env-0 terminations in the rollout
roll_anchor = "                    obs, rewards, dones, extras = self.env.step(actions.to(self.env.device))\n"
if roll_anchor not in s:
    print("ROLLOUT ANCHOR NOT FOUND"); sys.exit(1)
roll_add = roll_anchor + (
    "                    try:\n"
    "                        if bool(dones[0]):\n"
    "                            self._spot_ep = getattr(self, '_spot_ep', 1) + 1\n"
    "                            open('/dev/shm/spotlight_episode', 'w').write(str(self._spot_ep))\n"
    "                    except Exception:\n"
    "                        pass\n"
)
s = s.replace(roll_anchor, roll_add, 1)

# 2) reset the episode count on demo-restart
reset_anchor = "                    print('DEMO_RESET_MARKER', flush=True)\n"
if reset_anchor not in s:
    print("RESET ANCHOR NOT FOUND"); sys.exit(1)
reset_add = reset_anchor + (
    "                    self._spot_ep = 1\n"
    "                    try:\n"
    "                        open('/dev/shm/spotlight_episode', 'w').write('1')\n"
    "                    except Exception:\n"
    "                        pass\n"
)
s = s.replace(reset_anchor, reset_add, 1)

open(R, "w").write(s)
print("episode tracking added")
