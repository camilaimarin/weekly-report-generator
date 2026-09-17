from weekly_report.aggregate import WeekStats
from weekly_report.config import Config
from weekly_report.llm import WeekDraft
from weekly_report.models import (
    Achievement, DayLog, Metric, ProjectStatus, Report,
)


def assemble_report(
    draft: WeekDraft,
    stats: WeekStats,
    config: Config,
    metrics: list[Metric],
    previous: Report | None = None,
) -> Report:
    anteriores = {p.project: p for p in previous.projects} if previous else {}
    projects = [
        _project(item.project, anteriores.get(item.project))
        for item in stats.by_project
    ]
    known = {p.project for p in projects}
    con_commits = {day.day for day in stats.by_day if day.commits}
    refs = {day.day: day.refs for day in stats.by_day}

    return Report(
        author=config.author,
        role=config.role,
        week_start=stats.week_start,
        overall_status="en_curso",
        goals_done=0,
        goals_total=0,
        focus=draft.focus,
        focus_context=draft.focus_context,
        summary=draft.summary,
        projects=projects,
        achievements=[
            Achievement(project=a.project, title=a.title, result=a.result)
            for a in draft.achievements
            if a.project in known
        ],
        metrics=metrics,
        days=[
            DayLog(
                day=d.day,
                project=d.project,
                summary=d.summary,
                status="cumplido",
                refs=refs.get(d.day, []),
            )
            for d in draft.days
            if d.project in known and d.day in con_commits
        ],
    )


def _project(code: str, antes: ProjectStatus | None) -> ProjectStatus:
    if antes is None:
        return ProjectStatus(
            project=code, name=code, status="en_curso", progress=0, milestone=""
        )
    return ProjectStatus(
        project=code,
        name=antes.name,
        status=antes.status,
        progress=antes.progress,
        milestone=antes.next_milestone or "",
    )
