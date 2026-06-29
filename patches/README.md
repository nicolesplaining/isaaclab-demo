# Engine-tree patches (reference snapshots)

These files live OUTSIDE this repo in the built Isaac Sim / Isaac Lab tree (gitignored)
and are the working, patched versions running on the Spark. Snapshotted here so the
changes are version-controlled. To restore on this Spark, copy each back to its path:

- `viser_visualizer.py` -> `IsaacLab/source/isaaclab_visualizers/isaaclab_visualizers/viser/viser_visualizer.py`
  (spotlight follow, static main camera, ~24 Hz render cap)
- `on_policy_runner.py`  -> `IsaacLab/_isaac_sim/kit/python/lib/python3.12/site-packages/rsl_rl/runners/on_policy_runner.py`
  (instant-reset hook + spotlight episode counter)
