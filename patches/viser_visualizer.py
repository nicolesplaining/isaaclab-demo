# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Viser-based visualizer using Newton's ViewerViser."""

from __future__ import annotations

import contextlib
import io
import logging
import math
import os
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING, Any

import newton
import numpy as np
from newton.viewer import ViewerViser

from isaaclab.visualizers.base_visualizer import BaseVisualizer

from isaaclab_visualizers.newton.newton_visualization_markers import render_newton_visualization_markers
from isaaclab_visualizers.newton_adapter import (
    apply_viewer_visible_worlds,
    log_geo_with_expanded_plane_scale,
    resolve_visible_env_indices,
)

from .viser_visualizer_cfg import ViserVisualizerCfg

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from isaaclab.scene_data import SceneDataProvider


def _disable_viser_runtime_client_rebuild_if_bundled() -> None:
    """Skip viser's runtime frontend rebuild when a bundled build is present."""
    try:
        import viser
        import viser._client_autobuild as client_autobuild
    except Exception:
        return

    client_root = Path(viser.__file__).resolve().parent / "client"
    has_bundled_build = (client_root / "build" / "index.html").exists()
    if not has_bundled_build:
        return

    client_autobuild.ensure_client_is_built = lambda: None


def _open_viser_web_viewer(url: str) -> None:
    """Open the Viser web UI in a browser."""
    try:
        if not webbrowser.open_new_tab(url):
            logger.info("[ViserVisualizer] Could not auto-open browser tab. Open manually: %s", url)
    except Exception:
        logger.info("[ViserVisualizer] Could not auto-open browser tab. Open manually: %s", url)


def _viser_web_viewer_url(port: int, display_address: str) -> str:
    """Return Viser web UI URL for display to users."""
    return f"http://{display_address}:{int(port)}"


class NewtonViewerViser(ViewerViser):
    """Isaac Lab wrapper for Newton's ViewerViser."""

    def __init__(
        self,
        port: int = 8080,
        bind_address: str = "0.0.0.0",
        label: str | None = None,
        verbose: bool = True,
        share: bool = False,
        record_to_viser: str | None = None,
        metadata: dict | None = None,
    ):
        """Initialize Newton-backed viser viewer wrapper.

        Args:
            port: HTTP port for viser server.
            bind_address: Host/interface for the Viser server to bind.
            label: Optional viewer label.
            verbose: Whether to keep verbose startup output enabled.
            share: Whether to enable sharing/tunneling.
            record_to_viser: Optional recording destination.
            metadata: Optional metadata attached to the viewer.
        """
        _disable_viser_runtime_client_rebuild_if_bundled()
        viser = self._get_viser()
        original_viser_server = viser.ViserServer

        def _viser_server_with_bind_address(*args, **kwargs):
            kwargs["host"] = bind_address
            kwargs["verbose"] = verbose
            return original_viser_server(*args, **kwargs)

        with contextlib.ExitStack() as stack:
            viser.ViserServer = _viser_server_with_bind_address
            stack.callback(setattr, viser, "ViserServer", original_viser_server)
            if not verbose:
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            super().__init__(
                port=port,
                label=label,
                verbose=verbose,
                share=share,
                record_to_viser=record_to_viser,
            )
        self._metadata = metadata or {}
        self._isaaclab_plane_grid_cache: dict[str, tuple] = {}

    @property
    def share_url(self) -> str | None:
        """Return the public share URL created by Viser, if any."""
        return self._share_url

    def clear_model(self) -> None:
        """Clear cached static plane-grid signatures with the viewer model."""
        cache = getattr(self, "_isaaclab_plane_grid_cache", None)
        if cache is not None:
            cache.clear()
        return super().clear_model()

    @staticmethod
    def _array_signature(array) -> tuple[tuple[int, ...], bytes] | None:
        """Return a stable signature for small transform/scale arrays."""
        if array is None:
            return None
        array_np = np.ascontiguousarray(np.asarray(array, dtype=np.float32))
        return tuple(int(dim) for dim in array_np.shape), array_np.tobytes()

    def _log_plane_instances(
        self,
        name: str,
        plane_info: dict[str, float | bool],
        xforms,
        scales,
        hidden: bool = False,
    ) -> None:
        """Avoid removing/re-adding unchanged Viser plane grids every frame."""
        cache = getattr(self, "_isaaclab_plane_grid_cache", None)
        if hidden or xforms is None:
            if cache is not None:
                cache.pop(name, None)
            return super()._log_plane_instances(name, plane_info, xforms, scales, hidden=hidden)

        xforms_np = self._to_numpy(xforms)
        if xforms_np is None or len(xforms_np) == 0:
            if cache is not None:
                cache.pop(name, None)
            return super()._log_plane_instances(name, plane_info, xforms, scales, hidden=hidden)

        scales_np = self._to_numpy(scales) if scales is not None else None
        signature = (
            float(plane_info["width"]),
            float(plane_info["length"]),
            self._array_signature(xforms_np),
            self._array_signature(scales_np),
        )
        if cache is not None and cache.get(name) == signature and name in self._plane_handles:
            return None
        if cache is not None:
            cache[name] = signature
        return super()._log_plane_instances(name, plane_info, xforms, scales, hidden=hidden)

    def log_geo(
        self,
        name: str,
        geo_type: int,
        geo_scale: tuple[float, ...],
        geo_thickness: float,
        geo_is_solid: bool,
        geo_src=None,
        hidden: bool = False,
    ):
        """Log geometry, preserving large render extents for infinite ground planes."""
        return log_geo_with_expanded_plane_scale(
            super().log_geo,
            newton.GeoType.PLANE,
            name,
            geo_type,
            geo_scale,
            geo_thickness,
            geo_is_solid,
            geo_src,
            hidden,
        )


