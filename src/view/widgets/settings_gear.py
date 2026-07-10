"""Settings gear icon — canvas-drawn, self-contained touch handling."""

from math import cos, sin, pi

from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse


class SettingsGear(Widget):
    """Tappable gear icon (8-tooth cog), canvas-drawn."""

    callback = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.callback:
                self.callback()
            return True
        return False

    def _draw(self, *args):
        self.canvas.clear()
        cx = self.x + self.width / 2.0
        cy = self.y + self.height / 2.0
        r = min(self.width, self.height) / 2.0 - 1

        tooth_r = r * 0.22
        body_r = r * 0.68
        hole_r = body_r * 0.42

        with self.canvas:
            Color(0.45, 0.45, 0.45, 1)
            for i in range(8):
                angle = i * pi / 4.0
                tx = cx + r * 0.82 * cos(angle) - tooth_r
                ty = cy + r * 0.82 * sin(angle) - tooth_r
                Ellipse(pos=(tx, ty), size=(tooth_r * 2, tooth_r * 2))

            Ellipse(
                pos=(cx - body_r, cy - body_r),
                size=(body_r * 2, body_r * 2),
            )

            Color(0.95, 0.95, 1.0, 1)
            Ellipse(
                pos=(cx - hole_r, cy - hole_r),
                size=(hole_r * 2, hole_r * 2),
            )
