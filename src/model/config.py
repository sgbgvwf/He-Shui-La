"""Centralized game configuration — single source of truth for all tunable values."""

import dataclasses
from dataclasses import dataclass, field

# ── streak bonus table: (min_days, multiplier) sorted ascending ────
_DEFAULT_STREAK_TABLE: tuple = ((3, 0.10), (7, 0.20), (15, 0.30), (30, 0.50))


@dataclass
class GameConfig:
    """All game parameters loaded from ``user_config.json`` at startup.

    Every field has a sensible default matching the design-doc v4.9
    placeholder values.  Changing a default here does NOT require
    touching model code — models read from this config at construction.
    """

    # ── Companion ──────────────────────────────────────────────
    hydration_per_drink: float = 20.0
    hydration_max: float = 100.0
    hydration_low_threshold: float = 20.0
    exp_per_drink: int = 10
    exp_per_level: int = 100
    decay_per_tick: float = 1.0

    # ── AntiCheat ──────────────────────────────────────────────
    cooldown_seconds: int = 300
    daily_max_cups: int = 15

    # ── DailyTracker ───────────────────────────────────────────
    daily_target: int = 8
    target_reward_exp: int = 20
    streak_bonus_table: tuple = field(default=_DEFAULT_STREAK_TABLE)

    # ── ViewModel ──────────────────────────────────────────────
    decay_interval_seconds: float = 3.0
    autosave_debounce_seconds: float = 2.0
    toast_duration_seconds: float = 2.5

    # ── User-facing ────────────────────────────────────────────
    partner_name: str = "小水滴"
    sound_enabled: bool = True

    # ── factory ────────────────────────────────────────────────

    @classmethod
    def from_user_config(cls, config: dict) -> "GameConfig":
        """Build a GameConfig from a ``user_config.json`` dict.

        Unknown keys are ignored; missing keys fall back to dataclass defaults.
        """
        known = {f.name for f in dataclasses.fields(cls)}
        kwargs = {k: v for k, v in config.items() if k in known}

        # coerce streak_bonus_table back to tuple-of-tuples (JSON stores lists)
        if "streak_bonus_table" in kwargs:
            raw = kwargs["streak_bonus_table"]
            if isinstance(raw, list):
                kwargs["streak_bonus_table"] = tuple(
                    (int(entry[0]), float(entry[1])) for entry in raw
                )

        return cls(**kwargs)
