"""伙伴展示 Widget — NumPy 光栅化 + 多伙伴 + 水滴粒子."""

import json, math, os, struct, time, random
import numpy as np

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.graphics.texture import Texture
from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget

_MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "models")
_DEFAULT_MODEL = os.path.join(_MODELS_DIR, "companion.glb")

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

def load_model(path: str):
    """加载 3D 模型，返回 (顶点, 三角面, 材质色或None)。"""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.obj':
        return (*_load_obj(path), None)
    elif ext == '.glb':
        return _load_glb(path)
    else:
        raise ValueError(f"Unsupported format: {ext}")


def _load_obj(path):
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


def _load_glb(path):
    """解析 GLB (glTF Binary) 文件，返回 (顶点, 三角面)。"""
    with open(path, "rb") as f:
        data = f.read()

    # ── Header ──
    magic, version, total_len = struct.unpack_from("<I II", data, 0)
    if magic != 0x46546C67:
        raise ValueError("Not a valid GLB file")

    # ── Chunks ──
    offset = 12
    json_data = None
    bin_data = None
    while offset < total_len:
        chunk_len, chunk_type = struct.unpack_from("<I I", data, offset)
        chunk_start = offset + 8
        if chunk_type == 0x4E4F534A:  # JSON
            json_data = json.loads(data[chunk_start:chunk_start + chunk_len])
        elif chunk_type == 0x004E4942:  # BIN
            bin_data = data[chunk_start:chunk_start + chunk_len]
        offset = chunk_start + chunk_len

    if json_data is None:
        raise ValueError("GLB missing JSON chunk")

    # ── Helpers ──
    def get_accessor_data(acc_idx):
        acc = json_data["accessors"][acc_idx]
        bv = json_data["bufferViews"][acc["bufferView"]]
        bo = acc.get("byteOffset", 0) + bv.get("byteOffset", 0)
        ct = acc["componentType"]
        at = acc["type"]
        count = acc["count"]
        comp_count = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[at]
        fmt_map = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
        fmt = fmt_map[ct]
        total = count * comp_count
        return struct.unpack_from(f"<{total}{fmt}", bin_data, bo), count, comp_count

    positions = []
    all_faces = []
    face_materials = []  # 每面一个颜色或 None

    # ── Materials ──
    base_colours = []
    if "materials" in json_data:
        for mat in json_data["materials"]:
            pbr = mat.get("pbrMetallicRoughness", {})
            bc = pbr.get("baseColorFactor", [0.5, 0.5, 0.5, 1.0])
            base_colours.append(tuple(bc[:3]))

    def _mat_color(mat_idx):
        if mat_idx is not None and mat_idx < len(base_colours):
            r, g, b = base_colours[mat_idx]
            # 线性 → sRGB gamma 校正
            return (r ** (1/2.2), g ** (1/2.2), b ** (1/2.2))
        return None

    # ── Scene graph → meshes ──
    def visit_node(node_idx):
        node = json_data["nodes"][node_idx]
        mesh_idx = node.get("mesh")
        if mesh_idx is not None:
            mesh = json_data["meshes"][mesh_idx]
            for prim in mesh["primitives"]:
                mat_color = _mat_color(prim.get("material"))
                raw, cnt, _ = get_accessor_data(prim["attributes"]["POSITION"])
                vert_start = len(positions)
                for i in range(cnt):
                    positions.append((raw[i*3], raw[i*3+1], raw[i*3+2]))
                if "indices" in prim:
                    raw, cnt, _ = get_accessor_data(prim["indices"])
                    for i in range(0, cnt, 3):
                        all_faces.append([vert_start+raw[i], vert_start+raw[i+1], vert_start+raw[i+2]])
                        face_materials.append(mat_color)
                else:
                    for i in range(0, cnt, 3):
                        all_faces.append([vert_start+i, vert_start+i+1, vert_start+i+2])
                        face_materials.append(mat_color)
        for child_idx in node.get("children", []):
            visit_node(child_idx)

    scene_idx = json_data.get("scene", 0)
    scene = json_data["scenes"][scene_idx]
    for root_node in scene.get("nodes", []):
        visit_node(root_node)

    if not positions:
        raise ValueError("GLB has no mesh data")

    return positions, all_faces, face_materials


