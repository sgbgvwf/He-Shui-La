"""3D 伙伴模型 Widget — OBJ 加载器 + Kivy OpenGL 渲染 + 触控交互."""

import math
import os
import time

from kivy.clock import Clock
from kivy.graphics import Callback, Mesh, RenderContext
from kivy.graphics.opengl import (
    GL_CULL_FACE,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    glClear,
    glDisable,
    glEnable,
)
from kivy.graphics.transformation import Matrix
from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget

# ═══════════════════════════════════════════════════════════════════
# 着色器加载
# ═══════════════════════════════════════════════════════════════════

_SHADER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shaders")


def _load_shader(filename: str) -> str:
    with open(os.path.join(_SHADER_DIR, filename), encoding="utf-8") as f:
        return f.read()


_VS = _load_shader("companion_vertex.glsl")
_FS = _load_shader("companion_fragment.glsl")

# ═══════════════════════════════════════════════════════════════════
# 模型路径
# ═══════════════════════════════════════════════════════════════════

_MODELS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "resources", "models"
)
_DEFAULT_MODEL = os.path.join(_MODELS_DIR, "companion.obj")

# ═══════════════════════════════════════════════════════════════════
# 后备立方体
# ═══════════════════════════════════════════════════════════════════

_FALLBACK_CUBE_VERTS: list[float] = [
    -0.5, -0.5,  0.5,   0.0,  0.0,  1.0,
     0.5, -0.5,  0.5,   0.0,  0.0,  1.0,
     0.5,  0.5,  0.5,   0.0,  0.0,  1.0,
    -0.5,  0.5,  0.5,   0.0,  0.0,  1.0,
     0.5, -0.5, -0.5,   0.0,  0.0, -1.0,
    -0.5, -0.5, -0.5,   0.0,  0.0, -1.0,
    -0.5,  0.5, -0.5,   0.0,  0.0, -1.0,
     0.5,  0.5, -0.5,   0.0,  0.0, -1.0,
    -0.5,  0.5,  0.5,   0.0,  1.0,  0.0,
     0.5,  0.5,  0.5,   0.0,  1.0,  0.0,
     0.5,  0.5, -0.5,   0.0,  1.0,  0.0,
    -0.5,  0.5, -0.5,   0.0,  1.0,  0.0,
    -0.5, -0.5, -0.5,   0.0, -1.0,  0.0,
    -0.5, -0.5,  0.5,   0.0, -1.0,  0.0,
     0.5, -0.5,  0.5,   0.0, -1.0,  0.0,
     0.5, -0.5, -0.5,   0.0, -1.0,  0.0,
    -0.5, -0.5, -0.5,  -1.0,  0.0,  0.0,
    -0.5,  0.5, -0.5,  -1.0,  0.0,  0.0,
    -0.5,  0.5,  0.5,  -1.0,  0.0,  0.0,
    -0.5, -0.5,  0.5,  -1.0,  0.0,  0.0,
     0.5, -0.5,  0.5,   1.0,  0.0,  0.0,
     0.5,  0.5,  0.5,   1.0,  0.0,  0.0,
     0.5,  0.5, -0.5,   1.0,  0.0,  0.0,
     0.5, -0.5, -0.5,   1.0,  0.0,  0.0,
]

_FALLBACK_CUBE_INDICES: list[int] = [
     0,  1,  2,   0,  2,  3,
     4,  5,  6,   4,  6,  7,
     8,  9, 10,   8, 10, 11,
    12, 13, 14,  12, 14, 15,
    16, 17, 18,  16, 18, 19,
    20, 21, 22,  20, 22, 23,
]

# ═══════════════════════════════════════════════════════════════════
# OBJ 加载器
# ═══════════════════════════════════════════════════════════════════


def _resolve_obj_index(token: str, count: int) -> int:
    i = int(token)
    return i - 1 if i > 0 else count + i


