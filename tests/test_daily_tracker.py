"""Tests for DailyTracker model."""

import time

import pytest

from src.model.daily_tracker import DailyTracker


class TestDailyTrackerInitial:
    def test_initial_state(self):
        dt = DailyTracker(daily_target=8)
        assert dt.today_cups == 0
        assert dt.streak_days == 0
        assert dt.today_target_completed is False
        assert dt.daily_target == 8

    def test_streak_bonus_zero_by_default(self):
        dt = DailyTracker()
        assert dt.streak_bonus == 0.0


class TestDailyTrackerStreakBonus:
    def test_streak_0_to_2_no_bonus(self):
        dt = DailyTracker()
        dt._streak_days = 2
        assert dt.streak_bonus == 0.0

    def test_streak_3_to_6(self):
        dt = DailyTracker()
        dt._streak_days = 3
        assert dt.streak_bonus == 0.10
        dt._streak_days = 6
        assert dt.streak_bonus == 0.10

    def test_streak_7_to_14(self):
        dt = DailyTracker()
        dt._streak_days = 7
        assert dt.streak_bonus == 0.20
        dt._streak_days = 14
        assert dt.streak_bonus == 0.20

    def test_streak_15_to_29(self):
        dt = DailyTracker()
        dt._streak_days = 15
        assert dt.streak_bonus == 0.30
        dt._streak_days = 29
        assert dt.streak_bonus == 0.30

    def test_streak_30_plus(self):
        dt = DailyTracker()
        dt._streak_days = 30
        assert dt.streak_bonus == 0.50
        dt._streak_days = 365
        assert dt.streak_bonus == 0.50


class TestDailyTrackerRecord:
    def test_record_increases_cups(self):
        dt = DailyTracker()
        result = dt.record()
        assert dt.today_cups == 1
        assert result["today_cups"] == 1

    def test_record_sets_streak_to_1_on_first_drink(self):
        dt = DailyTracker()
        result = dt.record()
        assert dt.streak_days == 1
        assert result["streak_days"] == 1

    def test_record_multiple_same_day_does_not_bump_streak(self):
        dt = DailyTracker()
        dt.record()  # streak → 1
        dt.record()  # same day, streak stays 1
        dt.record()
        assert dt.streak_days == 1
        assert dt.today_cups == 3


class TestDailyTrackerCrossDay:
    def test_reset_if_new_day_same_date_noop(self):
        dt = DailyTracker()
        dt.reset_if_new_day()  # sets _last_date for the first time
        dt.record()
        assert dt.today_cups == 1

        # second call on same day → no-op
        changed = dt.reset_if_new_day()
        assert changed is False
        assert dt.today_cups == 1  # unchanged

    def test_cross_day_resets_cups_and_target(self):
        dt = DailyTracker()
        dt._last_date = "2026-07-09"
        dt._today_cups = 5
        dt._streak_days = 3
        dt._today_target_completed = True

        dt.reset_if_new_day()  # → today is >= 2026-07-10

        assert dt.today_cups == 0
        assert dt.today_target_completed is False
        # yesterday was consecutive → streak preserved
        assert dt.streak_days == 3

    def test_cross_day_then_record_bumps_streak(self):
        dt = DailyTracker()
        dt._last_date = "2026-07-09"
        dt._today_cups = 1
        dt._streak_days = 3

        dt.reset_if_new_day()  # consecutive → streak stays 3
        assert dt.streak_days == 3
        dt.record()            # first drink of new day → streak → 4
        assert dt.streak_days == 4
        assert dt.today_cups == 1

    def test_streak_resets_on_gap(self):
        dt = DailyTracker()
        dt._last_date = "2026-07-08"  # day before yesterday
        dt._today_cups = 3
        dt._streak_days = 5
        dt._today_target_completed = True

        dt.reset_if_new_day()  # → today is 2026-07-10, gap detected

        assert dt.streak_days == 0
        assert dt.today_cups == 0
        assert dt.today_target_completed is False

        # first drink after gap → streak restarts at 1
        dt.record()
        assert dt.streak_days == 1

    def test_first_day_ever_streak_starts_at_1(self):
        dt = DailyTracker()
        # no _last_date set; streak should be 0
        dt.record()
        assert dt.streak_days == 1


class TestDailyTrackerTarget:
    def test_target_completion_triggers_at_threshold(self):
        dt = DailyTracker(daily_target=3)
        dt.record()  # 1/3
        dt.record()  # 2/3
        result = dt.record()  # 3/3
        assert dt.today_target_completed is True
        assert result["target_just_completed"] is True

    def test_target_completion_is_one_shot(self):
        dt = DailyTracker(daily_target=2)
        dt.record()           # 1/2
        result1 = dt.record()  # 2/2 → triggered
        assert result1["target_just_completed"] is True
        result2 = dt.record()  # 3/2 → not triggered again
        assert result2["target_just_completed"] is False

    def test_target_does_not_trigger_when_already_completed_from_load(self):
        """If state was loaded with target already completed, record() should not re-trigger."""
        dt = DailyTracker(daily_target=2)
        dt._today_target_completed = True
        dt._today_cups = 5
        result = dt.record()
        assert result["target_just_completed"] is False

    def test_target_resets_across_days(self):
        dt = DailyTracker(daily_target=2)
        dt.record()
        dt.record()  # 2/2 → completed
        assert dt.today_target_completed is True

        dt._last_date = "2026-07-09"
        dt.reset_if_new_day()  # cross-day
        assert dt.today_target_completed is False

        result = dt.record()  # 1/2 on new day
        assert result["target_just_completed"] is False  # not reached yet

    def test_check_target_completed(self):
        dt = DailyTracker(daily_target=1)
        assert dt.check_target_completed() is False
        dt.record()  # 1/1
        assert dt.check_target_completed() is True


class TestDailyTrackerSerialization:
    def test_to_dict(self):
        dt = DailyTracker(daily_target=5)
        dt._today_cups = 3
        dt._last_date = "2026-07-10"
        dt._streak_days = 2
        dt._today_target_completed = True
        d = dt.to_dict()
        assert d["today_cups"] == 3
        assert d["last_date"] == "2026-07-10"
        assert d["streak_days"] == 2
        assert d["today_target_completed"] is True

    def test_from_dict(self):
        d = {
            "today_cups": 5,
            "last_date": "2026-07-09",
            "streak_days": 3,
            "today_target_completed": True,
        }
        dt = DailyTracker.from_dict(d, daily_target=8)
        assert dt.today_cups == 5
        assert dt._last_date == "2026-07-09"
        assert dt.streak_days == 3
        assert dt.today_target_completed is True
        assert dt.daily_target == 8

    def test_round_trip(self):
        dt = DailyTracker(daily_target=8)
        dt._today_cups = 7
        dt._last_date = "2026-07-10"
        dt._streak_days = 5
        dt._today_target_completed = True
        restored = DailyTracker.from_dict(dt.to_dict(), daily_target=8)
        assert restored.today_cups == 7
        assert restored.streak_days == 5
        assert restored._last_date == "2026-07-10"
        assert restored.today_target_completed is True

    def test_from_dict_empty(self):
        dt = DailyTracker.from_dict({}, daily_target=8)
        assert dt.today_cups == 0
        assert dt._last_date == ""
        assert dt.streak_days == 0
        assert dt.today_target_completed is False
        assert dt.daily_target == 8
