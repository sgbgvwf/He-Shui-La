"""Achievement system — sticker-style milestone tracking (placeholder)."""

from dataclasses import dataclass
from enum import Enum


class ConditionType(Enum):
    TOTAL_CUPS = "total_cups"
    STREAK_DAYS = "streak_days"
    LEVEL_REACHED = "level_reached"


@dataclass
class AchievementDef:
    """Definition of one achievement.  Thresholds are placeholder values."""
    id: str
    name: str
    description: str
    condition_type: ConditionType
    threshold: int


# ── placeholder achievement list (5 entries) ─────────────────────

PLACEHOLDER_ACHIEVEMENTS: list[AchievementDef] = [
    AchievementDef("a1", "初次喝水", "完成第一次喝水记录", ConditionType.TOTAL_CUPS, 1),
    AchievementDef("a2", "小有成就", "累计喝水 10 杯", ConditionType.TOTAL_CUPS, 10),
    AchievementDef("a3", "坚持不懈", "连续喝水 3 天", ConditionType.STREAK_DAYS, 3),
    AchievementDef("a4", "成长之星", "伙伴达到等级 3", ConditionType.LEVEL_REACHED, 3),
    AchievementDef("a5", "喝水达人", "累计喝水 100 杯", ConditionType.TOTAL_CUPS, 100),
]


class AchievementManager:
    """Tracks unlocked achievements and checks conditions.

    Call ``check()`` after each drink — it returns newly-unlocked entries
    so the ViewModel can show a toast / animation.
    """

    def __init__(
        self,
        definitions: list[AchievementDef] | None = None,
        unlocked: set[str] | None = None,
        total_cups: int = 0,
    ) -> None:
        self._defs: dict[str, AchievementDef] = {}
        for d in (definitions or PLACEHOLDER_ACHIEVEMENTS):
            self._defs[d.id] = d
        self._unlocked: set[str] = unlocked or set()
        self.total_cups = total_cups

    # ── read ─────────────────────────────────────────────────────

    @property
    def all_definitions(self) -> list[AchievementDef]:
        return list(self._defs.values())

    @property
    def unlocked_ids(self) -> set[str]:
        return self._unlocked

    def is_unlocked(self, aid: str) -> bool:
        return aid in self._unlocked

    # ── check ────────────────────────────────────────────────────

    def check(
        self,
        companion,
        daily_tracker,
    ) -> list[AchievementDef]:
        """Evaluate all locked achievements.  Returns newly-unlocked list."""
        newly: list[AchievementDef] = []
        for ad in self._defs.values():
            if ad.id in self._unlocked:
                continue
            if self._condition_met(ad, companion, daily_tracker):
                self._unlocked.add(ad.id)
                newly.append(ad)
        return newly

    def _condition_met(self, ad: AchievementDef, companion, daily_tracker) -> bool:
        if ad.condition_type == ConditionType.TOTAL_CUPS:
            return self.total_cups >= ad.threshold
        if ad.condition_type == ConditionType.STREAK_DAYS:
            return daily_tracker.streak_days >= ad.threshold
        if ad.condition_type == ConditionType.LEVEL_REACHED:
            return companion.level >= ad.threshold
        return False

    # ── serialization ────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "unlocked": sorted(self._unlocked),
            "total_cups": self.total_cups,
        }

    @classmethod
    def from_dict(
        cls,
        d: dict,
        definitions: list[AchievementDef] | None = None,
    ) -> "AchievementManager":
        return cls(
            definitions=definitions,
            unlocked=set(d.get("unlocked", [])),
            total_cups=int(d.get("total_cups", 0)),
        )
