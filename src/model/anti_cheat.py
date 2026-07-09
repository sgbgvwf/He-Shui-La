"""Anti-cheat: cooldown timer between drinks."""

import time


class AntiCheat:
    """Validates drink actions with a configurable cooldown."""

    def __init__(self, cooldown_seconds: int = 300, daily_max_cups: int = 15) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.daily_max_cups = daily_max_cups
        self._last_drink_time: float = 0.0
        self._today_cups: int = 0
        self._last_date: str = ""

    # ── validation ──────────────────────────────────────────────

    def can_drink(self) -> tuple[bool, str]:
        """Return (allowed, reason)."""
        now = time.time()
        today = time.strftime("%Y-%m-%d", time.localtime(now))

        # cross-day reset
        if today != self._last_date:
            self._today_cups = 0
            self._last_date = today

        # cooldown check
        elapsed = now - self._last_drink_time
        if elapsed < self.cooldown_seconds:
            remaining = int(self.cooldown_seconds - elapsed)
            return False, f"再等等哦～ "

        # daily cap check
        if self._today_cups >= self.daily_max_cups:
            return False, "今天喝够啦！"

        return True, ""

    # ── record ──────────────────────────────────────────────────

    def record(self) -> None:
        """Mark a successful drink."""
        now = time.time()
        today = time.strftime("%Y-%m-%d", time.localtime(now))

        if today != self._last_date:
            self._today_cups = 0
            self._last_date = today

        self._last_drink_time = now
        self._today_cups += 1

    @property
    def today_cups(self) -> int:
        return self._today_cups

    @property
    def remaining_cooldown(self) -> float:
        elapsed = time.time() - self._last_drink_time
        return max(0.0, self.cooldown_seconds - elapsed)

    # ── serialization ───────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize mutable state. Settings (cooldown, daily_max) live in user_config."""
        return {
            "last_drink_time": self._last_drink_time,
            "today_cups": self._today_cups,
            "last_date": self._last_date,
        }

    @classmethod
    def from_dict(cls, d: dict, *, cooldown_seconds: int = 300, daily_max_cups: int = 15) -> "AntiCheat":
        """Restore from dict. Settings must be passed separately from user_config."""
        ac = cls(cooldown_seconds=cooldown_seconds, daily_max_cups=daily_max_cups)
        ac._last_drink_time = float(d.get("last_drink_time", 0.0))
        ac._today_cups = int(d.get("today_cups", 0))
        ac._last_date = str(d.get("last_date", ""))
        return ac
