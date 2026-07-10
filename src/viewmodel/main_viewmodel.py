"""Main screen ViewModel — bridges Model ↔ View via Kivy properties."""

from kivy.event import EventDispatcher
from kivy.properties import NumericProperty, StringProperty, BooleanProperty
from kivy.clock import Clock

from src.model.companion import Companion
from src.model.anti_cheat import AntiCheat
from src.model.daily_tracker import DailyTracker


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
    # debounce autosave window
    AUTOSAVE_DEBOUNCE_SECONDS = 2.0

    def __init__(self, data_dir: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.data_dir = data_dir
        self.companion = Companion()
        self.anticheat = AntiCheat()
        self.daily_tracker = DailyTracker()
        self._save_handle = None
        self._toast_handle = None

        # start decay clock
        Clock.schedule_interval(self._tick, self.DECAY_INTERVAL)

        # sync initial state
        self._sync_from_model()

    # ── commands ────────────────────────────────────────────────

    def drink_water(self) -> None:
        """Handle drink button press."""
        self.daily_tracker.reset_if_new_day()
        allowed, reason = self.anticheat.can_drink(self.daily_tracker.today_cups)

        if not allowed:
            self._show_toast(reason)
            return

        bonus = self.daily_tracker.streak_bonus

        companion_result = self.companion.drink(streak_bonus=bonus)
        tracker_result = self.daily_tracker.record()
        self.anticheat.record()
        self._sync_from_model()
        self._schedule_autosave()

        # Toast priority: target-completion > companion level-up > generic
        if tracker_result.get("target_just_completed"):
            bonus_result = self.companion.award_exp(20, streak_bonus=bonus)
            self._sync_from_model()
            if bonus_result.get("leveled_up"):
                stage = self.companion.evolution_stage
                self._show_toast(
                    f"每日目标达成！连击 {tracker_result['streak_days']} 天！"
                    f" 升级到 {stage}！"
                )
            else:
                self._show_toast(
                    f"每日目标达成！连击 {tracker_result['streak_days']} 天！"
                )
        elif companion_result.get("leveled_up"):
            stage = self.companion.evolution_stage
            self._show_toast(f"升级了！进化到 {stage}！")
        else:
            self._show_toast("咕噜咕噜～ 真好喝！")

    def dismiss_toast(self) -> None:
        self.toast_visible = False
        self.toast_message = ""
        if self._toast_handle is not None:
            self._toast_handle.cancel()
            self._toast_handle = None

    # ── persistence ─────────────────────────────────────────────

    def load_state(self, data_dir: str) -> None:
        """Load settings + state from disk. Called by App.build()."""
        from src.model.persistence import (
            load_user_config,
            load_game_state,
            ensure_data_dir,
        )
        self.data_dir = data_dir
        ensure_data_dir(data_dir)

        config = load_user_config(data_dir)

        # build state with settings from user_config
        state = load_game_state(data_dir)

        self.companion = Companion(
            name=config.get("partner_name", state["companion"].get("name", "小水滴"))
        )
        self.companion._hydration = state["companion"].get("hydration", 100.0)
        self.companion._exp = state["companion"].get("exp", 0)
        self.companion._level = state["companion"].get("level", 1)

        self.anticheat = AntiCheat.from_dict(
            state["anticheat"],
            cooldown_seconds=config["cooldown_seconds"],
            daily_max_cups=config["daily_max_cups"],
        )

        self.daily_tracker = DailyTracker.from_dict(
            state["daily_tracker"],
            daily_target=config.get("target_cups", 8),
        )

        self._sync_from_model()

    def save_state(self, data_dir: str | None = None) -> None:
        """Force-save state + settings. Called by on_stop / on_pause."""
        from src.model.persistence import save_game_state, save_user_config
        target = data_dir or self.data_dir
        if not target:
            return

        save_game_state(target, {
            "version": 1,
            "companion": self.companion.to_dict(),
            "anticheat": self.anticheat.to_dict(),
            "daily_tracker": self.daily_tracker.to_dict(),
        })
        save_user_config(target, {
            "version": 1,
            "target_cups": 8,  # placeholder; P1 settings screen will own this
            "cooldown_seconds": self.anticheat.cooldown_seconds,
            "daily_max_cups": self.anticheat.daily_max_cups,
            "sound_enabled": True,
            "partner_name": self.companion.name,
        })

        # cancel any pending debounced save (we just wrote synchronously)
        if self._save_handle is not None:
            self._save_handle.cancel()
            self._save_handle = None

    def _schedule_autosave(self) -> None:
        """Debounce 2s after a drink; on_stop/on_pause force final save."""
        if self._save_handle is not None:
            self._save_handle.cancel()
        self._save_handle = Clock.schedule_once(
            lambda _dt: self.save_state(), self.AUTOSAVE_DEBOUNCE_SECONDS
        )

    # ── internal ────────────────────────────────────────────────

    def _tick(self, dt: float) -> None:
        """Periodic decay + cross-day check."""
        self.daily_tracker.reset_if_new_day()
        self.companion.tick()
        self._sync_from_model()
        self._schedule_autosave()

    def _sync_from_model(self) -> None:
        """Push model state into observable properties."""
        c = self.companion
        self.hydration = c.hydration
        self.hydration_norm = c.hydration / 100.0
        self.level = c.level
        self.exp = c.exp
        self.evolution_stage = c.evolution_stage
        self.today_cups = self.daily_tracker.today_cups
        self.button_disabled = not self.anticheat.can_drink(
            self.daily_tracker.today_cups
        )[0]

    def _show_toast(self, msg: str) -> None:
        # cancel any pending dismiss before showing a new message
        if self._toast_handle is not None:
            self._toast_handle.cancel()
        self.toast_message = msg
        self.toast_visible = True
        self._toast_handle = Clock.schedule_once(
            lambda _dt: self.dismiss_toast(), 2.5
        )
