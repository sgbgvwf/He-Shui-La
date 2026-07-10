"""Sound manager — wraps Kivy SoundLoader with caching and graceful degradation."""

import os

from kivy.core.audio import SoundLoader


class SoundManager:
    """Loads and plays game sounds.  Missing files are silently ignored.

    ``enabled`` mirrors ``GameConfig.sound_enabled`` — set from ViewModel.
    """

    def __init__(self, sounds_dir: str, enabled: bool = True):
        self._dir = sounds_dir
        self.enabled = enabled
        self._cache: dict[str, object] = {}  # name → Sound

    # ── public ────────────────────────────────────────────────────

    def play(self, name: str) -> None:
        """Play a sound by short name (e.g. ``"drink"``).  No-op if disabled."""
        if not self.enabled:
            return
        sound = self._load(name)
        if sound is not None:
            sound.play()

    # ── internal ──────────────────────────────────────────────────

    def _load(self, name: str):
        if name in self._cache:
            return self._cache[name]
        path = os.path.join(self._dir, f"{name}.wav")
        if not os.path.exists(path):
            self._cache[name] = None   # cache the miss
            return None
        try:
            sound = SoundLoader.load(path)
        except Exception:
            sound = None
        self._cache[name] = sound
        return sound
