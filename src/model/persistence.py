"""Persistence layer — atomic JSON read/write with .bak fallback.

Two files are managed:
  - ``game_state.json`` : mutable runtime state (companion, anticheat)
  - ``user_config.json`` : user-tweakable settings

Atomic write pattern: write to ``<path>.tmp`` then ``os.replace`` onto the target,
followed by ``shutil.copy2`` to ``<path>.bak`` for crash recovery.

Load order: target file → ``.bak`` → default dict.
"""

from __future__ import annotations

import json
import os
import shutil


# ── file names ───────────────────────────────────────────────────────

GAME_STATE_FILE = "game_state.json"
USER_CONFIG_FILE = "user_config.json"

SCHEMA_VERSION = 1


# ── default payloads (mirror Model defaults) ─────────────────────────

def _default_game_state() -> dict:
    return {
        "version": SCHEMA_VERSION,
        "companion": {
            "name": "小水滴",
            "hydration": 100.0,
            "exp": 0,
            "level": 1,
        },
        "anticheat": {
            "last_drink_time": 0.0,
        },
        "daily_tracker": {
            "today_cups": 0,
            "last_date": "",
            "streak_days": 0,
            "today_target_completed": False,
        },
    }


def _default_user_config() -> dict:
    return {
        "version": SCHEMA_VERSION,
        # ── DailyTracker ──
        "target_cups": 8,
        "target_reward_exp": 20,
        "streak_bonus_table": [[3, 0.10], [7, 0.20], [15, 0.30], [30, 0.50]],
        # ── AntiCheat ──
        "cooldown_seconds": 300,
        "daily_max_cups": 15,
        # ── Companion ──
        "hydration_per_drink": 20.0,
        "hydration_max": 100.0,
        "hydration_low_threshold": 20.0,
        "exp_per_drink": 10,
        "exp_per_level": 100,
        "decay_per_tick": 1.0,
        # ── ViewModel ──
        "decay_interval_seconds": 3.0,
        "autosave_debounce_seconds": 2.0,
        "toast_duration_seconds": 2.5,
        # ── User-facing ──
        "sound_enabled": True,
        "partner_name": "小水滴",
    }


# ── primitives ──────────────────────────────────────────────────────

def ensure_data_dir(data_dir: str) -> None:
    """Create the data directory tree if it doesn't exist."""
    os.makedirs(data_dir, exist_ok=True)


def _save_json(path: str, payload: dict) -> None:
    """Atomic write: write to .tmp → os.replace → copy to .bak."""
    tmp = path + ".tmp"
    bak = path + ".bak"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    try:
        shutil.copy2(path, bak)
    except OSError:
        # backup best-effort; primary write already succeeded
        pass


def _load_json(path: str) -> dict | None:
    """Load JSON, falling back to .bak on missing/corrupt primary file."""
    bak = path + ".bak"
    for candidate in (path, bak):
        if not os.path.exists(candidate):
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge overlay into base; overlay values win on leaf conflict."""
    result = dict(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ── game_state ──────────────────────────────────────────────────────

def save_game_state(data_dir: str, state: dict) -> None:
    """Persist runtime state. ``state`` is written verbatim (no schema injection)."""
    ensure_data_dir(data_dir)
    path = os.path.join(data_dir, GAME_STATE_FILE)
    _save_json(path, state)


def load_game_state(data_dir: str) -> dict:
    """Return persisted state merged with defaults (recursively).

    Includes backward-compat migration for saves that pre-date the
    ``daily_tracker`` section (when ``today_cups`` lived inside ``anticheat``).
    """
    path = os.path.join(data_dir, GAME_STATE_FILE)
    loaded = _load_json(path)
    if loaded is None:
        return _default_game_state()

    merged = _deep_merge(_default_game_state(), loaded)

    # ── backward compat: migrate today_cups/last_date from anticheat → daily_tracker
    if "daily_tracker" not in loaded:
        old_ac = loaded.get("anticheat", {})
        merged["daily_tracker"]["today_cups"] = int(old_ac.get("today_cups", 0))
        merged["daily_tracker"]["last_date"] = str(old_ac.get("last_date", ""))
        # streak starts at 0 for migrated saves (conservative — won't inflate)

    return merged


# ── user_config ─────────────────────────────────────────────────────

def save_user_config(data_dir: str, config: dict) -> None:
    """Persist user settings. ``config`` is written verbatim."""
    ensure_data_dir(data_dir)
    path = os.path.join(data_dir, USER_CONFIG_FILE)
    _save_json(path, config)


def load_user_config(data_dir: str) -> dict:
    """Return persisted settings merged with defaults (recursively)."""
    path = os.path.join(data_dir, USER_CONFIG_FILE)
    loaded = _load_json(path)
    if loaded is None:
        return _default_user_config()
    return _deep_merge(_default_user_config(), loaded)
