from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel

from weekly_report.models import Activity
from weekly_report.sources.base import Source

DATA_DIR = Path("data")


class WeekCache(BaseModel):
    week_start: date
    collected_at: AwareDatetime
    activities: list[Activity]


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def week_range(week_start: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(week_start, time.min, tzinfo=tz)
    return start, start + timedelta(days=7)


def cache_path(week_start: date, data_dir: Path = DATA_DIR) -> Path:
    return data_dir / f"{week_start:%G-W%V}.json"


def collect_week(
    sources: list[Source], week_start: date, tz: ZoneInfo
) -> WeekCache:
    start, end = week_range(week_start, tz)
    seen = set()
    activities = []
    for source in sources:
        for activity in source.collect(start, end):
            key = (activity.source, activity.ref)
            if key in seen:
                continue
            seen.add(key)
            activities.append(activity)
    activities.sort(key=lambda activity: activity.timestamp)
    return WeekCache(
        week_start=week_start,
        collected_at=datetime.now(tz),
        activities=activities,
    )


def save_week(cache: WeekCache, data_dir: Path = DATA_DIR) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = cache_path(cache.week_start, data_dir)
    path.write_text(cache.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_week(week_start: date, data_dir: Path = DATA_DIR) -> WeekCache | None:
    path = cache_path(week_start, data_dir)
    if not path.exists():
        return None
    return WeekCache.model_validate_json(path.read_text(encoding="utf-8"))


def get_week(
    sources: list[Source],
    week_start: date,
    tz: ZoneInfo,
    data_dir: Path = DATA_DIR,
    refresh: bool = False,
) -> WeekCache:
    if not refresh:
        cached = load_week(week_start, data_dir)
        if cached is not None:
            return cached
    cache = collect_week(sources, week_start, tz)
    save_week(cache, data_dir)
    return cache
