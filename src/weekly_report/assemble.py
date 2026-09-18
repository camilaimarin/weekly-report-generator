from datetime import date, timedelta

from weekly_report.aggregate import WeekStats
from weekly_report.config import Config
from weekly_report.llm import PlanDraft, ProjectDraft, WeekDraft
from weekly_report.models import (
    Achievement, CarryOver, DayLog, Metric, PlannedActivity, ProjectStatus, Report,
)

DIAS_HABILES = 5


def assemble_report(
    draft: WeekDraft,
    stats: WeekStats,
    config: Config,
    metrics: list[Metric],
    previous: Report | None = None,
) -> Report:
    anteriores = {p.project: p for p in previous.projects} if previous else {}
    hitos = {p.project: p for p in draft.projects}
    projects = [
        _project(item.project, anteriores.get(item.project), hitos.get(item.project))
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
        carry_over=[
            CarryOver(project=c.project, title=c.title, remaining=c.remaining)
            for c in draft.carry_over
            if c.project in known
        ],
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
        plan=_plan(draft.plan, known, stats.week_start + timedelta(days=7)),
    )


def _plan(
    propuestas: list[PlanDraft], known: set[str], next_week_start: date
) -> list[PlannedActivity]:
    plan = []
    for item in propuestas:
        dias = sorted({d for d in item.weekdays if 1 <= d <= DIAS_HABILES})
        if item.project not in known or not dias:
            continue
        plan.append(
            PlannedActivity(
                project=item.project,
                title=item.title,
                kind=item.kind,
                days=[next_week_start + timedelta(days=d - 1) for d in dias],
            )
        )
    return plan


def _project(
    code: str, antes: ProjectStatus | None, hito: ProjectDraft | None
) -> ProjectStatus:
    heredado = antes.next_milestone if antes else ""
    return ProjectStatus(
        project=code,
        name=antes.name if antes else code,
        status=antes.status if antes else "en_curso",
        progress=antes.progress if antes else None,
        milestone=(hito.milestone if hito else "") or heredado or "",
        next_milestone=(hito.next_milestone if hito else None) or None,
    )
