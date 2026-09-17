from datetime import datetime
from zoneinfo import ZoneInfo

from weekly_report.cache import WeekCache
from weekly_report.models import Activity
from weekly_report.sources.base import Source

TZ = ZoneInfo("America/Mexico_City")
LUNES = datetime(2026, 9, 14, tzinfo=TZ).date()


class FakeSource(Source):
    def __init__(self, name: str, activities: list[Activity]):
        self.name = name
        self.activities = activities
        self.calls = 0

    def collect(self, start: datetime, end: datetime) -> list[Activity]:
        self.calls += 1
        return [a for a in self.activities if start <= a.timestamp < end]


def activity(
    day: int = 14,
    hour: int = 10,
    project: str | None = "PIPE",
    ref: str = "abc",
    title: str = "un commit",
    tz: ZoneInfo = TZ,
    **extra: int,
) -> Activity:
    return Activity(
        source="git_local",
        project=project,
        timestamp=datetime(2026, 9, day, hour, tzinfo=tz),
        title=title,
        kind="commit",
        ref=ref,
        extra=extra or {"lines_added": 10, "lines_deleted": 2, "files_changed": 1},
    )


def cache_with(*activities: Activity, week_start=LUNES) -> WeekCache:
    return WeekCache(
        week_start=week_start,
        collected_at=datetime(2026, 9, 18, 9, tzinfo=TZ),
        activities=sorted(activities, key=lambda a: a.timestamp),
    )