def load_obj(path: str) -> tuple[list[float], list[int]]:
    """解析 Wavefront .obj 文件, 返回 (flat_vertices, indices)."""
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    vertex_map: dict[tuple[int, int], int] = {}
    flat_verts: list[float] = []
    idx_list: list[int] = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            token = parts[0]

            if token == "v":
                positions.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif token == "vn":
                normals.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif token == "f":
                face_count = len(parts) - 1
                if face_count < 3:
                    continue
                face_idxs: list[tuple[int, int]] = []
                for vi in range(1, len(parts)):
                    v_str = parts[vi]
                    if "//" in v_str:
                        s = v_str.split("//")
                        v_idx_str, vn_idx_str = s[0], s[1]
                    elif "/" in v_str:
                        s = v_str.split("/")
                        v_idx_str = s[0]
                        vn_idx_str = s[2] if len(s) >= 3 and s[2] else ""
                    else:
                        v_idx_str, vn_idx_str = v_str, ""
                    p_idx = _resolve_obj_index(v_idx_str, len(positions))
                    n_idx = (
                        _resolve_obj_index(vn_idx_str, len(normals))
                        if vn_idx_str else 0
                    )
                    face_idxs.append((p_idx, n_idx))
                for i in range(1, face_count - 1):
                    for vi in (0, i, i + 1):
                        p_idx, n_idx = face_idxs[vi]
                        key = (p_idx, n_idx)
                        if key not in vertex_map:
                            px, py, pz = positions[p_idx]
                            if normals and n_idx < len(normals):
                                nx, ny, nz = normals[n_idx]
                            else:
                                nx, ny, nz = 0.0, 0.0, 1.0
                            flat_verts.extend([px, py, pz, nx, ny, nz])
                            vertex_map[key] = len(flat_verts) // 6 - 1
                        idx_list.append(vertex_map[key])
    return flat_verts, idx_list


# ═══════════════════════════════════════════════════════════════════
# 3D Widget
# ═══════════════════════════════════════════════════════════════════


