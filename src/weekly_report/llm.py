import re
from datetime import date

import ollama
from pydantic import BaseModel, Field

from weekly_report.aggregate import WeekStats
from weekly_report.cache import WeekCache

MAX_COMMITS_POR_DIA = 25

SISTEMA = """\
Redactas el reporte semanal de {author} ({role}).

Reglas:
- Escribes en español de México, claro y directo, sin adjetivos de relleno.
- Solo puedes usar los hechos que te doy. Si algo no está en los commits, no existe.
- No inventes números, porcentajes ni fechas: los números ya están calculados aparte.
- Usa los códigos de proyecto tal como aparecen (PIPE, AI...), nunca otros.
- Describe resultados para alguien que no lee código, no nombres de archivos."""

INSTRUCCIONES = """\
Escribe, en JSON:
- focus: el tema que dominó la semana, en menos de 6 palabras.
- focus_context: una línea que explique ese foco.
- summary: 3 o 4 frases sobre qué avanzó y qué quedó pendiente.
- achievements: máximo 4 logros, del más importante al menos. Cada uno con el
  código de proyecto, un título corto y el resultado concreto.
- days: una línea por cada día CON commits, con su fecha (AAAA-MM-DD), el
  código del proyecto principal de ese día y qué se hizo. Los días sin
  commits no se redactan: se omiten."""


class AchievementDraft(BaseModel):
    project: str
    title: str
    result: str


class DayDraft(BaseModel):
    day: date
    project: str
    summary: str


class WeekDraft(BaseModel):
    focus: str
    focus_context: str
    summary: str
    achievements: list[AchievementDraft] = Field(max_length=4)
    days: list[DayDraft]


def build_prompt(cache: WeekCache, stats: WeekStats) -> str:
    por_proyecto = ", ".join(
        f"{p.project} {p.commits}" for p in stats.by_project
    )
    partes = [
        f"Semana del {stats.week_start}.",
        f"Commits por proyecto: {por_proyecto}.",
        "",
        "Commits de la semana:",
    ]
    actividades = {activity.ref: activity for activity in cache.activities}
    for day in stats.by_day:
        if not day.commits:
            partes.append(f"\n{day.day}: sin commits.")
            continue
        partes.append(f"\n{day.day} ({day.commits} commits):")
        for ref in day.refs[:MAX_COMMITS_POR_DIA]:
            actividad = actividades[ref]
            partes.append(f"  {actividad.project}: {actividad.title}")
        extra = day.commits - MAX_COMMITS_POR_DIA
        if extra > 0:
            partes.append(f"  (y {extra} commits más)")
    partes += ["", INSTRUCCIONES]
    return "\n".join(partes)


def draft_week(
    cache: WeekCache,
    stats: WeekStats,
    author: str,
    role: str,
    model: str,
) -> WeekDraft:
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": SISTEMA.format(author=author, role=role)},
            {"role": "user", "content": build_prompt(cache, stats)},
        ],
        format=WeekDraft.model_json_schema(),
        think=False,
        options={"temperature": 0.2},
    )
    return WeekDraft.model_validate_json(response.message.content)


def review_draft(draft: WeekDraft, stats: WeekStats, cache: WeekCache) -> list[str]:
    projects = {p.project for p in stats.by_project}
    days = {day.day for day in stats.by_day}
    con_commits = {day.day for day in stats.by_day if day.commits}

    mencionados = {a.project for a in draft.achievements}
    mencionados |= {d.project for d in draft.days}

    problemas = [
        f"proyecto que no existe: {project}"
        for project in sorted(mencionados - projects)
    ]
    problemas += [
        f"día fuera de la semana: {d.day}" for d in draft.days if d.day not in days
    ]
    problemas += [
        f"día con commits que no redactó: {day}"
        for day in sorted(con_commits - {d.day for d in draft.days})
    ]

    fuente = " ".join(
        f"{a.title} {a.body or ''}" for a in cache.activities
    )
    sin_hashes = stats.model_dump_json(exclude={"by_day": {"__all__": {"refs"}}})
    known = _numbers(fuente) | _numbers(sin_hashes)
    escrito = [draft.focus, draft.focus_context, draft.summary]
    escrito += [f"{a.title} {a.result}" for a in draft.achievements]
    escrito += [d.summary for d in draft.days]
    problemas += [
        f"número que no está en los datos: {number}"
        for number in sorted(_numbers(" ".join(escrito)) - known)
    ]
    return problemas


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+", text))
