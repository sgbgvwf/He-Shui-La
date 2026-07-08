"""Tests for Companion model."""

import pytest
from src.model.companion import Companion


class TestCompanion:
    def test_initial_state(self):
        c = Companion()
        assert c.name == "小水滴"
        assert c.hydration == 100.0
        assert c.exp == 0
        assert c.level == 1
        assert c.evolution_stage == "形态A"

    def test_drink_increases_hydration_and_exp(self):
        c = Companion()
        result = c.drink()
        assert c.hydration == 100.0  # capped at 100
        assert c.exp == 10
        assert result["exp_gained"] == 10
        assert result["leveled_up"] is False

    def test_drink_below_full(self):
        c = Companion()
        c._hydration = 50.0
        c.drink()
        assert c.hydration == 70.0

    def test_hydration_capped_at_100(self):
        c = Companion()
        c._hydration = 95.0
        c.drink()
        assert c.hydration == 100.0

    def test_tick_decays_hydration(self):
        c = Companion()
        c.tick()
        assert c.hydration == 99.0

    def test_tick_floor_at_zero(self):
        c = Companion()
        c._hydration = 0.0
        c.tick()
        assert c.hydration == 0.0

    def test_level_up(self):
        c = Companion()
        c._exp = 95
        result = c.drink()  # exp becomes 105, level should become 2
        assert c.exp == 105
        assert c.level == 2
        assert result["leveled_up"] is True
        assert result["new_level"] == 2

    def test_evolution_stage_maps_to_level(self):
        c = Companion()
        assert c.evolution_stage == "形态A"
        c._level = 2
        assert c.evolution_stage == "形态B"
        c._level = 5
        assert c.evolution_stage == "形态E"

    def test_is_hydrated(self):
        c = Companion()
        assert c.is_hydrated is True
        c._hydration = 15
        assert c.is_hydrated is False

    def test_to_dict_and_from_dict(self):
        c = Companion(name="测试水滴")
        c._hydration = 80.0
        c._exp = 50
        c._level = 2
        d = c.to_dict()
        restored = Companion.from_dict(d)
        assert restored.name == "测试水滴"
        assert restored.hydration == 80.0
        assert restored.exp == 50
        assert restored.level == 2
