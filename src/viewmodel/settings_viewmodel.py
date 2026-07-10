"""Settings ViewModel — arithmetic-gated parent settings."""

import random

from kivy.event import EventDispatcher
from kivy.properties import NumericProperty, StringProperty, BooleanProperty

from src.model.config import GameConfig


class SettingsViewModel(EventDispatcher):
    """Exposes GameConfig fields as Kivy properties for the settings dialog.

    Verification — simple addition problem before settings are accessible.
    """

    # ── settings ─────────────────────────────────────────────────

    daily_target = NumericProperty(8)
    cooldown_minutes = NumericProperty(5)
    daily_max_cups = NumericProperty(15)
    partner_name = StringProperty("小水滴")
    sound_enabled = BooleanProperty(True)

    # ── verification ─────────────────────────────────────────────

    verify_a = NumericProperty(0)
    verify_b = NumericProperty(0)
    verify_input = StringProperty("")
    verify_error = StringProperty("")

    def __init__(self, config: GameConfig, data_dir: str, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.data_dir = data_dir
        self._load_from_config()
        self.generate_question()

    # ── config ↔ properties ──────────────────────────────────────

    def _load_from_config(self) -> None:
        self.daily_target = self.config.daily_target
        self.cooldown_minutes = self.config.cooldown_seconds // 60
        self.daily_max_cups = self.config.daily_max_cups
        self.partner_name = self.config.partner_name
        self.sound_enabled = self.config.sound_enabled

    # ── verification ─────────────────────────────────────────────

    def generate_question(self) -> None:
        self.verify_a = random.randint(1, 20)
        self.verify_b = random.randint(1, 20)
        self.verify_input = ""
        self.verify_error = ""

    def check_verification(self) -> bool:
        try:
            answer = int(self.verify_input.strip())
        except ValueError:
            self.verify_error = "请输入数字"
            return False
        if answer == self.verify_a + self.verify_b:
            self.verify_error = ""
            return True
        self.generate_question()
        self.verify_error = "答案不对，再试一次"
        return False

    # ── actions ──────────────────────────────────────────────────

    def save(self) -> None:
        """Write current property values into config and persist to disk."""
        self.config.daily_target = int(self.daily_target)
        self.config.cooldown_seconds = int(self.cooldown_minutes * 60)
        self.config.daily_max_cups = int(self.daily_max_cups)
        self.config.partner_name = self.partner_name
        self.config.sound_enabled = bool(self.sound_enabled)

        from src.model.persistence import save_user_config, ensure_data_dir

        ensure_data_dir(self.data_dir)
        save_user_config(self.data_dir, {
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

    def reset_data(self) -> None:
        """Reset game state to defaults."""
        from src.model.persistence import save_game_state, _default_game_state

        save_game_state(self.data_dir, _default_game_state())
