"""伙伴展示 Widget — 软件光栅化 z-buffer 3D 渲染."""

import math
import os
import time

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.graphics.texture import Texture
from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget

# ═══════════════════════════════════════════════════════════════════

_MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "models")
_DEFAULT_MODEL = os.path.join(_MODELS_DIR, "companion.obj")

_CUBE_VERTS = [
    (-0.5,-0.5,-0.5),(0.5,-0.5,-0.5),(0.5,0.5,-0.5),(-0.5,0.5,-0.5),
    (-0.5,-0.5,0.5),(0.5,-0.5,0.5),(0.5,0.5,0.5),(-0.5,0.5,0.5),
]
_CUBE_FACES: list[list[int]] = [
    [0,1,2],[0,2,3],[4,6,5],[4,7,6],[0,4,5],[0,5,1],
    [1,5,6],[1,6,2],[2,6,7],[2,7,3],[3,7,4],[3,4,0],
]

def _resolve(idx, cnt):
    i = int(idx); return i-1 if i>0 else cnt+i

def load_obj(path):
    positions, faces = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            parts = line.split(); t = parts[0]
            if t == "v":
                positions.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif t == "f":
                pts = []
                for vi in range(1, len(parts)):
                    vs = parts[vi]; vi_s = vs.split("/")[0] if "/" in vs else vs
                    pts.append(_resolve(vi_s, len(positions)))
                for i in range(1, len(pts)-1):
                    faces.append([pts[0], pts[i], pts[i+1]])
    return positions, faces


