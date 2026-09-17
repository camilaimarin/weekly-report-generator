import re
from datetime import date, timedelta

from weekly_report.aggregate import WeekStats
from weekly_report.config import Config
from weekly_report.formats import format_day, parse_number
from weekly_report.llm import WeekDraft
from weekly_report.models import (
    Achievement, CarryOver, DayLog, Metric, Obstacle, PlannedActivity,
    ProjectStatus, Report,
)

ESTADO_SEMANA = [
    ("en_curso", "En curso"),
    ("en_riesgo", "En riesgo"),
    ("bloqueado", "Bloqueado"),
]

ESTADO_PROYECTO = [
    ("en_curso", "En curso"),
    ("en_riesgo", "En riesgo"),
    ("detenido", "Detenido"),
    ("completado", "Completado"),
]

SEMAFORO = [
    ("cumplido", "Cumplido"),
    ("parcial", "Parcial"),
    ("bloqueado", "No avanzó"),
]

IMPACTO = [
    ("alto", "Alto"),
    ("medio", "Medio"),
    ("bajo", "Bajo"),
]

TIPO_PLAN = [
    ("critico", "Crítico / compromiso"),
    ("planificado", "Trabajo planificado"),
    ("producto", "Producto / ceremonias"),
]


def ask(pregunta: str, default: str = "", show_default: bool = True) -> str:
    sufijo = f" [{default}]" if default and show_default else ""
    return input(f"\n{pregunta}{sufijo}\n> ").strip() or default


def ask_int(pregunta: str, default: int, maximo: int | None = None) -> int:
    while True:
        raw = ask(pregunta, str(default))
        try:
            value = int(parse_number(raw))
        except ValueError:
            print("  Escribe un número.")
            continue
        if value < 0 or (maximo is not None and value > maximo):
            print(f"  Tiene que estar entre 0 y {maximo if maximo else '∞'}.")
            continue
        return value


def ask_percent(pregunta: str) -> int | None:
    while True:
        raw = ask(f"{pregunta} (Enter si no aplica)")
        if not raw:
            return None
        try:
            value = int(parse_number(raw))
        except ValueError:
            print("  Escribe un número o Enter.")
            continue
        if 0 <= value <= 100:
            return value
        print("  Tiene que estar entre 0 y 100.")


def ask_choice(pregunta: str, opciones: list[tuple[str, str]], default: int = 0) -> str:
    print(f"\n{pregunta}")
    for i, (_, label) in enumerate(opciones, 1):
        print(f"  {i}) {label}")
    while True:
        raw = input(f"> [{default + 1}] ").strip()
        if not raw:
            return opciones[default][0]
        if raw.isdigit() and 1 <= int(raw) <= len(opciones):
            return opciones[int(raw) - 1][0]
        print("  Escribe un número de la lista.")


def ask_yes_no(pregunta: str, default: bool = True) -> bool:
    sufijo = "S/n" if default else "s/N"
    while True:
        raw = input(f"\n{pregunta} [{sufijo}] ").strip().lower()
        if not raw:
            return default
        if raw in ("s", "si", "sí"):
            return True
        if raw in ("n", "no"):
            return False


def ask_project(projects: list[ProjectStatus], default: int = 0) -> str:
    opciones = [(p.project, f"{p.project} · {p.name}") for p in projects]
    return ask_choice("Proyecto", opciones, default)


def ask_weekdays(pregunta: str, week_start: date) -> list[date]:
    while True:
        raw = ask(f"{pregunta} (1=lun … 7=dom, ejemplo: 1,2 o 1 4)")
        try:
            numeros = sorted({int(n) for n in re.split(r"[,\s]+", raw) if n})
        except ValueError:
            print("  Escribe números del 1 al 7.")
            continue
        if not numeros or numeros[0] < 1 or numeros[-1] > 7:
            print("  Escribe al menos un número del 1 al 7.")
            continue
        return [week_start + timedelta(days=n - 1) for n in numeros]


def run_interview(
    draft: WeekDraft,
    stats: WeekStats,
    config: Config,
    metrics: list[Metric],
) -> Report:
    print(f"\n{'=' * 60}")
    print(f"Reporte de la semana del {stats.week_start}")
    print(f"{stats.commits} commits · {len(stats.by_project)} proyectos")
    print(f"{'=' * 60}")

    overall_status = ask_choice("¿Cómo cerró la semana?", ESTADO_SEMANA)
    goals_total = ask_int("¿Cuántos objetivos te pusiste?", 0)
    goals_done = ask_int("¿Cuántos cerraste?", goals_total, maximo=goals_total)

    focus = ask("Foco de la semana", draft.focus)
    focus_context = ask("Una línea de contexto", draft.focus_context)

    print(f"\nResumen propuesto:\n  {draft.summary}")
    summary = ask("Enter para aceptarlo, o escribe el tuyo", draft.summary, False)

    projects = _ask_projects(stats)
    achievements = _ask_achievements(draft, {p.project for p in projects})
    obstacles = _ask_obstacles(projects)
    carry_over = _ask_carry_over(projects)
    days = _ask_days(draft, stats, projects)
    plan = _ask_plan(projects, stats.week_start + timedelta(days=7))
    notes = _ask_notes()

    return Report(
        author=config.author,
        role=config.role,
        week_start=stats.week_start,
        overall_status=overall_status,
        goals_done=goals_done,
        goals_total=goals_total,
        focus=focus,
        focus_context=focus_context,
        summary=summary,
        projects=projects,
        achievements=achievements,
        obstacles=obstacles,
        metrics=metrics,
        carry_over=carry_over,
        days=days,
        plan=plan,
        notes=notes,
    )


