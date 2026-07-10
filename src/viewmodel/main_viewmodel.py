"""Main screen ViewModel — bridges Model ↔ View via Kivy properties."""

from kivy.event import EventDispatcher
from kivy.properties import NumericProperty, StringProperty, BooleanProperty
from kivy.clock import Clock

from src.model.companion import Companion
from src.model.anti_cheat import AntiCheat
from src.model.daily_tracker import DailyTracker
from src.model.config import GameConfig


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

    def __init__(self, data_dir: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.data_dir = data_dir
        self.config = GameConfig()

        self.companion = self._make_companion(self.config)
        self.anticheat = AntiCheat(
            cooldown_seconds=self.config.cooldown_seconds,
            daily_max_cups=self.config.daily_max_cups,
        )
        self.daily_tracker = DailyTracker(
            daily_target=self.config.daily_target,
            streak_bonus_table=self.config.streak_bonus_table,
        )
        self._save_handle = None
        self._toast_handle = None

        Clock.schedule_interval(self._tick, self.config.decay_interval_seconds)
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

        if tracker_result.get("target_just_completed"):
            bonus_result = self.companion.award_exp(
                self.config.target_reward_exp, streak_bonus=bonus
            )
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

        raw_config = load_user_config(data_dir)
        self.config = GameConfig.from_user_config(raw_config)

        state = load_game_state(data_dir)

        self.companion = self._make_companion(
            self.config,
            name=self.config.partner_name,
        )
        self.companion._hydration = state["companion"].get("hydration", 100.0)
        self.companion._exp = state["companion"].get("exp", 0)
        self.companion._level = state["companion"].get("level", 1)

        self.anticheat = AntiCheat.from_dict(
            state["anticheat"],
            cooldown_seconds=self.config.cooldown_seconds,
            daily_max_cups=self.config.daily_max_cups,
        )

        self.daily_tracker = DailyTracker.from_dict(
            state["daily_tracker"],
            daily_target=self.config.daily_target,
            streak_bonus_table=self.config.streak_bonus_table,
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
            "target_cups": self.config.daily_target,
            "target_reward_exp": self.config.target_reward_exp,
            "streak_bonus_table": [
                [int(d), float(r)] for d, r in self.config.streak_bonus_table
            ],
            "cooldown_seconds": self.config.cooldown_seconds,
            "daily_max_cups": self.config.daily_max_cups,
            "hydration_per_drink": self.config.hydration_per_drink,
            "hydration_max": self.config.hydration_max,
            "hydration_low_threshold": self.config.hydration_low_threshold,
            "exp_per_drink": self.config.exp_per_drink,
            "exp_per_level": self.config.exp_per_level,
            "decay_per_tick": self.config.decay_per_tick,
            "decay_interval_seconds": self.config.decay_interval_seconds,
            "autosave_debounce_seconds": self.config.autosave_debounce_seconds,
            "toast_duration_seconds": self.config.toast_duration_seconds,
            "sound_enabled": self.config.sound_enabled,
            "partner_name": self.config.partner_name,
        })

        if self._save_handle is not None:
            self._save_handle.cancel()
            self._save_handle = None

    def reload_config(self) -> None:
        """Reload config + state from disk. Called after settings changed."""
        if self.data_dir:
            self.load_state(self.data_dir)

    def _schedule_autosave(self) -> None:
        if self._save_handle is not None:
            self._save_handle.cancel()
        self._save_handle = Clock.schedule_once(
            lambda _dt: self.save_state(),
            self.config.autosave_debounce_seconds,
        )

    # ── internal ────────────────────────────────────────────────

    @staticmethod
    def _make_companion(config: GameConfig, name: str | None = None) -> Companion:
        """Build a Companion from config values."""
        return Companion(
            name=name or config.partner_name,
            hydration_max=config.hydration_max,
            hydration_per_drink=config.hydration_per_drink,
            hydration_low_threshold=config.hydration_low_threshold,
            exp_per_drink=config.exp_per_drink,
            exp_per_level=config.exp_per_level,
            decay_per_tick=config.decay_per_tick,
        )

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
        self.hydration_norm = c.hydration / self.config.hydration_max
        self.level = c.level
        self.exp = c.exp
        self.evolution_stage = c.evolution_stage
        self.today_cups = self.daily_tracker.today_cups
        self.button_disabled = not self.anticheat.can_drink(
            self.daily_tracker.today_cups
        )[0]

    def _show_toast(self, msg: str) -> None:
        if self._toast_handle is not None:
            self._toast_handle.cancel()
        self.toast_message = msg
        self.toast_visible = True
        self._toast_handle = Clock.schedule_once(
            lambda _dt: self.dismiss_toast(),
            self.config.toast_duration_seconds,
        )
