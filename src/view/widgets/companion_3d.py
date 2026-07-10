"""伙伴展示 Widget — 3D OBJ 模型 (面+边混排深度排序)."""

import math
import os
import time

from kivy.clock import Clock
from kivy.graphics import Color, Mesh
from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget

# ═══════════════════════════════════════════════════════════════════

_MODELS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "resources", "models"
)
_DEFAULT_MODEL = os.path.join(_MODELS_DIR, "companion.obj")

_CUBE_VERTS = [
    (-2,-2,-2),( 1,-1,-1),( 1, 1,-1),(-1, 1,-1),
    (-1,-1, 1),( 1,-1, 1),( 1, 1, 1),(-1, 1, 1),
]
_CUBE_EDGES = [
    (0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7),
]
_CUBE_FACES: list[list[int]] = [
    [0,1,2, 0,2,3],[4,6,5, 4,7,6],[0,4,5, 0,5,1],
    [1,5,6, 1,6,2],[2,6,7, 2,7,3],[3,7,4, 3,4,0],
]

def _resolve(idx, cnt):
    i = int(idx); return i-1 if i>0 else cnt+i

def load_obj(path):
    positions, faces, edges = [], [], set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            parts = line.split()
            t = parts[0]
            if t == "v":
                positions.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif t == "f":
                pts = []
                for vi in range(1, len(parts)):
                    vs = parts[vi]; vi_s = vs.split("/")[0] if "/" in vs else vs
                    pts.append(_resolve(vi_s, len(positions)))
                for i in range(1, len(pts)-1):
                    faces.append([pts[0], pts[i], pts[i+1]])
                n = len(pts)
                for i in range(n):
                    a,b = pts[i], pts[(i+1)%n]; edges.add((a,b) if a<b else (b,a))
    return positions, faces, list(edges)


