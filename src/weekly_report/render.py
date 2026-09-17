from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from weekly_report.models import Metric, Report

TEMPLATES_DIR = Path(__file__).parent / "templates"
OUTPUT_DIR = Path("output")

MESES = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]

VERDE = "#1E7B45"
AMBAR = "#C77700"
ROJO = "#B3261E"
GRIS = "#667085"

STATUS = {
    "en_curso": ("En curso", VERDE),
    "completado": ("Completado", VERDE),
    "en_riesgo": ("En riesgo", AMBAR),
    "detenido": ("Detenido", ROJO),
    "bloqueado": ("Bloqueado", ROJO),
}

IMPACTO = {
    "alto": ("Alto", ROJO),
    "medio": ("Medio", AMBAR),
    "bajo": ("Bajo", VERDE),
}


def status_label(code: str) -> str:
    return STATUS[code][0]


def status_color(code: str) -> str:
    return STATUS[code][1]


def impact_label(code: str) -> str:
    return IMPACTO[code][0]


def impact_color(code: str) -> str:
    return IMPACTO[code][1]


def format_number(value: float) -> str:
    if value == int(value):
        return f"{int(value):,}"
    return f"{value:,.1f}"


def metric_value(metric: Metric) -> str:
    text = format_number(metric.value)
    if metric.target is not None:
        return f"{text} / {format_number(metric.target)}"
    if metric.unit:
        return f"{text} {metric.unit}"
    return text


def change_text(metric: Metric) -> str:
    diff = metric.value - metric.previous
    if diff == 0:
        return "estable"
    sign = "+" if diff > 0 else "−"
    if metric.unit == "%":
        return f"{sign}{format_number(abs(diff))} pts"
    if metric.previous == 0:
        return f"{sign}{format_number(abs(diff))} {metric.unit}".strip()
    return f"{sign}{format_number(round(abs(diff / metric.previous * 100)))} %"


def change_color(metric: Metric) -> str:
    diff = metric.value - metric.previous
    if diff == 0 or metric.better is None:
        return GRIS
    improved = (diff > 0) if metric.better == "sube" else (diff < 0)
    return VERDE if improved else ROJO


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
    env.globals["impact_label"] = impact_label
    env.globals["impact_color"] = impact_color
    env.globals["metric_value"] = metric_value
    env.globals["change_text"] = change_text
    env.globals["change_color"] = change_color
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
