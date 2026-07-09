"""Main screen ViewModel — bridges Model ↔ View via Kivy properties."""

from kivy.event import EventDispatcher
from kivy.properties import NumericProperty, StringProperty, BooleanProperty
from kivy.clock import Clock

from src.model.companion import Companion
from src.model.anti_cheat import AntiCheat


class MainViewModel(EventDispatcher):
    """Aggregates all state for the main screen."""

    # ── observable properties ───────────────────────────────────

    hydration = NumericProperty(100)
    hydration_norm = NumericProperty(1.0)  # 0.0 ~ 1.0 for progress bar
    level = NumericProperty(1)
    exp = NumericProperty(0)
    evolution_stage = StringProperty("形态A")
    today_cups = NumericProperty(0)

    button_text = StringProperty("喝水啦！")
    button_disabled = BooleanProperty(False)
    toast_message = StringProperty("")
    toast_visible = BooleanProperty(False)

    # decay every 3 seconds
    DECAY_INTERVAL = 3.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.companion = Companion()
        self.anticheat = AntiCheat(cooldown_seconds=300, daily_max_cups=15)

        # start decay clock
        Clock.schedule_interval(self._tick, self.DECAY_INTERVAL)

        # sync initial state
        self._sync_from_model()

    # ── commands ────────────────────────────────────────────────

    def drink_water(self) -> None:
        """Handle drink button press."""
        allowed, reason = self.anticheat.can_drink()

        if not allowed:
            self._show_toast(reason)
            return

        result = self.companion.drink()
        self.anticheat.record()
        self._sync_from_model()

        if result.get("leveled_up"):
            stage = self.companion.evolution_stage
            self._show_toast(f"升级了！进化到 {stage}！")
        else:
            self._show_toast("咕噜咕噜～ 真好喝！")

    def dismiss_toast(self) -> None:
        self.toast_visible = False
        self.toast_message = ""

    # ── internal ────────────────────────────────────────────────

    def _tick(self, dt: float) -> None:
        """Periodic decay."""
        self.companion.tick()
        self._sync_from_model()

    def _sync_from_model(self) -> None:
        """Push model state into observable properties."""
        c = self.companion
        self.hydration = c.hydration
        self.hydration_norm = c.hydration / 100.0
        self.level = c.level
        self.exp = c.exp
        self.evolution_stage = c.evolution_stage
        self.today_cups = self.anticheat.today_cups
        self.button_disabled = not self.anticheat.can_drink()[0]

    def _show_toast(self, msg: str) -> None:
        self.toast_message = msg
        self.toast_visible = True
