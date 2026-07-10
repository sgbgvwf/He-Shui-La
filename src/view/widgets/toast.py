"""Toast widget — auto-animating feedback message with fade transitions."""

from kivy.animation import Animation
from kivy.properties import BooleanProperty
from kivy.uix.label import Label


class Toast(Label):
    """Fade-in / fade-out label driven by a ``visible`` property.

    Bind ``text`` and ``visible`` to ViewModel properties — the widget
    handles opacity animation internally.  No timer needed in the caller.
    """

    visible = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.opacity = 0

    def on_visible(self, instance, value):
        Animation.cancel_all(self)
        if value and self.text:
            Animation(opacity=1, duration=0.12).start(self)
        else:
            Animation(opacity=0, duration=0.25).start(self)
