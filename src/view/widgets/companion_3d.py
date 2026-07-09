"""伙伴展示 Widget — 立方体旋转 + 水分/进化联动."""

import math
import time

from kivy.clock import Clock
from kivy.graphics import Color, Line, PopMatrix, PushMatrix, Rotate, Scale, Translate
from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget


class Companion3DWidget(Widget):
    """旋转立方体 + 弹跳 + 水分联动."""

    viewmodel = ObjectProperty(None)

    AUTO_ROTATE_SPEED = 0.8
    AUTO_RESUME_DELAY = 1.5
    DRAG_SENSITIVITY = 0.008
    BOUNCE_AMPLITUDE = 8.0
    BOUNCE_FREQ = 2.0

    # 立方体 8 个顶点 3D 坐标 (边长为1, 中心在原点)
    CUBE_VERTS = [
        (-0.5, -0.5, -0.5), ( 0.5, -0.5, -0.5),
        ( 0.5,  0.5, -0.5), (-0.5,  0.5, -0.5),  # 后面
        (-0.5, -0.5,  0.5), ( 0.5, -0.5,  0.5),
        ( 0.5,  0.5,  0.5), (-0.5,  0.5,  0.5),  # 前面
    ]
    # 12 条边 (每边两个顶点索引)
    CUBE_EDGES = [
        (0,1),(1,2),(2,3),(3,0),  # 后面
        (4,5),(5,6),(6,7),(7,4),  # 前面
        (0,4),(1,5),(2,6),(3,7),  # 连线
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ── 动画状态 ──
        self._auto_angle_y = 0.0
        self._auto_angle_x = 0.3        # 微微倾斜
        self._drag_angle_y = 0.0
        self._drag_angle_x = 0.0
        self._is_dragging = False
        self._release_time = 0.0
        self._last_touch_pos = (0.0, 0.0)
        self._time_acc = 0.0
        self._bounce_offset = 0.0

        # ── 外观 ──
        self._model_scale = 1.0
        self._edge_rgb = [0.25, 0.65, 1.00]   # 蓝色线框

        # ── Canvas 一次性构建 ──
        with self.canvas.before:
            PushMatrix()
            self._tr_center = Translate(0, 0)
            self._sc = Scale(1.0)
            self._tr_bounce = Translate(0, 0)

        with self.canvas:
            self._c_edge = Color(*self._edge_rgb)
            self._lines: list[Line] = []
            for _ in self.CUBE_EDGES:
                self._lines.append(Line(points=[0,0,0,0], width=2.0))

        with self.canvas.after:
            PopMatrix()

        self.bind(size=self._on_size)
        Clock.schedule_interval(self._update, 0)

    # ── 简单透视投影 ──
    def _project(self, v3: tuple[float, float, float],
                 angle_y: float, angle_x: float) -> tuple[float, float]:
        """3D 顶点绕原点旋转后透视投影到 2D."""
        x, y, z = v3

        # 绕 Y 轴旋转
        cos_y, sin_y = math.cos(angle_y), math.sin(angle_y)
        x, z = x * cos_y + z * sin_y, -x * sin_y + z * cos_y

        # 绕 X 轴旋转
        cos_x, sin_x = math.cos(angle_x), math.sin(angle_x)
        y, z = y * cos_x - z * sin_x, y * sin_x + z * cos_x

        # 透视投影
        dist = 3.0
        z_clip = z + dist
        if z_clip < 0.1:
            z_clip = 0.1
        scale_p = 1.5 / z_clip   # 投影缩放
        return x * scale_p, y * scale_p

    # ── 尺寸更新 ──
    def _on_size(self, *args):
        w, h = self.width, self.height
        self._tr_center.xy = (w / 2.0, h / 2.0)

    # ── 帧更新 ──
    def _update(self, dt: float) -> None:
        now = time.time()
        self._time_acc += dt

        # 自动旋转
        if (
            not self._is_dragging
            and (now - self._release_time) >= self.AUTO_RESUME_DELAY
        ):
            self._auto_angle_y += self.AUTO_ROTATE_SPEED * dt
            self._auto_angle_y %= 2.0 * math.pi

        total_y = self._auto_angle_y + self._drag_angle_y
        total_x = self._auto_angle_x + self._drag_angle_x

        # 弹跳
        self._bounce_offset = (
            math.sin(self._time_acc * self.BOUNCE_FREQ * 2 * math.pi)
            * self.BOUNCE_AMPLITUDE
            * self._model_scale
        )

        # 变换
        size = min(self.width, self.height)
        cube_scale = size * 0.22 * self._model_scale
        self._sc.xyz = (cube_scale, cube_scale, cube_scale)
        self._tr_bounce.y = self._bounce_offset

        # 颜色
        self._c_edge.rgb = self._edge_rgb

        # 投影所有顶点
        proj = [
            self._project(v, total_y, total_x + 0.3)
            for v in self.CUBE_VERTS
        ]

        # 更新线段
        for i, (a, b) in enumerate(self.CUBE_EDGES):
            self._lines[i].points = [
                proj[a][0], proj[a][1],
                proj[b][0], proj[b][1],
            ]
            self._lines[i].width = max(1.0, cube_scale * 0.04)

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
        scale_map = {
            "形态A": 1.00, "形态B": 1.08,
            "形态C": 1.15, "形态D": 1.22, "形态E": 1.30,
        }
        self._model_scale = scale_map.get(stage, 1.0)
