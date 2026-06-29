#!/usr/bin/env python3
"""Reduce viser streaming/render load with many robots WITHOUT cutting the count:
  - cap visual scene updates to ~30 Hz (was every physics step)
  - drop the per-robot velocity-command markers
Physics + training are unaffected. Idempotent."""
import sys
P = "/home/sp9/rl-demo/IsaacLab/source/isaaclab_visualizers/isaaclab_visualizers/viser/viser_visualizer.py"
src = open(P).read()
if "_last_render_t" in src:
    print("already optimized"); sys.exit(0)

old = '''        self._follow_tracked_env()

        self._sim_time += dt
        self._viewer.begin_frame(self._sim_time)
        try:
            self._viewer.log_state(self._state)
            if self.cfg.enable_markers:
                self._render_markers(num_envs)
        finally:
            self._viewer.end_frame()'''

new = '''        self._sim_time += dt
        # cap visual updates to ~30 Hz: cuts streaming/render load with many robots.
        # physics + training run at full rate regardless of this throttle.
        if (self._sim_time - getattr(self, "_last_render_t", -1e9)) < (1.0 / 30.0):
            return
        self._last_render_t = self._sim_time

        self._follow_tracked_env()
        self._viewer.begin_frame(self._sim_time)
        try:
            self._viewer.log_state(self._state)
            # per-robot velocity markers disabled to reduce geometry at high env counts
        finally:
            self._viewer.end_frame()'''

if old not in src:
    print("ANCHOR NOT FOUND - aborting"); sys.exit(1)
src = src.replace(old, new, 1)
open(P, "w").write(src)
print("render optimization applied (30 Hz cap + markers off)")
