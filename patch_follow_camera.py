#!/usr/bin/env python3
"""Follow logic v4 (DETERMINISTIC): identify the spotlight vs main view by CANVAS
SIZE, not connection order. The spotlight PiP iframe is physically smaller, so the
client with the smallest canvas area is always the spotlight; the largest is the
main. Spotlight follows the tracked robot; main is framed once (static crowd)."""
import re, sys
P = "/home/sp9/rl-demo/IsaacLab/source/isaaclab_visualizers/isaaclab_visualizers/viser/viser_visualizer.py"
src = open(P).read()
if "_follow_tracked_env" not in src:
    print("base patch missing"); sys.exit(1)

new_method = '''    def _follow_tracked_env(self) -> None:
        """Spotlight (smallest canvas) follows the robot; main (largest) stays static."""
        try:
            if self._viewer is None:
                return
            server = getattr(self._viewer, "_server", None)
            get_clients = getattr(server, "get_clients", None) if server is not None else None
            if not callable(get_clients):
                return
            clients = get_clients()
            cl = list(clients.values()) if isinstance(clients, dict) else list(clients)
            sized = []
            for c in cl:
                cam = getattr(c, "camera", None)
                if cam is None:
                    continue
                w = getattr(cam, "image_width", 0) or 0
                h = getattr(cam, "image_height", 0) or 0
                if w > 0 and h > 0:
                    sized.append((w * h, c))
            if len(sized) < 2:
                return  # need both the large main and the small spotlight reporting sizes
            sized.sort(key=lambda t: t[0])
            spot = sized[0][1]      # smallest canvas  -> spotlight PiP (deterministic)
            main = sized[-1][1]     # largest canvas   -> main crowd view
            ids = self._resolved_visible_env_ids
            env_id = ids[0] if ids else 0
            scene = self._scene_data_provider.get_interactive_scene()
            robot = scene["robot"]
            allpos = robot.data.root_pos_w
            fov = math.radians(self._focal_length_to_vertical_fov_degrees())

            # one-time: frame the MAIN view (static) on the visible-robot cluster
            if not getattr(self, "_main_framed", False):
                vis = ids if ids else [env_id]
                cen = allpos[vis].detach().cpu().numpy()
                cx, cy = float(cen[:, 0].mean()), float(cen[:, 1].mean())
                cam = getattr(main, "camera", None)
                if cam is not None:
                    if hasattr(cam, "fov"):
                        cam.fov = fov
                    if hasattr(cam, "position"):
                        cam.position = (cx + 9.0, cy - 9.0, 6.5)
                    if hasattr(cam, "look_at"):
                        cam.look_at = (cx, cy, 0.6)
                self._main_framed = True

            # per-step: spotlight follows the tracked robot (smoothed), full body in frame
            p = allpos[env_id].detach().cpu().numpy()
            tx, ty = float(p[0]), float(p[1])
            prev = getattr(self, "_follow_xy", None)
            if prev is not None:
                tx = 0.85 * prev[0] + 0.15 * tx
                ty = 0.85 * prev[1] + 0.15 * ty
            self._follow_xy = (tx, ty)
            cam = getattr(spot, "camera", None)
            if cam is not None:
                if hasattr(cam, "fov"):
                    cam.fov = fov
                if hasattr(cam, "position"):
                    cam.position = (tx + 2.9, ty - 2.9, 1.8)
                if hasattr(cam, "look_at"):
                    cam.look_at = (tx, ty, 0.7)
        except Exception:
            pass

'''
pat = re.compile(r"    def _follow_tracked_env\(self\) -> None:.*?\n(?=    def )", re.DOTALL)
if not pat.search(src):
    print("locate fail"); sys.exit(1)
src = pat.sub(new_method, src, count=1)
open(P, "w").write(src)
print("follow v4 (canvas-size deterministic) applied")
