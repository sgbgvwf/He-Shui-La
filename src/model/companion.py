"""Companion entity — hydration, experience, and evolution."""

EVOLUTION_STAGES = {1: "形态A", 2: "形态B", 3: "形态C", 4: "形态D", 5: "形态E"}


class Companion:
    """Virtual companion driven by drinking water."""

    def __init__(self, name: str = "小水滴") -> None:
        self.name = name
        self._hydration = 100.0
        self._exp = 0
        self._level = 1

    # ── properties ──────────────────────────────────────────────

    @property
    def hydration(self) -> float:
        return self._hydration

    @property
    def exp(self) -> int:
        return self._exp

    @property
    def level(self) -> int:
        return self._level

    @property
    def evolution_stage(self) -> str:
        stage = 1
        for threshold in sorted(EVOLUTION_STAGES):
            if self._level >= threshold:
                stage = threshold
        return EVOLUTION_STAGES.get(stage, EVOLUTION_STAGES[1])

    @property
    def is_hydrated(self) -> bool:
        return self._hydration > 20

    # ── actions ─────────────────────────────────────────────────

    def drink(self) -> dict:
        """Record a drink. Returns info dict for ViewModel."""
        prev_level = self._level

        self._hydration = min(100.0, self._hydration + 20)
        self._exp += 10

        # level-up: every 100 exp → +1 level
        self._level = 1 + self._exp // 100

        return {
            "hydration": self._hydration,
            "exp_gained": 10,
            "leveled_up": self._level > prev_level,
            "new_level": self._level,
        }

    def award_exp(self, amount: int) -> dict:
        """Award bonus EXP (e.g. daily target) and recalculate level."""
        prev_level = self._level
        self._exp += amount
        self._level = 1 + self._exp // 100
        return {
            "exp_gained": amount,
            "leveled_up": self._level > prev_level,
            "new_level": self._level,
        }

    def tick(self) -> None:
        """Natural hydration decay — call every N seconds."""
        self._hydration = max(0.0, self._hydration - 1)

    # ── helpers ─────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "hydration": self._hydration,
            "exp": self._exp,
            "level": self._level,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Companion":
        c = cls(name=d.get("name", "小水滴"))
        c._hydration = d.get("hydration", 100.0)
        c._exp = d.get("exp", 0)
        c._level = d.get("level", 1)
        return c
