from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from weekly_report.models import Report

TEMPLATES_DIR = Path(__file__).parent / "templates"
OUTPUT_DIR = Path("output")

MESES = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]

STATUS = {
    "en_curso": ("En curso", "#1E7B45"),
    "completado": ("Completado", "#1E7B45"),
    "en_riesgo": ("En riesgo", "#C77700"),
    "detenido": ("Detenido", "#B3261E"),
    "bloqueado": ("Bloqueado", "#B3261E"),
}


def status_label(code: str) -> str:
    return STATUS[code][0]


def status_color(code: str) -> str:
    return STATUS[code][1]


def format_week_range(start: date, end: date) -> str:
    if start.month == end.month:
        return f"{start.day}–{end.day} {MESES[end.month - 1]} {end.year}"
    return (
        f"{start.day} {MESES[start.month - 1]} – "
        f"{end.day} {MESES[end.month - 1]} {end.year}"
    )


def _environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
    )
    env.globals["status_label"] = status_label
    env.globals["status_color"] = status_color
    env.globals["format_week_range"] = format_week_range
    return env


def render_report(report: Report) -> str:
    template = _environment().get_template("report.html.j2")
    return template.render(report=report)


def save_report(html: str, week_start: date, output_dir: Path = OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{week_start:%G-W%V}.html"
    path.write_text(html, encoding="utf-8")
    return path