class Companion3DWidget(Widget):
    """Kivy Widget 用 OpenGL 渲染 3D OBJ 模型."""

    viewmodel = ObjectProperty(None)

    AUTO_ROTATE_SPEED = 0.5
    AUTO_ROTATE_RESUME_DELAY = 1.5
    DRAG_SENSITIVITY = 0.008
    CAMERA_DISTANCE = 3.0

    def __init__(self, model_path: str | None = None, **kwargs):
        super().__init__(**kwargs)

        # ── 状态 ──
        self._auto_angle = 0.0
        self._drag_angle_y = 0.0
        self._drag_angle_x = 0.0
        self._is_dragging = False
        self._release_time = 0.0
        self._last_touch_pos = (0.0, 0.0)
        self._model_scale = 1.0
        self._diffuse_color = (0.25, 0.70, 1.00, 1.0)
        self._ambient_color = (0.10, 0.30, 0.50, 1.0)

        # ── 加载模型 ──
        path = model_path or _DEFAULT_MODEL
        if os.path.exists(path):
            try:
                verts, idxs = load_obj(path)
            except Exception as exc:
                print(f"[Companion3D] 加载失败: {exc}，使用后备立方体")
                verts = list(_FALLBACK_CUBE_VERTS)
                idxs = list(_FALLBACK_CUBE_INDICES)
        else:
            if model_path is not None:
                print(f"[Companion3D] 模型不存在: {path}，使用后备立方体")
            verts = list(_FALLBACK_CUBE_VERTS)
            idxs = list(_FALLBACK_CUBE_INDICES)

        self._vert_count = len(idxs)
        self._proj = Matrix()

        # ── Canvas ──
        # 替换 canvas 为 RenderContext，关闭父级 2D 投影
        self.canvas = RenderContext(
            use_parent_projection=False,
            use_parent_modelview=False,
        )
        self.canvas.shader.vs = _VS
        self.canvas.shader.fs = _FS

        with self.canvas:
            self._pre_cb = Callback(self._pre_draw)
            self._mesh = Mesh(
                vertices=verts,
                indices=idxs,
                fmt=[(b"v_pos", 3, "float"), (b"v_normal", 3, "float")],
                mode="triangles",
            )
            self._post_cb = Callback(self._post_draw)

        # 设置默认投影矩阵和初始 uniform（避免首帧无矩阵导致模型被裁剪）
        self._proj.perspective(45.0, 1.0, 0.1, 100.0)
        self._apply_uniforms(0.0)

        Clock.schedule_interval(self._update_frame, 0)

    # ── GL 状态 ──

    def _pre_draw(self, instr: Callback) -> None:
        """准备 3D 渲染 GL 状态。"""
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)
        glClear(GL_DEPTH_BUFFER_BIT)

    @staticmethod
    def _post_draw(instr: Callback) -> None:
        """恢复 2D 渲染 GL 状态。"""
        glDisable(GL_DEPTH_TEST)

    # ── 投影 ──

    def on_size(self, *args):
        self._update_projection()

    def _update_projection(self) -> None:
        aspect = self.width / max(self.height, 1.0)
        self._proj = Matrix()
        self._proj.perspective(45.0, aspect, 0.1, 100.0)

    # ── 每帧 ──

    def _update_frame(self, dt: float) -> None:
        now = time.time()

        if (
            not self._is_dragging
            and (now - self._release_time) >= self.AUTO_ROTATE_RESUME_DELAY
        ):
            self._auto_angle += self.AUTO_ROTATE_SPEED * dt
            self._auto_angle %= 2.0 * math.pi

        self._apply_uniforms(self._auto_angle + self._drag_angle_y)

    def _apply_uniforms(self, total_y: float) -> None:
        """构建 MVP 矩阵并设置所有着色器 uniform."""

        model = Matrix()
        model = model.scale(self._model_scale, self._model_scale, self._model_scale)
        model = model.rotate(self._drag_angle_x, 1, 0, 0)
        model = model.rotate(total_y, 0, 1, 0)

        view = Matrix().translate(0, 0, -self.CAMERA_DISTANCE)

        mvp = self._proj.multiply(view).multiply(model)
        mv = view.multiply(model)

        self.canvas["u_mvp"] = mvp
        self.canvas["u_modelview"] = mv
        self.canvas["u_light_dir"] = (0.577, 0.577, 0.577)
        self.canvas["u_diffuse_color"] = self._diffuse_color
        self.canvas["u_ambient_color"] = self._ambient_color

    # ── 触控 ──

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._is_dragging = True
            self._last_touch_pos = touch.pos
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            dx = touch.x - self._last_touch_pos[0]
            dy = touch.y - self._last_touch_pos[1]
            self._drag_angle_y += dx * self.DRAG_SENSITIVITY
            self._drag_angle_x += dy * self.DRAG_SENSITIVITY
            self._drag_angle_x = max(
                -math.pi / 2, min(math.pi / 2, self._drag_angle_x)
            )
            self._last_touch_pos = touch.pos
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self._is_dragging = False
            self._release_time = time.time()
            return True
        return super().on_touch_up(touch)

    # ── ViewModel ──

    def on_viewmodel(self, instance, vm):
        if vm is None:
            return
        vm.bind(hydration_norm=self._on_hydration_changed)
        vm.bind(evolution_stage=self._on_evolution_changed)
        self._on_hydration_changed(vm, vm.hydration_norm)
        self._on_evolution_changed(vm, vm.evolution_stage)

    def _on_hydration_changed(self, vm, norm: float) -> None:
        norm = max(0.0, min(1.0, norm))
        if norm < 0.25:
            self._diffuse_color = (0.45, 0.50, 0.55, 1.0)
            self._ambient_color = (0.20, 0.22, 0.25, 1.0)
        elif norm < 0.5:
            t = (norm - 0.25) / 0.25
            self._diffuse_color = (
                0.45 - 0.10 * t, 0.50 + 0.10 * t, 0.55 + 0.35 * t, 1.0)
            self._ambient_color = (
                0.20 - 0.05 * t, 0.22 + 0.03 * t, 0.25 + 0.15 * t, 1.0)
        elif norm < 0.75:
            t = (norm - 0.5) / 0.25
            self._diffuse_color = (
                0.35 - 0.10 * t, 0.60 + 0.10 * t, 0.90 + 0.10 * t, 1.0)
            self._ambient_color = (
                0.15 - 0.05 * t, 0.25 + 0.05 * t, 0.40 + 0.10 * t, 1.0)
        else:
            t = (norm - 0.75) / 0.25
            self._diffuse_color = (
                0.25 + 0.15 * t, 0.70 + 0.15 * t, 1.00, 1.0)
            self._ambient_color = (
                0.10 + 0.10 * t, 0.30 + 0.10 * t, 0.50 + 0.10 * t, 1.0)

    def _on_evolution_changed(self, vm, stage: str) -> None:
        scale_map = {
            "形态A": 1.00, "形态B": 1.08, "形态C": 1.15,
            "形态D": 1.22, "形态E": 1.30,
        }
        self._model_scale = scale_map.get(stage, 1.0)