class Companion3DWidget(Widget):
    """NumPy z-buffer 3D + 多伙伴切换 + 水滴粒子."""

    viewmodel = ObjectProperty(None)
    AUTO_ROTATE_SPEED = 0.6
    AUTO_RESUME_DELAY = 1.0
    DRAG_SENSITIVITY = 0.01
    SLIDE_DURATION = 0.35          # 切换滑动时间(秒)

    def __init__(self, model_path=None, model_paths=None, companions=None, **kwargs):
        super().__init__(**kwargs)
        self._auto_ay = 0.0; self._auto_ax = -0.6
        self._drag_ay = 0.0; self._drag_ax = 0.0
        self._dragging = False; self._release_t = 0.0
        self._last_t = (0.0, 0.0); self._tacc = 0.0
        self._mscale = 1.0
        self._diffuse = [0.25, 0.65, 1.00]
        self._ambient = [0.08, 0.20, 0.35]
        self._face_materials = None
        self._slide_prev_mats = None

        # ── 伙伴列表 ──
        self._companions: list[str] = list(companions or [])
        if model_path: self._companions.append(model_path)
        if not self._companions: self._companions = [_DEFAULT_MODEL]
        self._current_idx = 0

        # ── 每伙伴独立数据: {idx: {level, stage, scale}}  喝水值全局共享 ──
        self._companion_data: dict[int, dict] = {}
        for i in range(len(self._companions)):
            self._companion_data[i] = {"level": 1, "stage": "形态A", "scale": 1.0}

        # ── 模型注册表 (阶段→路径) ──
        self._model_paths: dict[str, str] = {}
        if model_paths: self._model_paths.update(model_paths)

        # ── 模型缓存 ──
        self._model_cache: dict[str, dict] = {}
        self._verts: list = _CUBE_VERTS
        self._faces: list[list[int]] = _CUBE_FACES
        self._load_model(self._companions[0])

        # ── 滑动动画 ──
        self._slide_offset = 0.0         # 当前滑动偏移 (-1~1, 0=正常)
        self._slide_prev_verts = None    # 切换前的模型顶点(用于同时渲染)
        self._slide_prev_faces = None
        self._slide_prev_material = None # 切换前的材质颜色

        # ── 水滴粒子 ──
        self._drops: list[dict] = []    # [{x, y, vy, life, size}]

        # ── 贴图 ──
        self._tex = Texture.create(size=(2, 2), colorfmt='rgba')
        self._tex.mag_filter = 'nearest'
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(texture=self._tex, pos=(0, 0), size=(100, 100))

        # ── 切换 UI ──
        self._arrows_visible = False  # 左右箭头是否可见

        with self.canvas:
            # 触发按钮 (始终可见, 右上角)
            self._btn_bg = Color(0.2, 0.2, 0.2, 0.4)
            self._btn_circle = Ellipse(pos=(0,0), size=(0,0))
            self._btn_c = Color(1, 1, 1, 0.85)
            self._btn_lines = Line(points=[0,0]*6, width=2)  # ↕ 图标

            # 左箭头 (条件可见)
            self._la_bg = Color(0, 0, 0, 0.3)
            self._la_circle = Ellipse(pos=(0,0), size=(0,0))
            self._la_c = Color(1, 1, 1, 0.7)
            self._la_icon = Line(points=[0,0,0,0,0,0], width=2, close=True)

            # 右箭头 (条件可见)
            self._ra_bg = Color(0, 0, 0, 0.3)
            self._ra_circle = Ellipse(pos=(0,0), size=(0,0))
            self._ra_c = Color(1, 1, 1, 0.7)
            self._ra_icon = Line(points=[0,0,0,0,0,0], width=2, close=True)

        self.bind(pos=self._on_geo, size=self._on_geo)
        self._on_geo()
        Clock.schedule_interval(self._update, 0)

    # ═══════════════════════════════════════════════════════════════
    # 伙伴切换 (带滑动动效)
    # ═══════════════════════════════════════════════════════════════
    def _next_companion(self):
        self._switch_companion(1)

    def _prev_companion(self):
        self._switch_companion(-1)

    def _switch_companion(self, direction: int):
        if len(self._companions) <= 1: return
        # 保存当前伙伴数据 (等级/形态，不包括水分)
        self._companion_data[self._current_idx]["scale"] = self._mscale
        # 保存旧模型用于过渡渲染
        self._slide_prev_verts = self._verts
        self._slide_prev_faces = self._faces
        self._slide_prev_mats = self._face_materials
        self._slide_offset = float(direction)

        self._current_idx = (self._current_idx + direction) % len(self._companions)
        self._load_model(self._companions[self._current_idx])

        # 恢复新伙伴数据
        data = self._companion_data[self._current_idx]
        self._mscale = data.get("scale", 1.0)

    # ═══════════════════════════════════════════════════════════════
    # 水滴粒子
    # ═══════════════════════════════════════════════════════════════
    def trigger_drops(self, count: int = 20):
        """触发水滴粒子动画。"""
        w, h = self.width, self.height
        cx, cy = self.pos[0] + w/2, self.pos[1] + h*0.95
        for _ in range(count):
            angle = random.uniform(-0.9, 0.9)
            dist = random.uniform(w*0.03, w*0.22)
            self._drops.append({
                "x": cx + math.sin(angle) * dist,
                "y": cy + random.uniform(0, h*0.08),
                "vy": random.uniform(-50, -20),
                "life": random.uniform(1.8, 3.0),
                "size": random.uniform(5, 9),
            })

    # ═══════════════════════════════════════════════════════════════
    # 3D 数学
    # ═══════════════════════════════════════════════════════════════
    @staticmethod
    def _rotate(v, ay, ax):
        x, y, z = v
        cy, sy = math.cos(ay), math.sin(ay)
        x, z = x*cy+z*sy, -x*sy+z*cy
        cx, sx = math.cos(ax), math.sin(ax)
        y, z = y*cx-z*sx, y*sx+z*cx
        return x, y, z

    def _render_model(self, verts, faces, sc, cx, cy, ay, ax, zbuf, pxbuf, ox, oy,
                      face_mats=None):
        """渲染模型。face_mats: 每面颜色或None(用水分色)。"""
        mats = face_mats or ([None] * len(faces))
        Lx, Ly, Lz = 0.0, 0.0, 1.0
        for fi, face in enumerate(faces):
            mat = mats[fi] if fi < len(mats) else None
            eff = list(mat) if mat else self._diffuse
            r0 = self._rotate(verts[face[0]], ay, ax)
            r1 = self._rotate(verts[face[1]], ay, ax)
            r2 = self._rotate(verts[face[2]], ay, ax)
            e1x,e1y,e1z = r1[0]-r0[0], r1[1]-r0[1], r1[2]-r0[2]
            e2x,e2y,e2z = r2[0]-r0[0], r2[1]-r0[1], r2[2]-r0[2]
            nx = e1y*e2z-e1z*e2y; ny = e1z*e2x-e1x*e2z; nz = e1x*e2y-e1y*e2x
            nlen = math.sqrt(nx*nx+ny*ny+nz*nz) or 1
            bright = 0.30 + abs((nx*Lx+ny*Ly+nz*Lz)/nlen)*0.70
            p2d = []
            for (rx,ry,rz) in (r0,r1,r2):
                s = 2.5 / max(rz+8.0, 0.1)
                p2d.append((rx*s*sc+cx, ry*s*sc+cy, (rz+8.0)/16.0))
            color = np.array([eff[0]*bright, eff[1]*bright, eff[2]*bright, 1.0], dtype=np.float32)
            self._rasterize(p2d, color, zbuf, pxbuf, ox, oy)

    # ═══════════════════════════════════════════════════════════════
    # 圆环 + 光栅化
    # ═══════════════════════════════════════════════════════════════
    def _draw_ring(self, pxbuf, w, h):
        norm = getattr(self, '_hydration_norm', 1.0)
        r = np.array([0.45-0.25*norm, 0.50+0.35*norm, 0.55+0.45*norm, 1.0])
        rg = np.array([0.24, 0.24, 0.27, 0.31])
        size = min(w, h); cx, cy = w/2, h/2
        r_out, r_in = size*0.44, size*0.37
        yy, xx = np.ogrid[:h, :w]
        dist2 = (xx-cx+0.5)**2 + (yy-cy+0.5)**2
        mask = (dist2>=r_in*r_in) & (dist2<=r_out*r_out)
        angle = np.arctan2(xx-cx+0.5, yy-cy+0.5)
        angle[angle<0] += 2*np.pi
        filled = angle/(2*np.pi) <= norm
        pxbuf[filled&mask] = (r*255).astype(np.uint8)
        pxbuf[(~filled)&mask] = (rg*255).astype(np.uint8)

    @staticmethod
    def _rasterize(p2d, color, zbuf, pxbuf, ox, oy):
        (x0,y0,z0),(x1,y1,z1),(x2,y2,z2) = p2d
        mx = int(max(0, min(x0,x1,x2)-ox)); Mx = int(min(pxbuf.shape[1]-1, max(x0,x1,x2)-ox))
        my = int(max(0, min(y0,y1,y2)-oy)); My = int(min(pxbuf.shape[0]-1, max(y0,y1,y2)-oy))
        if mx>Mx or my>My: return
        yy, xx = np.ogrid[my:My+1, mx:Mx+1]
        sx, sy = xx+ox+0.5, yy+oy+0.5
        denom = (y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
        if abs(denom)<0.001: return
        w0 = ((y1-y2)*(sx-x2)+(x2-x1)*(sy-y2))/denom
        w1 = ((y2-y0)*(sx-x2)+(x0-x2)*(sy-y2))/denom
        w2 = 1-w0-w1
        inside = (w0>=0)&(w1>=0)&(w2>=0)
        if not inside.any(): return
        z = w0*z0+w1*z1+w2*z2
        region_z = zbuf[my:My+1, mx:Mx+1]
        closer = inside & (z < region_z)
        zbuf[my:My+1, mx:Mx+1][closer] = z[closer]
        c = (color*255).astype(np.uint8)
        pxbuf[my:My+1, mx:Mx+1][closer] = c

    # ═══════════════════════════════════════════════════════════════
    # 帧
    # ═══════════════════════════════════════════════════════════════
    def _update(self, dt):
        now = time.time(); self._tacc += dt
        if not self._dragging and (now-self._release_t) >= self.AUTO_RESUME_DELAY:
            self._auto_ay += self.AUTO_ROTATE_SPEED*dt; self._auto_ay %= 2*math.pi

        # ── 滑动动画 ──
        if abs(self._slide_offset) > 0.001:
            self._slide_offset += (-self._slide_offset) * min(1.0, dt*8)
            if abs(self._slide_offset) < 0.005:
                self._slide_offset = 0.0
                self._slide_prev_verts = None
                self._slide_prev_faces = None
                self._slide_prev_material = None

        ay = self._auto_ay + self._drag_ay
        ax = self._auto_ax + self._drag_ax
        ox, oy = self.pos; w, h = int(self.width), int(self.height)
        if w<2 or h<2: return
        sc = min(w,h)*0.5*self._mscale
        cx, cy = ox+w/2, oy+h/2

        zbuf = np.full((h,w), np.inf, dtype=np.float32)
        pxbuf = np.zeros((h,w,4), dtype=np.uint8)

        self._draw_ring(pxbuf, w, h)

        # ── 滑动过渡: 同时渲染旧模型和新模型 ──
        slide = self._slide_offset
        if abs(slide) > 0.001 and self._slide_prev_verts is not None:
            # 旧模型滑出
            shift_x = slide * w * 0.8
            self._render_model(self._slide_prev_verts, self._slide_prev_faces, sc, cx+shift_x, cy, ay, ax, zbuf, pxbuf, ox, oy, self._slide_prev_mats)
            shift_x2 = (slide - (1 if slide>0 else -1)) * w * 0.8 * (-1)
            if slide > 0: shift_x2 = (slide-1)*w*0.8
            else: shift_x2 = (slide+1)*w*0.8
            self._render_model(self._verts, self._faces, sc, cx+shift_x2, cy, ay, ax, zbuf, pxbuf, ox, oy, self._face_materials)
        else:
            self._render_model(self._verts, self._faces, sc, cx, cy, ay, ax, zbuf, pxbuf, ox, oy, self._face_materials)

        # ── 水滴粒子 ──
        for drop in self._drops:
            drop["y"] += drop["vy"] * dt
            drop["vy"] -= 120 * dt  # 重力
            drop["life"] -= dt
        self._drops = [d for d in self._drops if d["life"] > 0]

        # 绘制水滴 (在3D模型之上)
        for drop in self._drops:
            dx = int(drop["x"]-ox); dy = int(drop["y"]-oy)
            sz = int(drop["size"])
            alpha = min(1.0, drop["life"]/0.3)
            drop_color = np.array([0.30, 0.75, 1.0, alpha])
            x0 = max(0, dx-sz); x1 = min(w-1, dx+sz)
            y0 = max(0, dy-sz); y1 = min(h-1, dy+sz)
            if x0>x1 or y0>y1: continue
            yy, xx = np.ogrid[y0:y1+1, x0:x1+1]
            d2 = (xx-dx)**2 + (yy-dy)**2
            mask = d2 <= sz*sz
            c = (drop_color*255).astype(np.uint8)
            region = pxbuf[y0:y1+1, x0:x1+1]
            region[mask] = c

        # 更新贴图
        if self._tex.size != (w,h):
            self._tex = Texture.create(size=(w,h), colorfmt='rgba')
            self._tex.mag_filter = 'nearest'
            self._rect.texture = self._tex
        self._tex.blit_buffer(pxbuf.tobytes(), colorfmt='rgba', bufferfmt='ubyte')
        self.canvas.ask_update()

    # ═══════════════════════════════════════════════════════════════
    # UI 几何
    # ═══════════════════════════════════════════════════════════════
    def _on_geo(self, *a):
        ox, oy = self.pos; w, h = self.size
        self._rect.pos = (ox, oy); self._rect.size = (w, h)
        if len(self._companions) <= 1: return
        r = min(w, h) * 0.06
        # ── 触发按钮 (右上角, 始终可见) ──
        br = r * 1.3
        bx, by = ox + w - br*2 - 4, oy + h - br*2 - 4
        self._btn_circle.pos = (bx, by)
        self._btn_circle.size = (br*2, br*2)
        # ↕ 图标: 上下两个箭头
        cx, cy = bx + br, by + br
        s = br * 0.35
        self._btn_lines.points = [
            cx-s, cy+s, cx, cy+s*0.4, cx+s, cy+s,  # 上箭头
            cx-s, cy-s, cx, cy-s*0.4, cx+s, cy-s,  # 下箭头
        ]
        # ── 左右箭头 (仅在选择模式时显示) ──
        if self._arrows_visible:
            lx, ly = ox + 8, oy + h/2 - r
            rx = ox + w - 8 - r*2
            for circle, icon, x in [(self._la_circle, self._la_icon, lx),
                                     (self._ra_circle, self._ra_icon, rx)]:
                circle.pos = (x - r*0.3, ly - r*0.3)
                circle.size = (r*2.6, r*2.6)
            self._la_icon.points = [lx+r*0.8, ly+r*1.3, lx+r*0.2, ly+r, lx+r*0.8, ly+r*0.7]
            rx2 = rx + r*0.2
            self._ra_icon.points = [rx2+r*0.3, ly+r*1.3, rx2+r*0.9, ly+r, rx2+r*0.3, ly+r*0.7]
        else:
            self._la_circle.pos = (-100, -100); self._la_circle.size = (0, 0)
            self._ra_circle.pos = (-100, -100); self._ra_circle.size = (0, 0)

    # ═══════════════════════════════════════════════════════════════
    # 触控
    # ═══════════════════════════════════════════════════════════════
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if len(self._companions) <= 1:
            touch.grab(self); self._dragging = True; self._last_t = touch.pos; return True
        # 1. 触发按钮 (始终响应)
        if self._hit_circle(touch, self._btn_circle):
            self._arrows_visible = not self._arrows_visible
            self._update_arrow_visibility()
            return True
        # 2. 左右箭头 (仅在可见时响应, 不退出模式)
        if self._arrows_visible:
            if self._hit_circle(touch, self._la_circle):
                self._prev_companion(); return True
            if self._hit_circle(touch, self._ra_circle):
                self._next_companion(); return True
            # 点击非箭头区域 → 退出选择模式
            self._arrows_visible = False; self._update_arrow_visibility()
        touch.grab(self); self._dragging = True
        self._last_t = touch.pos; return True

    @staticmethod
    def _hit_circle(touch, circle):
        cx, cy = circle.pos; r = circle.size[0]/2
        return abs(touch.x-(cx+r))<r*1.3 and abs(touch.y-(cy+r))<r*1.3

    def _update_arrow_visibility(self):
        """根据 _arrows_visible 显隐左右箭头."""
        if self._arrows_visible:
            self._on_geo()
        else:
            # 移出屏幕确保彻底隐藏
            self._la_circle.pos = (-100, -100)
            self._la_circle.size = (0, 0)
            self._ra_circle.pos = (-100, -100)
            self._ra_circle.size = (0, 0)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            dx = touch.x-self._last_t[0]; dy = touch.y-self._last_t[1]
            self._drag_ay -= dx*self.DRAG_SENSITIVITY
            self._drag_ax += dy*self.DRAG_SENSITIVITY*0.5
            self._last_t = touch.pos; return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self); self._dragging = False
            self._release_t = time.time(); return True
        return super().on_touch_up(touch)

    # ═══════════════════════════════════════════════════════════════
    # 模型加载
    # ═══════════════════════════════════════════════════════════════
    def _load_model(self, path):
        if path in self._model_cache:
            e = self._model_cache[path]
            self._verts = e["verts"]; self._faces = e["faces"]
            self._face_materials = e.get("mats")
            return
        if os.path.exists(path):
            try:
                v, f, mats = load_model(path)
                self._model_cache[path] = {"verts": v, "faces": f, "mats": mats}
                self._verts = v; self._faces = f
                self._face_materials = mats
            except Exception as e:
                print(f"load fail: {path} ({e})")
        else:
            print(f"not found: {path}")

    def set_model(self, path): self._load_model(path)
    def set_models(self, paths): self._model_paths.update(paths)

    def setup_companions(self, paths: list[str]):
        """运行时配置多伙伴列表。清除旧伙伴，重新加载。"""
        self._companions = list(paths)
        self._current_idx = 0
        self._companion_data = {}
        for i in range(len(self._companions)):
            self._companion_data[i] = {"level": 1, "stage": "形态A", "scale": 1.0}
        self._load_model(self._companions[0])
        if hasattr(self, '_arr_l_circle') and len(self._companions) <= 1:
            self._arr_l_circle.size = (0, 0); self._arr_r_circle.size = (0, 0)
        self._on_geo()

    @property
    def current_companion_index(self): return self._current_idx
    @property
    def companion_count(self): return len(self._companions)

    # ═══════════════════════════════════════════════════════════════
    # ViewModel
    # ═══════════════════════════════════════════════════════════════
    def on_viewmodel(self, instance, vm):
        if vm is None: return
        vm.bind(hydration_norm=self._on_hydration)
        vm.bind(evolution_stage=self._on_evolution)
        vm.bind(drops_trigger=self._on_drops)
        self._on_hydration(vm, vm.hydration_norm)
        self._on_evolution(vm, vm.evolution_stage)

    def _on_drops(self, vm, val):
        self.trigger_drops(15)

    def _on_hydration(self, vm, norm):
        norm = max(0, min(1, norm))
        self._hydration_norm = norm
        r,g,b = 0.45-0.25*norm, 0.50+0.35*norm, 0.55+0.45*norm
        self._diffuse = [r,g,b]; self._ambient = [r*0.3, g*0.3, b*0.35]

    def _on_evolution(self, vm, stage):
        self._mscale = {"形态A":1,"形态B":1.08,"形态C":1.15,"形态D":1.22,"形态E":1.3}.get(stage,1)
        if stage in self._model_paths:
            self._load_model(self._model_paths[stage])
