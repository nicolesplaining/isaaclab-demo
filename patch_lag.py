#!/usr/bin/env python3
"""Reduce viz streaming/CPU contention with training WITHOUT changing the scene,
cameras, layout, robot count or fidelity:
  1) cap the state stream at ~24 Hz instead of 30 Hz (less serialization +
     websocket traffic on the shared Spark; 24 fps is still cinematically smooth).
  2) write the spotlight camera fov only once instead of every frame (it never
     changes) -> fewer per-frame camera messages.
Idempotent."""
import sys
V = "/home/sp9/rl-demo/IsaacLab/source/isaaclab_visualizers/isaaclab_visualizers/viser/viser_visualizer.py"
s = open(V).read()
changed = False

# 1) 30 Hz -> 24 Hz cap (+ comment)
if "(1.0 / 30.0)" in s:
    s = s.replace("cap visual updates to ~30 Hz", "cap visual updates to ~24 Hz")
    s = s.replace("(1.0 / 30.0)", "(1.0 / 24.0)")
    changed = True

# 2) spotlight fov: set once, not every render frame
old = (
    "            cam = getattr(spot, \"camera\", None)\n"
    "            if cam is not None:\n"
    "                if hasattr(cam, \"fov\"):\n"
    "                    cam.fov = fov\n"
    "                if hasattr(cam, \"position\"):\n"
    "                    cam.position = (tx + 2.9, ty - 2.9, 1.8)\n"
)
new = (
    "            cam = getattr(spot, \"camera\", None)\n"
    "            if cam is not None:\n"
    "                if hasattr(cam, \"fov\") and not getattr(self, \"_spot_fov_set\", False):\n"
    "                    cam.fov = fov\n"
    "                    self._spot_fov_set = True\n"
    "                if hasattr(cam, \"position\"):\n"
    "                    cam.position = (tx + 2.9, ty - 2.9, 1.8)\n"
)
if old in s:
    s = s.replace(old, new, 1)
    changed = True

if not changed:
    print("nothing to change (already patched or anchors moved)"); sys.exit(0)
import ast; ast.parse(s)
open(V, "w").write(s)
print("lag patch applied; AST OK")
