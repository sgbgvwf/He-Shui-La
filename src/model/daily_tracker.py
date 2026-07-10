"""Daily drinking tracker — cups, streak, and target completion."""

import time


class DailyTracker:
    """Tracks per-day drinking stats: cup count, streak, target checks.

    Responsibilities:
      - Cup counting with cross-day reset
      - Streak tracking (consecutive days with at least one drink)
      - Daily target completion detection (one-shot reward per day)

    Caller must invoke ``reset_if_new_day()`` before ``record()``.
    """

    def __init__(self, daily_target: int = 8) -> None:
        self.daily_target = daily_target
        self._today_cups: int = 0
        self._last_date: str = ""                 # "YYYY-MM-DD"
        self._streak_days: int = 0
        self._today_target_completed: bool = False

    # ── properties ──────────────────────────────────────────────

    @property
    def today_cups(self) -> int:
        return self._today_cups

    @property
    def streak_days(self) -> int:
        return self._streak_days

    @property
    def today_target_completed(self) -> bool:
        return self._today_target_completed

    # ── cross-day ──────────────────────────────────────────────

    def reset_if_new_day(self) -> bool:
        """If the date has changed, reset daily counters and update streak.

        Streak logic:
          - First-ever day (no prior ``_last_date``) → streak stays 0; record() sets to 1
          - Same date → no-op
          - Consecutive day (yesterday matched) → streak persists, record() will +1
          - Gap (more than 1 day skipped) → streak resets to 0, record() starts over at 1

        Returns True when a cross-day reset was performed.
        """
        now = time.time()
        today = time.strftime("%Y-%m-%d", time.localtime(now))

        if today == self._last_date:
            return False

        if self._last_date != "":
            yesterday_sec = now - 86400
            yesterday = time.strftime("%Y-%m-%d", time.localtime(yesterday_sec))
            if self._last_date != yesterday:
                self._streak_days = 0  # gap → reset

        self._today_cups = 0
        self._today_target_completed = False
        self._last_date = today
        return True

    # ── record ──────────────────────────────────────────────────

    def record(self) -> dict:
        """Record a drink. Returns info dict for ViewModel consumption.

        Caller should have already called ``reset_if_new_day()`` upstream.
        """
        was_zero = self._today_cups == 0
        self._today_cups += 1

        # first drink of the day → bump streak
        if was_zero:
            self._streak_days += 1

        result: dict = {
            "today_cups": self._today_cups,
            "streak_days": self._streak_days,
            "target_just_completed": False,
        }

        # one-shot target-completion trigger
        if not self._today_target_completed and self._today_cups >= self.daily_target:
            self._today_target_completed = True
            result["target_just_completed"] = True

        return result

    def check_target_completed(self) -> bool:
        """Query whether the daily target has been met today."""
        return self._today_target_completed

    # ── serialization ───────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize mutable state. ``daily_target`` lives in user_config."""
        return {
            "today_cups": self._today_cups,
            "last_date": self._last_date,
            "streak_days": self._streak_days,
            "today_target_completed": self._today_target_completed,
        }

    @classmethod
    def from_dict(cls, d: dict, *, daily_target: int = 8) -> "DailyTracker":
        """Restore from dict. ``daily_target`` must be passed from user_config."""
        dt = cls(daily_target=daily_target)
        dt._today_cups = int(d.get("today_cups", 0))
        dt._last_date = str(d.get("last_date", ""))
        dt._streak_days = int(d.get("streak_days", 0))
        dt._today_target_completed = bool(d.get("today_target_completed", False))
        return dt
