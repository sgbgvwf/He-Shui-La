"""Achievement ViewModel — sticker collection state for the view."""

from kivy.event import EventDispatcher

from src.model.achievement import AchievementManager


class AchievementViewModel(EventDispatcher):
    """Exposes achievement cards for the sticker-collection popup."""

    def __init__(self, manager: AchievementManager, **kwargs):
        super().__init__(**kwargs)
        self.manager = manager

    @property
    def cards(self) -> list[dict]:
        """Return card list: id, name, desc, unlocked (bool)."""
        return [
            {
                "id": ad.id,
                "name": ad.name,
                "description": ad.description,
                "unlocked": self.manager.is_unlocked(ad.id),
            }
            for ad in self.manager.all_definitions
        ]

    @property
    def unlocked_count(self) -> int:
        return len(self.manager.unlocked_ids)

    @property
    def total_count(self) -> int:
        return len(self.manager.all_definitions)
