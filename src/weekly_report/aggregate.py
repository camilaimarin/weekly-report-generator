from collections import Counter
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from weekly_report.cache import WeekCache
from weekly_report.models import Activity, Metric

NO_PROJECT = "sin-proyecto"
WEEKDAYS = 5


class DayStats(BaseModel):
    day: date
    commits: int
    lines_added: int
    lines_deleted: int
    files_changed: int
    by_project: dict[str, int]
    refs: list[str]

    @property
    def main_project(self) -> str | None:
        if not self.by_project:
            return None
        return min(self.by_project.items(), key=lambda item: (-item[1], item[0]))[0]


class ProjectStats(BaseModel):
    project: str
    commits: int
    lines_added: int
    lines_deleted: int
    files_changed: int
    days: list[date]


class WeekStats(BaseModel):
    week_start: date
    commits: int
    lines_added: int
    lines_deleted: int
    files_changed: int
    by_day: list[DayStats]
    by_project: list[ProjectStats]

    @property
    def active_days(self) -> int:
        return sum(1 for day in self.by_day if day.commits)


def summarize(cache: WeekCache, tz: ZoneInfo) -> WeekStats:
    per_day: dict[date, list[Activity]] = {}
    per_project: dict[str, list[Activity]] = {}
    for activity in cache.activities:
        day = activity.timestamp.astimezone(tz).date()
        per_day.setdefault(day, []).append(activity)
        per_project.setdefault(activity.project or NO_PROJECT, []).append(activity)

    days = {cache.week_start + timedelta(days=i) for i in range(WEEKDAYS)}
    days |= set(per_day)

    return WeekStats(
        week_start=cache.week_start,
        commits=len(cache.activities),
        lines_added=_total(cache.activities, "lines_added"),
        lines_deleted=_total(cache.activities, "lines_deleted"),
        files_changed=_total(cache.activities, "files_changed"),
        by_day=[_day_stats(day, per_day.get(day, [])) for day in sorted(days)],
        by_project=sorted(
            (
                _project_stats(project, items, tz)
                for project, items in per_project.items()
            ),
            key=lambda stats: (-stats.commits, stats.project),
        ),
    )


def git_metrics(current: WeekStats, previous: WeekStats | None = None) -> list[Metric]:
    def before(field: str) -> float | None:
        return getattr(previous, field) if previous else None

    return [
        Metric(label="Commits", value=current.commits, previous=before("commits")),
        Metric(label="Líneas escritas", value=current.lines_added,
               previous=before("lines_added")),
        Metric(label="Archivos tocados", value=current.files_changed,
               previous=before("files_changed")),
        Metric(label="Días con commits", value=current.active_days,
               previous=before("active_days")),
    ]


def _total(activities: list[Activity], field: str) -> int:
    return sum(activity.extra.get(field, 0) for activity in activities)


def _day_stats(day: date, activities: list[Activity]) -> DayStats:
    projects = Counter(activity.project or NO_PROJECT for activity in activities)
    return DayStats(
        day=day,
        commits=len(activities),
        lines_added=_total(activities, "lines_added"),
        lines_deleted=_total(activities, "lines_deleted"),
        files_changed=_total(activities, "files_changed"),
        by_project=dict(projects.most_common()),
        refs=[activity.ref for activity in activities],
    )


def _project_stats(
    project: str, activities: list[Activity], tz: ZoneInfo
) -> ProjectStats:
    return ProjectStats(
        project=project,
        commits=len(activities),
        lines_added=_total(activities, "lines_added"),
        lines_deleted=_total(activities, "lines_deleted"),
        files_changed=_total(activities, "files_changed"),
        days=sorted(
            {activity.timestamp.astimezone(tz).date() for activity in activities}
        ),
    )