def _ask_projects(stats: WeekStats) -> list[ProjectStatus]:
    projects = []
    for item in stats.by_project:
        print(f"\n--- {item.project} · {item.commits} commits ---")
        projects.append(_ask_project(item.project))
    while ask_yes_no("¿Agregar un proyecto sin commits?", False):
        code = ask("Código del proyecto (PIPE, AI...)")
        if code:
            projects.append(_ask_project(code))
    return projects


def _ask_project(code: str) -> ProjectStatus:
    return ProjectStatus(
        project=code,
        name=ask("Nombre del proyecto", code),
        status=ask_choice("Estado", ESTADO_PROYECTO),
        progress=ask_int("Avance (%)", 0, maximo=100),
        milestone=ask("Hito de esta semana"),
        next_milestone=ask("Próximo hito (Enter si no hay)") or None,
    )


def _ask_achievements(draft: WeekDraft, known: set[str]) -> list[Achievement]:
    achievements = []
    for item in draft.achievements:
        if item.project not in known:
            print(f"\n(se omite el logro de {item.project}: no está en la tabla)")
            continue
        print(f"\n[{item.project}] {item.title}")
        print(f"  {item.result}")
        if ask_yes_no("¿Lo incluyo?"):
            achievements.append(
                Achievement(
                    project=item.project,
                    title=ask("Título", item.title, False),
                    result=ask("Resultado", item.result, False),
                )
            )
    return achievements


def _ask_obstacles(projects: list[ProjectStatus]) -> list[Obstacle]:
    obstacles: list[Obstacle] = []
    while True:
        pregunta = "¿Otro obstáculo?" if obstacles else "¿Hubo algún obstáculo?"
        if not ask_yes_no(pregunta, False):
            return obstacles
        title = ask("¿Cuál es el obstáculo?")
        obstacles.append(
            Obstacle(
                project=ask_project(projects),
                title=title,
                impact=ask_choice("Impacto", IMPACTO, 1),
                owner=ask("¿De quién depende?"),
                need=ask("¿Qué necesitas, y para cuándo?"),
                blocking=ask_yes_no("¿Te está frenando ahora mismo?", False),
            )
        )


def _ask_carry_over(projects: list[ProjectStatus]) -> list[CarryOver]:
    carry_over: list[CarryOver] = []
    while True:
        pregunta = "¿Otro pendiente?" if carry_over else "¿Algo quedó a medias?"
        if not ask_yes_no(pregunta, False):
            return carry_over
        title = ask("¿Qué quedó a medias?")
        carry_over.append(
            CarryOver(
                project=ask_project(projects),
                title=title,
                progress=ask_percent("Avance (%)"),
                remaining=ask("¿Qué falta y cuándo se cierra?"),
            )
        )


def _ask_days(
    draft: WeekDraft, stats: WeekStats, projects: list[ProjectStatus]
) -> list[DayLog]:
    propuestas = {item.day: item for item in draft.days}
    days = []
    for day in stats.by_day:
        propuesta = propuestas.get(day.day)
        print(f"\n--- {format_day(day.day)} · {day.commits} commits ---")
        if propuesta:
            print(f"  {propuesta.summary}")
        summary = ask(
            "Qué pasó ese día (Enter para omitir el día)",
            propuesta.summary if propuesta else "",
            False,
        )
        if not summary:
            continue
        sugerido = _default_project(propuesta, day, projects)
        days.append(
            DayLog(
                day=day.day,
                project=ask_project(projects, sugerido),
                summary=summary,
                status=ask_choice("¿Cómo salió?", SEMAFORO),
                refs=day.refs,
            )
        )
    return days


def _ask_plan(
    projects: list[ProjectStatus], next_week_start: date
) -> list[PlannedActivity]:
    plan: list[PlannedActivity] = []
    while True:
        pregunta = "¿Otra actividad?" if plan else "¿Planeas algo para la otra semana?"
        if not ask_yes_no(pregunta, False):
            return plan
        title = ask("¿Qué vas a hacer?")
        plan.append(
            PlannedActivity(
                project=ask_project(projects),
                title=title,
                kind=ask_choice("¿De qué tipo es?", TIPO_PLAN, 1),
                days=ask_weekdays("¿Qué días?", next_week_start),
            )
        )


def _ask_notes() -> list[str]:
    notes = []
    while True:
        nota = ask("Nota o aprendizaje (Enter para terminar)")
        if not nota:
            return notes
        notes.append(nota)


def _default_project(propuesta, day, projects: list[ProjectStatus]) -> int:
    codes = [p.project for p in projects]
    for candidato in (propuesta.project if propuesta else None, day.main_project):
        if candidato in codes:
            return codes.index(candidato)
    return 0
