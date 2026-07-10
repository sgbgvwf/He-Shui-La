"""Progress stars — shows today's drinking progress as gold star shapes.

Canvas-drawn 5-pointed stars using triangle-fan Mesh.
Font-independent — no missing-glyph boxes.
Binds to ViewModel ``today_cups``.
"""

from math import cos, sin, pi

from kivy.properties import NumericProperty, ObjectProperty
from kivy.uix.widget import Widget
from kivy.graphics import Color, Mesh


_RADIUS = 11                # star outer radius
_RATIO = 0.40               # inner/outer radius ratio
_SPACING = 28               # horizontal spacing between stars
_FILLED = (1.0, 0.84, 0.0, 1)       # gold
_EMPTY = (0.75, 0.75, 0.75, 0.55)   # light gray


def _star_vertices(cx, cy, r):
    """Return (x, y, u, v) list for a 5-pointed star centered at (cx, cy).

    Vertex 0 = center; vertices 1–10 = perimeter (outer/inner alternating).
    """
    inner = r * _RATIO
    positions = [(cx, cy)]  # center
    for i in range(10):
        angle = -pi / 2 + i * pi / 5
        radius = r if i % 2 == 0 else inner
        positions.append((cx + radius * cos(angle), cy + radius * sin(angle)))
    # flatten to (x, y, u, v) format
    flat = []
    for px, py in positions:
        flat.extend([px, py, 0, 0])
    return flat


def _star_indices():
    """Triangle-fan indices: center (0) + each perimeter wedge."""
    idx = []
    for i in range(10):
        idx.extend([0, i + 1, ((i + 1) % 10) + 1])
    return idx


class ProgressStars(Widget):
    """Horizontal row of stars tracking daily cup progress."""

    viewmodel = ObjectProperty(None)
    _star_count = NumericProperty(8)
    _filled_count = NumericProperty(0)

    def on_viewmodel(self, instance, vm):
        if vm is None:
            return
        vm.bind(today_cups=self._on_data_changed)
        self._star_count = vm.config.daily_target
        self._on_data_changed(vm, vm.today_cups)

    def on_size(self, *args):
        self._draw()

    def _on_data_changed(self, vm, cups):
        filled = min(int(cups), self._star_count)
        if filled == self._filled_count:
            return
        self._filled_count = filled
        self._draw()

    def _draw(self):
        self.canvas.clear()
        n = self._star_count
        if n == 0:
            return

        w = self.width
        total_w = n * _SPACING
        start_x = self.x + (w - total_w) / 2.0 - 30
        cy = self.y + self.height / 2.0

        # pre-compute shape once (all stars identical)
        star_verts = _star_vertices(0, 0, _RADIUS)
        indices = _star_indices()

        with self.canvas:
            for i in range(n):
                cx = start_x + i * _SPACING
                if i < self._filled_count:
                    Color(*_FILLED)
                else:
                    Color(*_EMPTY)
                # translate each star to its position
                verts = list(star_verts)
                for j in range(0, len(verts), 4):
                    verts[j] += cx      # x
                    verts[j + 1] += cy   # y
                Mesh(vertices=verts, indices=indices, mode="triangles")
