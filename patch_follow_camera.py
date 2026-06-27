#!/usr/bin/env python3
"""Patch the Isaac Lab viser visualizer to make the camera FOLLOW the first
visible env's robot, so a small cluster of robots stays in frame and a zoomed
spotlight can lock onto one robot. Idempotent."""
import io, re, sys

P = "/home/sp9/rl-demo/IsaacLab/source/isaaclab_visualizers/isaaclab_visualizers/viser/viser_visualizer.py"
src = open(P).read()

if "_follow_tracked_env" in src:
    print("already patched"); sys.exit(0)

# 1) call the follow helper inside step(), right after num_envs is computed
anchor = "        num_envs = NewtonManager.get_num_envs()\n"
if anchor not in src:
    print("ANCHOR NOT FOUND - aborting"); sys.exit(1)
src = src.replace(anchor, anchor + "\n        self._follow_tracked_env()\n", 1)

# 2) add the method + a step counter init. Insert the method just before _render_markers.
method = '''
    def _follow_tracked_env(self) -> None:
        """Point the camera at the first visible env's robot so it stays centered.

        Makes the visible robot cluster trackable and lets a zoomed spotlight lock
        on. Fixed look-at height avoids vertical bobbing; decimated + smoothed to
        keep it gentle. Fully defensive: any failure leaves the camera untouched.
        """
        try:
            self._follow_count = getattr(self, "_follow_count", 0) + 1
            if (self._follow_count % 3) != 1:   # decimate: update ~every 3rd step
                return
            ids = self._resolved_visible_env_ids
            env_id = ids[0] if ids else 0
            scene = self._scene_data_provider.get_interactive_scene()
            robot = scene["robot"]
            p = robot.data.root_pos_w[env_id].detach().cpu().numpy()
            tx, ty = float(p[0]), float(p[1])
            # smooth the target horizontally
            prev = getattr(self, "_follow_xy", None)
            if prev is not None:
                tx = 0.8 * prev[0] + 0.2 * tx
                ty = 0.8 * prev[1] + 0.2 * ty
            self._follow_xy = (tx, ty)
            target = (tx, ty, 0.55)
            eye = (tx + 2.6, ty - 2.6, 1.9)
            self._set_viser_camera_view((eye, target))
        except Exception:
            pass

'''
src = src.replace("    def _render_markers(self, num_envs: int) -> None:",
                  method + "    def _render_markers(self, num_envs: int) -> None:", 1)

open(P, "w").write(src)
print("patched OK")
