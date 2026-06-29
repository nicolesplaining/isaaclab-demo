#!/usr/bin/env python3
"""On reset, hold training for ~3s while pumping fresh frames to the browser, so the
viewer catches up and the user sees the run from iteration 1 (not iter ~5).
  1) viser viewer 30Hz cap -> wall-clock based (so it renders while physics is paused)
  2) reset hook -> after reload+reset, render the fresh scene for ~3s before resuming
"""
import sys

# --- 1) viewer cap -> wall-clock ---
V = "/home/sp9/rl-demo/IsaacLab/source/isaaclab_visualizers/isaaclab_visualizers/viser/viser_visualizer.py"
vs = open(V).read()
old_cap = '''        self._sim_time += dt
        # cap visual updates to ~30 Hz: cuts streaming/render load with many robots.
        # physics + training run at full rate regardless of this throttle.
        if (self._sim_time - getattr(self, "_last_render_t", -1e9)) < (1.0 / 30.0):
            return
        self._last_render_t = self._sim_time'''
new_cap = '''        self._sim_time += dt
        # cap visual updates to ~30 Hz (WALL-CLOCK so it still renders while physics is
        # paused during a reset hold). cuts streaming/render load with many robots.
        import time as _wt
        _now = _wt.time()
        if (_now - getattr(self, "_last_render_wt", -1e9)) < (1.0 / 30.0):
            return
        self._last_render_wt = _now'''
if "_last_render_wt" in vs:
    print("viewer cap already wall-clock")
elif old_cap in vs:
    open(V, "w").write(vs.replace(old_cap, new_cap, 1)); print("viewer cap -> wall-clock OK")
else:
    print("VIEWER CAP ANCHOR NOT FOUND"); sys.exit(1)

# --- 2) reset hook -> add render hold ---
R = "/home/sp9/rl-demo/IsaacLab/_isaac_sim/kit/python/lib/python3.12/site-packages/rsl_rl/runners/on_policy_runner.py"
rs = open(R).read()
old_hook = """                    _r = self.env.reset()
                    obs = _r[0] if isinstance(_r, tuple) else _r
                    print('DEMO_RESET_MARKER', flush=True)"""
new_hook = """                    _r = self.env.reset()
                    obs = _r[0] if isinstance(_r, tuple) else _r
                    print('DEMO_RESET_MARKER', flush=True)
                    # hold ~3s and pump frames so the browser renders the fresh scene
                    # before training advances (user sees the run from iteration 1).
                    import time as _time
                    _sim = getattr(getattr(self.env, 'unwrapped', self.env), 'sim', None)
                    if _sim is not None:
                        for _ in range(45):
                            try:
                                _sim.render()
                            except Exception:
                                pass
                            _time.sleep(0.07)"""
if "hold ~3s and pump frames" in rs:
    print("reset hold already present")
elif old_hook in rs:
    open(R, "w").write(rs.replace(old_hook, new_hook, 1)); print("reset render-hold OK")
else:
    print("RESET HOOK ANCHOR NOT FOUND"); sys.exit(1)