class ViserVisualizer(BaseVisualizer):
    """Viser web-based visualizer backed by Newton's ViewerViser."""

    def __init__(self, cfg: ViserVisualizerCfg):
        """Initialize Viser visualizer state.

        Args:
            cfg: Viser visualizer configuration.
        """
        super().__init__(cfg)
        self.cfg: ViserVisualizerCfg = cfg
        self._viewer: NewtonViewerViser | None = None
        self._model: Any | None = None
        self._state = None
        self._sim_time = 0.0
        self._active_record_path: str | None = None
        self._last_camera_pose: tuple[tuple[float, float, float], tuple[float, float, float]] | None = None
        self._pending_camera_pose: tuple[tuple[float, float, float], tuple[float, float, float]] | None = None
        self._resolved_visible_env_ids: list[int] | None = None
        self._warned_marker_render_failure = False

    def initialize(self, scene_data_provider: SceneDataProvider) -> None:
        """Initialize viewer resources and bind scene data provider.

        Args:
            scene_data_provider: Scene data provider used to fetch model/state data.
        """
        from isaaclab_newton.physics import NewtonManager

        if self._is_initialized:
            logger.debug("[ViserVisualizer] initialize() called while already initialized.")
            return

        scene_data_provider = self._set_scene_data_provider(scene_data_provider)
        num_envs = scene_data_provider.num_envs
        metadata = {"num_envs": num_envs}
        self._env_ids = self._compute_visualized_env_ids()
        self._model = NewtonManager.get_model()
        self._state = NewtonManager.get_state(self._scene_data_provider)

        self._active_record_path = self.cfg.record_to_viser
        self._create_viewer(record_to_viser=self.cfg.record_to_viser, metadata=metadata)
        self._resolved_visible_env_ids = resolve_visible_env_indices(self._env_ids, self.cfg.max_visible_envs, num_envs)
        num_visualized_envs = (
            len(self._resolved_visible_env_ids) if self._resolved_visible_env_ids is not None else num_envs
        )
        self._log_initialization_table(
            logger=logger,
            title="ViserVisualizer Configuration",
            rows=[
                ("eye", self.cfg.eye),
                ("lookat", self.cfg.lookat),
                ("focal_length", self.cfg.focal_length),
                ("num_visualized_envs", num_visualized_envs),
                ("bind_address", self.cfg.bind_address),
                ("display_address", self.cfg.display_address),
                ("port", self.cfg.port),
                ("record_to_viser", self.cfg.record_to_viser or "<none>"),
            ],
        )
        self._is_initialized = True

    def step(self, dt: float) -> None:
        """Advance visualization by one simulation step.

        Args:
            dt: Simulation time-step in seconds.
        """
        from isaaclab_newton.physics import NewtonManager

        if not self._is_initialized or self._viewer is None or self._scene_data_provider is None:
            return

        self._apply_pending_camera_pose()

        self._state = NewtonManager.get_state(self._scene_data_provider)
        num_envs = NewtonManager.get_num_envs()

        self._sim_time += dt
        # cap visual updates to ~24 Hz (WALL-CLOCK so it still renders while physics is
        # paused during a reset hold). cuts streaming/render load with many robots.
        import time as _wt
        _now = _wt.time()
        if (_now - getattr(self, "_last_render_wt", -1e9)) < (1.0 / 24.0):
            return
        self._last_render_wt = _now

        self._follow_tracked_env()
        self._viewer.begin_frame(self._sim_time)
        try:
            self._viewer.log_state(self._state)
            # per-robot velocity markers disabled to reduce geometry at high env counts
        finally:
            self._viewer.end_frame()


    def _follow_tracked_env(self) -> None:
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
                if hasattr(cam, "fov") and not getattr(self, "_spot_fov_set", False):
                    cam.fov = fov
                    self._spot_fov_set = True
                if hasattr(cam, "position"):
                    cam.position = (tx + 2.9, ty - 2.9, 1.8)
                if hasattr(cam, "look_at"):
                    cam.look_at = (tx, ty, 0.7)
        except Exception:
            pass

    def _render_markers(self, num_envs: int) -> None:
        """Render marker overlays without letting them interrupt Viser body updates."""
        try:
            render_newton_visualization_markers(self._viewer, self._resolved_visible_env_ids, num_envs=num_envs)
        except Exception as exc:
            if not self._warned_marker_render_failure:
                logger.warning("[ViserVisualizer] Marker rendering failed; continuing body updates: %s", exc)
                self._warned_marker_render_failure = True
            else:
                logger.debug("[ViserVisualizer] Marker rendering failed: %s", exc)

    def close(self) -> None:
        """Close viewer resources and finalize optional recording."""
        if not self._is_initialized:
            return
        try:
            self._close_viewer(finalize_viser=bool(self.cfg.record_to_viser))
        except Exception as exc:
            logger.warning("[ViserVisualizer] Error during close: %s", exc)

        self._viewer = None
        self._is_initialized = False
        self._is_closed = True
        self._active_record_path = None
        self._pending_camera_pose = None

    def is_running(self) -> bool:
        """Return whether the visualizer should continue stepping.

        Returns:
            ``True`` while the visualizer is active, otherwise ``False``.
        """
        if not self._is_initialized or self._is_closed:
            return False
        if self._viewer is None:
            return False
        return self._viewer.is_running()

    def is_training_paused(self) -> bool:
        """Return whether training is paused.

        Viser backend does not currently expose a training pause control.
        """
        return False

    def supports_markers(self) -> bool:
        """Viser backend supports Isaac Lab markers through Newton viewer primitives."""
        return bool(self.cfg.enable_markers)

    def supports_live_plots(self) -> bool:
        """Viser backend currently does not expose Isaac Lab live-plot widgets."""
        return False

    def _create_viewer(self, record_to_viser: str | None, metadata: dict | None = None) -> None:
        """Create Newton-backed Viser viewer and apply initial camera.

        Args:
            record_to_viser: Optional output path for viser recording.
            metadata: Optional metadata passed to viewer.
        """
        if self._model is None:
            raise RuntimeError("Viser visualizer requires a Newton model.")

        self._viewer = NewtonViewerViser(
            port=self.cfg.port,
            bind_address=self.cfg.bind_address,
            label=self.cfg.label,
            verbose=False,
            share=self.cfg.share,
            record_to_viser=record_to_viser,
            metadata=metadata or {},
        )
        viewer_url = self._viewer.share_url or _viser_web_viewer_url(self.cfg.port, self.cfg.display_address)
        if self.cfg.verbose:
            print()
            self._log_viewer_url(
                "ViserVisualizer",
                viewer_url,
            )
        num_envs = int((metadata or {}).get("num_envs", 0))
        self._viewer.set_model(self._model)
        apply_viewer_visible_worlds(
            self._viewer,
            env_ids=self._env_ids,
            max_visible_envs=self.cfg.max_visible_envs,
            num_envs=num_envs,
        )
        # Preserve simulation world positions (env_spacing) rather than adding viewer-side offsets.
        self._viewer.set_world_offsets((0.0, 0.0, 0.0))
        if self.cfg.open_browser:
            _open_viser_web_viewer(viewer_url)
        initial_pose = self._resolve_initial_camera_pose()
        self._set_viser_camera_view(initial_pose)
        self._sim_time = 0.0

    def _close_viewer(self, finalize_viser: bool = False) -> None:
        """Close viewer and log recording output when requested."""
        if self._viewer is None:
            return
        self._viewer.close()
        if finalize_viser and self._active_record_path:
            if os.path.exists(self._active_record_path):
                size = os.path.getsize(self._active_record_path)
                logger.info("[ViserVisualizer] Recording saved: %s (%s bytes)", self._active_record_path, size)
            else:
                logger.warning("[ViserVisualizer] Recording file not found: %s", self._active_record_path)
        self._viewer = None

    def _resolve_initial_camera_pose(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """Resolve initial camera pose from config."""
        return self._resolve_cfg_camera_pose("ViserVisualizer")

    def _try_apply_viser_camera_view(self, pose: tuple[tuple[float, float, float], tuple[float, float, float]]) -> bool:
        """Try applying camera pose to active viser clients.

        Returns:
            ``True`` if at least one client camera was updated, otherwise ``False``.
        """
        if self._viewer is None:
            return False
        server = getattr(self._viewer, "_server", None)
        get_clients = getattr(server, "get_clients", None) if server is not None else None
        if not callable(get_clients):
            return False

        try:
            clients = get_clients()
        except Exception:
            return False

        client_iterable = clients.values() if isinstance(clients, dict) else clients
        cam_pos, cam_target = pose
        fov_radians = math.radians(self._focal_length_to_vertical_fov_degrees())
        applied = False
        for client in client_iterable:
            camera = getattr(client, "camera", None)
            if camera is None:
                continue
            try:
                if hasattr(camera, "fov"):
                    camera.fov = fov_radians
                    applied = True
                if hasattr(camera, "position"):
                    camera.position = cam_pos
                    applied = True
                if hasattr(camera, "look_at"):
                    camera.look_at = cam_target
                    applied = True
            except Exception:
                continue
        return applied

    def _set_viser_camera_view(self, pose: tuple[tuple[float, float, float], tuple[float, float, float]]) -> None:
        """Apply or defer camera pose update depending on client readiness."""
        if self._try_apply_viser_camera_view(pose):
            self._last_camera_pose = pose
            self._pending_camera_pose = None
        else:
            self._pending_camera_pose = pose

    def _apply_pending_camera_pose(self) -> None:
        """Apply deferred camera pose once client cameras are available."""
        if self._pending_camera_pose is None:
            return
        if self._try_apply_viser_camera_view(self._pending_camera_pose):
            self._last_camera_pose = self._pending_camera_pose
            self._pending_camera_pose = None
