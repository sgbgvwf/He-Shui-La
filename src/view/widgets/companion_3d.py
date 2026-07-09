"""伙伴展示 Widget — 线框立方体旋转 (父级坐标系统)."""

import math
import time

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget


class Companion3DWidget(Widget):
    """旋转线框立方体 + 弹跳 + 水分联动."""

    viewmodel = ObjectProperty(None)

    AUTO_ROTATE_SPEED = 0.8
    AUTO_RESUME_DELAY = 1.5
    DRAG_SENSITIVITY = 0.008
    BOUNCE_AMPLITUDE = 5.0
    BOUNCE_FREQ = 2.0

    CUBE_VERTS = [
        (-2, -2, -2), ( 2, -2, -2),
        ( 2,  2, -2), (-2,  2, -2),
        (-2, -2,  2), ( 2, -2,  2),
        ( 2,  2,  2), (-2,  2,  2),
    ]
    CUBE_EDGES = [
        (0,1),(1,2),(2,3),(3,0),
        (4,5),(5,6),(6,7),(7,4),
        (0,4),(1,5),(2,6),(3,7),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._auto_angle_y = 0.0
        self._auto_angle_x = 0.35
        self._drag_angle_y = 0.0
        self._drag_angle_x = 0.0
        self._is_dragging = False
        self._release_time = 0.0
        self._last_touch_pos = (0.0, 0.0)
        self._time_acc = 0.0
        self._bounce = 0.0
        self._model_scale = 1.0
        self._edge_rgb = [0.25, 0.65, 1.00]

        # 坐标原点 = 父级空间中的 self.pos (KV 橙色矩形也是用的 self.pos)
        ox, oy = self.pos
        w, h = self.size

        with self.canvas:
            # 背景
            Color(0.85, 0.92, 1.0, 0.5)
            self._bg = Rectangle(pos=(ox, oy), size=(w, h))

            # 绿边框
            Color(0.0, 0.9, 0.2, 0.7)
            self._border = Line(rectangle=(ox, oy, w, h), width=1.5)

            # 红点 (中心)
            Color(1.0, 0.0, 0.0, 0.9)
            cx = ox + w / 2
            cy = oy + h / 2
            self._dot = Ellipse(pos=(cx - 5, cy - 5), size=(10, 10))

            # 立方体线框
            self._c_edge = Color(*self._edge_rgb)
            self._lines: list[Line] = []
            for _ in self.CUBE_EDGES:
                self._lines.append(Line(points=[0, 0, 0, 0], width=2.0))

        self.bind(pos=self._on_geometry, size=self._on_geometry)
        Clock.schedule_interval(self._update, 0)

    # ── 3D→2D 投影 ──
    @staticmethod
    def _project(v, ay, ax):
        x, y, z = v
        cy, sy = math.cos(ay), math.sin(ay)
        x, z = x * cy + z * sy, -x * sy + z * cy
        cx, sx = math.cos(ax), math.sin(ax)
        y, z = y * cx - z * sx, y * sx + z * cx
        s = 1.5 / max(z + 3.0, 0.1)
        return x * s, y * s

    # ── 几何变更 ──
    def _on_geometry(self, *args):
        ox, oy = self.pos
        w, h = self.size
        self._bg.pos = (ox, oy)
        self._bg.size = (w, h)
        self._border.rectangle = (ox, oy, w, h)
        cx, cy = ox + w / 2, oy + h / 2
        self._dot.pos = (cx - 5, cy - 5)

    # ── 帧 ──
    def _update(self, dt: float) -> None:
        now = time.time()
        self._time_acc += dt

        if (not self._is_dragging and
                (now - self._release_time) >= self.AUTO_RESUME_DELAY):
            self._auto_angle_y += self.AUTO_ROTATE_SPEED * dt
            self._auto_angle_y %= 2.0 * math.pi

        ay = self._auto_angle_y + self._drag_angle_y
        ax = self._auto_angle_x + self._drag_angle_x

        self._bounce = (math.sin(self._time_acc * self.BOUNCE_FREQ * 2 * math.pi)
                        * self.BOUNCE_AMPLITUDE * self._model_scale)

        ox, oy = self.pos
        w, h = self.width, self.height
        size = min(w, h)
        s = size * 0.15 * self._model_scale
        cx = ox + w / 2.0
        cy = oy + h / 2.0 + self._bounce

        proj = [self._project(v, ay, ax) for v in self.CUBE_VERTS]
        self._c_edge.rgb = self._edge_rgb
        for i, (a, b) in enumerate(self.CUBE_EDGES):
            self._lines[i].points = [
                proj[a][0] * s + cx, proj[a][1] * s + cy,
                proj[b][0] * s + cx, proj[b][1] * s + cy,
            ]
            self._lines[i].width = max(1.0, s * 0.04)

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
            self._drag_angle_x += dy * self.DRAG_SENSITIVITY * 0.5
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
        self._edge_rgb = [
            0.45 - 0.25 * norm,
            0.50 + 0.35 * norm,
            0.55 + 0.45 * norm,
        ]

    def _on_evolution_changed(self, vm, stage: str) -> None:
        self._model_scale = {
            "形态A": 1.00, "形态B": 1.08,
            "形态C": 1.15, "形态D": 1.22, "形态E": 1.30,
        }.get(stage, 1.0)