class Companion3DWidget(Widget):
    """软件 z-buffer 3D 渲染."""

    viewmodel = ObjectProperty(None)
    AUTO_ROTATE_SPEED = 0.6
    AUTO_RESUME_DELAY = 1.0
    DRAG_SENSITIVITY = 0.01

    def __init__(self, model_path=None, **kwargs):
        super().__init__(**kwargs)
        self._auto_ay = 0.0; self._auto_ax = -0.6
        self._drag_ay = 0.0; self._drag_ax = 0.0
        self._dragging = False; self._release_t = 0.0
        self._last_t = (0.0, 0.0); self._tacc = 0.0
        self._mscale = 1.0
        self._diffuse = [0.25, 0.65, 1.00]
        self._ambient = [0.08, 0.20, 0.35]

        path = model_path or _DEFAULT_MODEL
        if os.path.exists(path):
            try:
                self._verts, self._faces = load_obj(path)
            except Exception:
                self._verts=_CUBE_VERTS; self._faces=_CUBE_FACES
        else:
            self._verts=_CUBE_VERTS; self._faces=_CUBE_FACES

        # 贴图用于显示光栅化结果
        self._tex = Texture.create(size=(2, 2), colorfmt='rgba')
        self._tex.mag_filter = 'nearest'

        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(texture=self._tex, pos=(0, 0), size=(100, 100))

        self.bind(pos=self._on_geo, size=self._on_geo)
        self._on_geo()
        Clock.schedule_interval(self._update, 0)

    # ── 3D ──
    @staticmethod
    def _rotate(v, ay, ax):
        x, y, z = v
        cy, sy = math.cos(ay), math.sin(ay)
        x, z = x*cy + z*sy, -x*sy + z*cy
        cx, sx = math.cos(ax), math.sin(ax)
        y, z = y*cx - z*sx, y*sx + z*cx
        return x, y, z

    def _on_geo(self, *a):
        self._rect.pos = self.pos
        self._rect.size = self.size

    # ── 三角光栅化 ──
    def _rasterize(self, tri_2d, tri_z3, color, zbuf, pxbuf, w, h, ox, oy):
        """光栅化一个三角形到像素缓冲区."""
        (x0,y0),(x1,y1),(x2,y2) = tri_2d
        z0, z1, z2 = tri_z3

        # 包围盒
        min_x = max(0, int(min(x0,x1,x2) - ox))
        max_x = min(w-1, int(max(x0,x1,x2) - ox + 0.5))
        min_y = max(0, int(min(y0,y1,y2) - oy))
        max_y = min(h-1, int(max(y0,y1,y2) - oy + 0.5))

        # 重心坐标预计算
        denom = (y1-y2)*(x0-x2) + (x2-x1)*(y0-y2)
        if abs(denom) < 0.001:
            return

        for py in range(min_y, max_y + 1):
            for px in range(min_x, max_x + 1):
                sx = px + ox + 0.5
                sy = py + oy + 0.5
                w0 = ((y1-y2)*(sx-x2) + (x2-x1)*(sy-y2)) / denom
                w1 = ((y2-y0)*(sx-x2) + (x0-x2)*(sy-y2)) / denom
                w2 = 1.0 - w0 - w1
                if w0 >= 0 and w1 >= 0 and w2 >= 0:
                    z = w0*z0 + w1*z1 + w2*z2
                    idx = py * w + px
                    if z < zbuf[idx]:
                        zbuf[idx] = z
                        pxbuf[idx*4]   = color[0]
                        pxbuf[idx*4+1] = color[1]
                        pxbuf[idx*4+2] = color[2]
                        pxbuf[idx*4+3] = 255

    # ── 帧 ──
    def _update(self, dt):
        now = time.time(); self._tacc += dt
        if not self._dragging and (now - self._release_t) >= self.AUTO_RESUME_DELAY:
            self._auto_ay += self.AUTO_ROTATE_SPEED * dt
            self._auto_ay %= 2*math.pi

        ay = self._auto_ay + self._drag_ay
        ax = self._auto_ax + self._drag_ax

        ox, oy = self.pos
        w, h = int(self.width), int(self.height)
        if w < 2 or h < 2:
            return

        size = min(w, h)
        sc = size * 0.5 * self._mscale
        cx = ox + w/2
        cy = oy + h/2

        # 清空 z-buffer + 像素缓冲
        total = w * h
        zbuf = [float('inf')] * total
        pxbuf = bytearray(total * 4)  # RGBA

        # 3D 深度值: 近处 z 小(离相机近), need z_near=1 z_far=0
        # 用旋转后 z+8 映射: z-rot越小越近
        Lx, Ly, Lz = 0.0, 0.0, 1.0

        for face in self._faces:
            # 旋转 + 投影 3个顶点
            r0 = self._rotate(self._verts[face[0]], ay, ax)
            r1 = self._rotate(self._verts[face[1]], ay, ax)
            r2 = self._rotate(self._verts[face[2]], ay, ax)

            # 法线 + 光照
            e1x,e1y,e1z = r1[0]-r0[0], r1[1]-r0[1], r1[2]-r0[2]
            e2x,e2y,e2z = r2[0]-r0[0], r2[1]-r0[1], r2[2]-r0[2]
            nx = e1y*e2z - e1z*e2y
            ny = e1z*e2x - e1x*e2z
            nz = e1x*e2y - e1y*e2x
            nlen = math.sqrt(nx*nx+ny*ny+nz*nz) or 1
            ndotl = abs((nx*Lx + ny*Ly + nz*Lz) / nlen)
            bright = 0.30 + ndotl * 0.70

            # 投影
            proj_2d = []
            proj_z = []
            for (rx, ry, rz) in (r0, r1, r2):
                s = 2.5 / max(rz + 8.0, 0.1)
                proj_2d.append((rx*s*sc + cx, ry*s*sc + cy))
                # z 映射: 近=0, 远=1 (越小越近, 用于深度比较)
                proj_z.append((rz + 8.0) / 16.0)  # z范围~[-2,2], +8=[6,10], /16=[0.375,0.625]

            color = (
                int(self._diffuse[0] * bright * 255),
                int(self._diffuse[1] * bright * 255),
                int(self._diffuse[2] * bright * 255),
            )
            self._rasterize(proj_2d, proj_z, color, zbuf, pxbuf, w, h, ox, oy)

        # 更新贴图
        if self._tex.size != (w, h):
            self._tex = Texture.create(size=(w, h), colorfmt='rgba')
            self._tex.mag_filter = 'nearest'
            self._rect.texture = self._tex
        self._tex.blit_buffer(pxbuf, colorfmt='rgba', bufferfmt='ubyte')
        self.canvas.ask_update()

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
        self._diffuse = [r,g,b]; self._ambient = [r*0.3, g*0.3, b*0.35]

    def _on_evolution(self, vm, stage):
        self._mscale = {"形态A":1,"形态B":1.08,"形态C":1.15,"形态D":1.22,"形态E":1.3}.get(stage,1)
