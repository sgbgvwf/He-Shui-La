"""Tests for AntiCheat model."""

import time
import pytest
from src.model.anti_cheat import AntiCheat


class TestAntiCheat:
    def test_first_drink_allowed(self):
        ac = AntiCheat(cooldown_seconds=300)
        allowed, reason = ac.can_drink()
        assert allowed is True
        assert reason == ""

    def test_cooldown_blocks_second_drink(self):
        ac = AntiCheat(cooldown_seconds=300)
        ac.record()
        allowed, reason = ac.can_drink()
        assert allowed is False
        assert "再等等" in reason

    def test_cooldown_expires(self):
        ac = AntiCheat(cooldown_seconds=0)  # zero cooldown
        ac.record()
        allowed, reason = ac.can_drink()
        assert allowed is True

    def test_daily_max_enforced(self):
        ac = AntiCheat(cooldown_seconds=0, daily_max_cups=3)
        for _ in range(3):
            ac.record()
        allowed, reason = ac.can_drink()
        assert allowed is False
        assert "今天喝够啦" in reason

    def test_today_cups_tracks_correctly(self):
        ac = AntiCheat(cooldown_seconds=0)
        assert ac.today_cups == 0
        ac.record()
        ac.record()
        assert ac.today_cups == 2

    def test_record_updates_last_drink_time(self):
        ac = AntiCheat(cooldown_seconds=300)
        before = time.time()
        ac.record()
        assert ac._last_drink_time >= before

    def test_remaining_cooldown_decreases(self):
        ac = AntiCheat(cooldown_seconds=300)
        assert ac.remaining_cooldown == 0.0
        ac.record()
        assert ac.remaining_cooldown > 0
        assert ac.remaining_cooldown <= 300
