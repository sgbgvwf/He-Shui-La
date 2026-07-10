"""Streak fire — flame icon + streak counter, intensity grows with days.

Canvas-drawn flame shape + label, font-independent.
Binds to ViewModel ``streak_days`` via ``viewmodel`` property.
"""

from kivy.properties import NumericProperty, ObjectProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Ellipse, Mesh


# ── flame color tiers (bg, tip) ────────────────────────────
_TIERS = [
    (0,   (0.65, 0.65, 0.65, 1), (0.55, 0.55, 0.55, 1)),   # gray (no streak)
    (1,   (1.0, 0.65, 0.1, 1),   (1.0, 0.45, 0.0, 1)),      # orange
    (3,   (1.0, 0.35, 0.1, 1),   (0.95, 0.2, 0.0, 1)),      # red-orange
    (7,   (1.0, 0.15, 0.05, 1),  (0.9, 0.05, 0.0, 1)),      # deep red
    (15,  (0.9, 0.1, 0.5, 1),    (0.7, 0.0, 0.7, 1)),        # purple
    (30,  (0.2, 0.3, 1.0, 1),    (0.1, 0.1, 0.8, 1)),        # blue
]


def _pick_color(days):
    """Return (body_rgba, tip_rgba) for the given streak days."""
    body, tip = _TIERS[0][1], _TIERS[0][2]
    for threshold, b, t in _TIERS:
        if days >= threshold:
            body, tip = b, t
    return body, tip


class StreakFire(FloatLayout):
    """Flame icon + streak-day count, size/color driven by streak_days."""

    viewmodel = ObjectProperty(None)
    _streak = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._label = Label(
            font_size="18sp",
            bold=True,
            halign="center",
            valign="middle",
            color=(1, 1, 1, 1),
            size_hint=(1, 1),
        )
        self.add_widget(self._label)

    def on_viewmodel(self, instance, vm):
        if vm is None:
            return
        vm.bind(today_cups=self._on_streak_changed)
        self._on_streak_changed(vm, 0)

    def _on_streak_changed(self, vm, _cups):
        s = vm.daily_tracker.streak_days
        if s == self._streak:
            return
        self._streak = s
        self._label.text = str(s) if s > 0 else ""
        self._draw()

    def on_size(self, *args):
        self._draw()

    # ── drawing ───────────────────────────────────────────────

    def _draw(self):
        self.canvas.clear()
        s = self._streak
        body_rgba, tip_rgba = _pick_color(s)

        cx = self.x + self.width / 2.0
        base_y = self.y + 3
        body_r = min(self.width * 0.4, self.height * 0.22)

        # scale up with streak (capped)
        scale = 1.0 + min(s, 30) * 0.008
        body_r *= scale

        # ── flame tip (triangle) ──
        tip_h = body_r * 2.2
        tip_w = body_r * 0.7
        tip_verts = [
            cx, base_y + body_r * 1.4, 0, 0,         # bottom-left
            cx + tip_w, base_y + body_r * 0.8, 0, 0,  # mid-right
            cx, base_y + body_r * 1.4 + tip_h, 0, 0,   # top
            cx - tip_w, base_y + body_r * 0.8, 0, 0,  # mid-left
        ]

        with self.canvas:
            # main body (circle)
            Color(*body_rgba)
            Ellipse(
                pos=(cx - body_r, base_y),
                size=(body_r * 2, body_r * 2),
            )

            # flame tip
            Color(*tip_rgba)
            Mesh(
                vertices=tip_verts,
                indices=[0, 1, 2, 0, 2, 3],
                mode="triangles",
            )
