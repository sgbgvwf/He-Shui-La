"""Anti-cheat: cooldown timer between drinks."""

import time


class AntiCheat:
    """Validates drink actions with a configurable cooldown and daily cap.

    Daily cup tracking has been extracted to ``DailyTracker`` — pass
    ``today_cups`` into ``can_drink()`` from the tracker.
    """

    def __init__(self, cooldown_seconds: int = 300, daily_max_cups: int = 15) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.daily_max_cups = daily_max_cups
        self._last_drink_time: float = 0.0

    # ── validation ──────────────────────────────────────────────

    def can_drink(self, today_cups: int = 0) -> tuple[bool, str]:
        """Return (allowed, reason).  Pure query — no side-effects.

        Args:
            today_cups: Current cups count from ``DailyTracker``.
        """
        now = time.time()

        # cooldown check
        elapsed = now - self._last_drink_time
        if elapsed < self.cooldown_seconds:
            remaining = int(self.cooldown_seconds - elapsed)
            return False, f"再等等哦～ "

        # daily cap check
        if today_cups >= self.daily_max_cups:
            return False, "今天喝够啦！"

        return True, ""

    # ── record ──────────────────────────────────────────────────

    def record(self) -> None:
        """Mark a successful drink — only updates the cooldown timestamp.

        Daily cup counting is handled by ``DailyTracker.record()``.
        """
        self._last_drink_time = time.time()

    @property
    def remaining_cooldown(self) -> float:
        elapsed = time.time() - self._last_drink_time
        return max(0.0, self.cooldown_seconds - elapsed)

    # ── serialization ───────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize mutable state. Settings live in user_config."""
        return {
            "last_drink_time": self._last_drink_time,
        }

    @classmethod
    def from_dict(cls, d: dict, *, cooldown_seconds: int = 300, daily_max_cups: int = 15) -> "AntiCheat":
        """Restore from dict. Settings must be passed separately from user_config."""
        ac = cls(cooldown_seconds=cooldown_seconds, daily_max_cups=daily_max_cups)
        ac._last_drink_time = float(d.get("last_drink_time", 0.0))
        return ac
