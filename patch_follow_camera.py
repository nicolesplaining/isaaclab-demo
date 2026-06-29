#!/usr/bin/env python3
"""Follow logic v5 (main-follows): there is now a single viser view. Make it a
follow-cam on the hero robot (env 0) with the crowd visible around it. One render,
no second client => no lag."""
import re, sys
P = "/home/sp9/rl-demo/IsaacLab/source/isaaclab_visualizers/isaaclab_visualizers/viser/viser_visualizer.py"
src = open(P).read()
if "_follow_tracked_env" not in src:
    print("base patch missing"); sys.exit(1)

new_method = '''    def _follow_tracked_env(self) -> None:
        """Single view follows the hero robot (env 0); crowd stays visible around it."""
        try:
            if self._viewer is None:
                return
            server = getattr(self._viewer, "_server", None)
            get_clients = getattr(server, "get_clients", None) if server is not None else None
            if not callable(get_clients):
                return
            clients = get_clients()
            cl = list(clients.values()) if isinstance(clients, dict) else list(clients)
            if not cl:
                return
            ids = self._resolved_visible_env_ids
            env_id = ids[0] if ids else 0
            scene = self._scene_data_provider.get_interactive_scene()
            robot = scene["robot"]
            p = robot.data.root_pos_w[env_id].detach().cpu().numpy()
            tx, ty = float(p[0]), float(p[1])
            prev = getattr(self, "_follow_xy", None)
            if prev is not None:
                tx = 0.3 * prev[0] + 0.7 * tx
                ty = 0.3 * prev[1] + 0.7 * ty
            self._follow_xy = (tx, ty)
            fov = math.radians(self._focal_length_to_vertical_fov_degrees())
            eye = (tx + 6.0, ty - 6.0, 4.0)
            target = (tx, ty, 0.6)
            for c in cl:
                cam = getattr(c, "camera", None)
                if cam is None:
                    continue
                if hasattr(cam, "fov"):
                    cam.fov = fov
                if hasattr(cam, "position"):
                    cam.position = eye
                if hasattr(cam, "look_at"):
                    cam.look_at = target
        except Exception:
            pass

'''
pat = re.compile(r"    def _follow_tracked_env\(self\) -> None:.*?\n(?=    def )", re.DOTALL)
if not pat.search(src):
    print("locate fail"); sys.exit(1)
src = pat.sub(new_method, src, count=1)
open(P, "w").write(src)
print("follow v5 (main-follows) applied")
