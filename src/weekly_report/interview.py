from weekly_report.aggregate import WeekStats
from weekly_report.config import Config
from weekly_report.formats import format_day, parse_number
from weekly_report.llm import WeekDraft
from weekly_report.models import Achievement, DayLog, Metric, ProjectStatus, Report

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
    known = {p.project for p in projects}
    achievements = _ask_achievements(draft, known)
    days = _ask_days(draft, stats, known)

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
        metrics=metrics,
        days=days,
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


def _ask_days(
    draft: WeekDraft, stats: WeekStats, known: set[str]
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
        default_project = _default_project(propuesta, day, known)
        project = ask("Proyecto", default_project)
        days.append(
            DayLog(
                day=day.day,
                project=project,
                summary=summary,
                status=ask_choice("¿Cómo salió?", SEMAFORO),
                refs=day.refs,
            )
        )
    return days


def _default_project(propuesta, day, known: set[str]) -> str:
    if propuesta and propuesta.project in known:
        return propuesta.project
    if day.main_project in known:
        return day.main_project
    return sorted(known)[0] if known else ""