class Companion3DWidget(Widget):
    """面+边深度混排 3D 模型."""

    viewmodel = ObjectProperty(None)
    AUTO_ROTATE_SPEED = 0.6
    AUTO_RESUME_DELAY = 1.0
    DRAG_SENSITIVITY = 0.01
    BOUNCE_AMP = 2.5
    BOUNCE_FREQ = 1.0

    def __init__(self, model_path=None, **kwargs):
        super().__init__(**kwargs)
        self._auto_ay = 0.0; self._auto_ax = -0.6
        self._drag_ay = 0.0; self._drag_ax = 0.0
        self._dragging = False; self._release_t = 0.0
        self._last_t = (0.0, 0.0); self._tacc = 0.0; self._bounce = 0.0
        self._mscale = 1.0
        self._body_rgb = [0.25, 0.65, 1.00]
        self._edge_rgb = [0.10, 0.30, 0.60]

        path = model_path or _DEFAULT_MODEL
        if os.path.exists(path):
            try:
                self._verts, self._faces, self._edges = load_obj(path)
                print(f"[Companion] OBJ: {len(self._verts)}v {len(self._faces)}f {len(self._edges)}e")
            except Exception as e:
                print(f"[Companion] OBJ fail: {e}")
                self._verts=_CUBE_VERTS; self._faces=_CUBE_FACES; self._edges=_CUBE_EDGES
        else:
            print("[Companion] 用后备立方体")
            self._verts=_CUBE_VERTS; self._faces=_CUBE_FACES; self._edges=_CUBE_EDGES

        self.bind(pos=self._on_geo, size=self._on_geo)
        Clock.schedule_interval(self._update, 0)

    # ── 3D→2D ──
    @staticmethod
    def _rotate(v, ay, ax):
        """仅旋转不投影，返回 (x,y,z) 用于法线计算."""
        x, y, z = v
        cy, sy = math.cos(ay), math.sin(ay)
        x, z = x*cy + z*sy, -x*sy + z*cy
        cx, sx = math.cos(ax), math.sin(ax)
        y, z = y*cx - z*sx, y*sx + z*cx
        return x, y, z

    @staticmethod
    def _proj(v, ay, ax):
        x, y, z = Companion3DWidget._rotate(v, ay, ax)
        s = 2.5 / max(z + 8.0, 0.1)
        return x*s, y*s, z

    def _on_geo(self, *a): pass

    # ── 帧 ──
    def _update(self, dt):
        now = time.time(); self._tacc += dt
        if not self._dragging and (now - self._release_t) >= self.AUTO_RESUME_DELAY:
            self._auto_ay += self.AUTO_ROTATE_SPEED * dt
            self._auto_ay %= 2*math.pi
        ay = self._auto_ay + self._drag_ay
        ax = self._auto_ax + self._drag_ax
        self._bounce = (math.sin(self._tacc * self.BOUNCE_FREQ * 2*math.pi)
                        * self.BOUNCE_AMP * self._mscale)

        ox, oy = self.pos; w, h = self.width, self.height
        size = min(w, h); sc = size * 0.5 * self._mscale
        cx = ox + w/2; cy = oy + h/2 + self._bounce
        proj = [self._proj(v, ay, ax) for v in self._verts]

        # ── 所有面，按深度排序 ──
        elements: list[tuple[float, int, float]] = []  # (z, fi, bright)

        # 光源 = 摄像机方向 (0, 0, 1) = 从正前方照来
        Lx, Ly, Lz = 0.0, 0.0, 1.0

        for fi, face in enumerate(self._faces):
            z_avg = sum(proj[v][2] for v in face) / len(face)
            # 法线 (旋转后顶点)
            p0 = self._rotate(self._verts[face[0]], ay, ax)
            p1 = self._rotate(self._verts[face[1]], ay, ax)
            p2 = self._rotate(self._verts[face[2]], ay, ax)
            e1x, e1y, e1z = p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2]
            e2x, e2y, e2z = p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2]
            nx = e1y*e2z - e1z*e2y
            ny = e1z*e2x - e1x*e2z
            nz = e1x*e2y - e1y*e2x
            nlen = math.sqrt(nx*nx + ny*ny + nz*nz)
            ndotl = (nx*Lx + ny*Ly + nz*Lz) / max(nlen, 0.001)
            # 双面光照: 环境0.3 + 漫反射abs(ndotl)*0.7
            bright = 0.30 + abs(ndotl) * 0.70
            elements.append((z_avg, fi, bright))

        elements.sort(key=lambda x: x[0], reverse=True)

        # ── 重建 Canvas ──
        self.canvas.clear()

        with self.canvas:
            for _, fi, bright in elements:
                face = self._faces[fi]
                v0, v1, v2 = proj[face[0]], proj[face[1]], proj[face[2]]
                # 面颜色 = 基础色 × 亮度 (后续可从OBJ材质读取基础色)
                r = self._body_rgb[0] * bright
                g = self._body_rgb[1] * bright
                b = self._body_rgb[2] * bright
                Color(r, g, b)
                Mesh(
                    vertices=[
                        v0[0]*sc+cx, v0[1]*sc+cy, 0, 0,
                        v1[0]*sc+cx, v1[1]*sc+cy, 0, 0,
                        v2[0]*sc+cx, v2[1]*sc+cy, 0, 0,
                    ],
                    indices=[0,1,2], mode="triangles",
                )

    # ── 触控 ──
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self); self._dragging = True
            self._last_t = touch.pos; return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            dx = touch.x - self._last_t[0]; dy = touch.y - self._last_t[1]
            self._drag_ay -= dx * self.DRAG_SENSITIVITY
            self._drag_ax += dy * self.DRAG_SENSITIVITY * 0.5
            self._last_t = touch.pos; return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self); self._dragging = False
            self._release_t = time.time(); return True
        return super().on_touch_up(touch)

    # ── ViewModel ──
    def on_viewmodel(self, instance, vm):
        if vm is None: return
        vm.bind(hydration_norm=self._on_hydration)
        vm.bind(evolution_stage=self._on_evolution)
        self._on_hydration(vm, vm.hydration_norm)
        self._on_evolution(vm, vm.evolution_stage)

    def _on_hydration(self, vm, norm):
        norm = max(0, min(1, norm))
        r,g,b = 0.45-0.25*norm, 0.50+0.35*norm, 0.55+0.45*norm
        self._body_rgb = [r,g,b]; self._edge_rgb = [r*0.4, g*0.4, b*0.5]

    def _on_evolution(self, vm, stage):
        self._mscale = {"形态A":1,"形态B":1.08,"形态C":1.15,"形态D":1.22,"形态E":1.3}.get(stage,1)
