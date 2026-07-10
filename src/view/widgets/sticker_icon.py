"""Sticker icon — canvas-drawn, self-contained touch handling."""

from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle


class StickerIcon(Widget):
    """Tappable sticker icon: rounded square with center dot."""

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
        x, y = self.x, self.y
        w, h = self.width, self.height
        margin = max(w, h) * 0.15
        rx = x + margin
        ry = y + margin
        rw = w - margin * 2
        rh = h - margin * 2

        with self.canvas:
            Color(0.9, 0.75, 0.35, 1)
            RoundedRectangle(
                pos=(rx, ry),
                size=(rw, rh),
                radius=[4],
            )
            dot_r = min(rw, rh) * 0.18
            cx = rx + rw / 2.0 - dot_r
            cy = ry + rh / 2.0 - dot_r
            Color(0.8, 0.55, 0.15, 1)
            RoundedRectangle(
                pos=(cx, cy),
                size=(dot_r * 2, dot_r * 2),
                radius=[dot_r],
            )
