"""Tests for persistence layer."""

import json
import os

import pytest

from src.model.anti_cheat import AntiCheat
from src.model.companion import Companion
from src.model.persistence import (
    GAME_STATE_FILE,
    SCHEMA_VERSION,
    USER_CONFIG_FILE,
    _default_game_state,
    _default_user_config,
    ensure_data_dir,
    load_game_state,
    load_user_config,
    save_game_state,
    save_user_config,
)


class TestEnsureDataDir:
    def test_creates_nested(self, tmp_path):
        target = tmp_path / "a" / "b" / "c"
        ensure_data_dir(str(target))
        assert target.is_dir()

    def test_idempotent_on_existing(self, tmp_path):
        ensure_data_dir(str(tmp_path))
        ensure_data_dir(str(tmp_path))
        assert tmp_path.is_dir()


class TestGameStateRoundTrip:
    def test_save_load_round_trip(self, tmp_path):
        d = str(tmp_path)
        state = {
            "version": SCHEMA_VERSION,
            "companion": {"name": "测试", "hydration": 73.5, "exp": 42, "level": 2},
            "anticheat": {"last_drink_time": 123.45},
            "daily_tracker": {
                "today_cups": 3,
                "last_date": "2026-07-09",
                "streak_days": 2,
                "today_target_completed": True,
            },
        }
        save_game_state(d, state)
        loaded = load_game_state(d)
        assert loaded == state

    def test_atomic_write_no_tmp_left(self, tmp_path):
        save_game_state(str(tmp_path), _default_game_state())
        leftovers = list(tmp_path.glob("*.tmp"))
        assert leftovers == []

    def test_missing_file_returns_default(self, tmp_path):
        loaded = load_game_state(str(tmp_path))
        assert loaded == _default_game_state()

    def test_corrupt_main_falls_back_to_bak(self, tmp_path):
        d = str(tmp_path)
        # seed both files independently (save_game_state would overwrite .bak on every save)
        bak_data = _default_game_state()
        bak_data["companion"]["level"] = 7
        main_data = _default_game_state()  # level=1
        with open(os.path.join(d, GAME_STATE_FILE + ".bak"), "w", encoding="utf-8") as f:
            json.dump(bak_data, f)
        with open(os.path.join(d, GAME_STATE_FILE), "w", encoding="utf-8") as f:
            json.dump(main_data, f)
        # corrupt the main file
        main = os.path.join(d, GAME_STATE_FILE)
        with open(main, "w", encoding="utf-8") as f:
            f.write("garbage")
        loaded = load_game_state(d)
        assert loaded["companion"]["level"] == 7

    def test_corrupt_both_returns_default(self, tmp_path):
        d = str(tmp_path)
        save_game_state(d, _default_game_state())
        for name in (GAME_STATE_FILE, GAME_STATE_FILE + ".bak"):
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write("garbage")
        loaded = load_game_state(d)
        assert loaded == _default_game_state()

    def test_missing_keys_filled_from_default(self, tmp_path):
        d = str(tmp_path)
        # write a partial state
        with open(os.path.join(d, GAME_STATE_FILE), "w", encoding="utf-8") as f:
            json.dump({"version": SCHEMA_VERSION, "companion": {"level": 3}}, f)
        loaded = load_game_state(d)
        assert loaded["version"] == SCHEMA_VERSION
        assert loaded["companion"]["level"] == 3
        # missing keys filled
        assert loaded["companion"]["hydration"] == 100.0
        assert loaded["daily_tracker"]["today_cups"] == 0
        assert loaded["daily_tracker"]["streak_days"] == 0


class TestUserConfigRoundTrip:
    def test_save_load_round_trip(self, tmp_path):
        d = str(tmp_path)
        cfg = _default_user_config()
        cfg.update({
            "target_cups": 10,
            "cooldown_seconds": 120,
            "daily_max_cups": 20,
            "sound_enabled": False,
            "partner_name": "豆豆",
        })
        save_user_config(d, cfg)
        loaded = load_user_config(d)
        assert loaded == cfg

    def test_missing_file_returns_default(self, tmp_path):
        loaded = load_user_config(str(tmp_path))
        assert loaded == _default_user_config()

    def test_missing_keys_filled_from_default(self, tmp_path):
        d = str(tmp_path)
        with open(os.path.join(d, USER_CONFIG_FILE), "w", encoding="utf-8") as f:
            json.dump({"target_cups": 12}, f)
        loaded = load_user_config(d)
        assert loaded["target_cups"] == 12
        assert loaded["cooldown_seconds"] == 300


class TestModelIntegration:
    def test_companion_state_survives_save_load(self, tmp_path):
        d = str(tmp_path)
        c = Companion(name="豆豆")
        c._hydration = 42.0
        c._exp = 230
        c._level = 3
        save_game_state(d, {"version": SCHEMA_VERSION, "companion": c.to_dict(), "anticheat": {}})

        loaded = load_game_state(d)
        restored = Companion.from_dict(loaded["companion"])
        assert restored.name == "豆豆"
        assert restored.hydration == 42.0
        assert restored.exp == 230
        assert restored.level == 3

    def test_anticheat_state_survives_save_load(self, tmp_path):
        d = str(tmp_path)
        ac = AntiCheat(cooldown_seconds=300, daily_max_cups=15)
        ac.record()
        ac.record()
        save_game_state(d, {
            "version": SCHEMA_VERSION,
            "companion": {},
            "anticheat": ac.to_dict(),
            "daily_tracker": _default_game_state()["daily_tracker"],
        })

        loaded = load_game_state(d)
        restored = AntiCheat.from_dict(
            loaded["anticheat"],
            cooldown_seconds=300,
            daily_max_cups=15,
        )
        assert restored._last_drink_time == pytest.approx(ac._last_drink_time, abs=1.0)

    def test_daily_tracker_state_survives_save_load(self, tmp_path):
        from src.model.daily_tracker import DailyTracker
        d = str(tmp_path)
        dt = DailyTracker(daily_target=8)
        dt.record()  # today_cups=1, streak=1
        dt.record()  # today_cups=2, streak still 1
        save_game_state(d, {
            "version": SCHEMA_VERSION,
            "companion": {},
            "anticheat": {},
            "daily_tracker": dt.to_dict(),
        })

        loaded = load_game_state(d)
        restored = DailyTracker.from_dict(
            loaded["daily_tracker"],
            daily_target=8,
        )
        assert restored.today_cups == 2
        assert restored.streak_days == 1

    def test_backward_compat_migrates_from_anticheat(self, tmp_path):
        """Old saves without daily_tracker section should migrate."""
        d = str(tmp_path)
        # write old-format state (today_cups inside anticheat)
        with open(os.path.join(d, GAME_STATE_FILE), "w", encoding="utf-8") as f:
            json.dump({
                "version": SCHEMA_VERSION,
                "companion": {"level": 1},
                "anticheat": {
                    "last_drink_time": 999.0,
                    "today_cups": 7,
                    "last_date": "2026-07-08",
                },
            }, f)
        loaded = load_game_state(d)
        assert loaded["daily_tracker"]["today_cups"] == 7
        assert loaded["daily_tracker"]["last_date"] == "2026-07-08"
        assert loaded["daily_tracker"]["streak_days"] == 0  # conservative default
