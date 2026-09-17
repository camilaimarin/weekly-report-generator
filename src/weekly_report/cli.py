import argparse
import os
import shlex
import subprocess
from datetime import date, timedelta
from pathlib import Path

from pydantic import ValidationError

from weekly_report.aggregate import git_metrics, summarize
from weekly_report.assemble import assemble_report
from weekly_report.cache import get_week, monday_of
from weekly_report.config import Config, build_sources, load_config
from weekly_report.interview import review_report, run_interview
from weekly_report.llm import WeekDraft, draft_week, review_draft
from weekly_report.models import Report
from weekly_report.pdf import save_pdf
from weekly_report.render import OUTPUT_DIR, render_report, save_report

VACIO = WeekDraft(focus="", focus_context="", summary="", achievements=[], days=[])


def main() -> None:
    args = _parse_args()
    try:
        _run(args)
    except (KeyboardInterrupt, EOFError):
        raise SystemExit("\nCancelado. No se guardó nada.")
    except FileNotFoundError as error:
        raise SystemExit(f"\n{error}")


def _run(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    week_start = args.week or monday_of(date.today())

    if args.render_only:
        path = _json_path(week_start)
        if not path.exists():
            raise SystemExit(
                f"\nNo hay ningún reporte capturado en {path}.\n"
                "Corre el comando sin --render-only para capturarlo."
            )
        _save(Report.model_validate_json(path.read_text()), args.pdf)
        return

    sources = build_sources(config)
    print(f"Leyendo git de {len(sources)} repositorios...")
    cache = get_week(sources, week_start, config.timezone, refresh=args.refresh)
    stats = summarize(cache, config.timezone)
    print(f"Semana {week_start:%G-W%V}: {stats.commits} commits.")

    previous = get_week(sources, week_start - timedelta(days=7), config.timezone)
    metrics = git_metrics(stats, summarize(previous, config.timezone))

    draft = VACIO if args.no_llm else _draft(cache, stats, config)
    previous = _last_report(week_start)

    path = _json_path(week_start)
    capturado = _existing(path)

    if args.entrevista:
        report = run_interview(draft, stats, config, metrics, previous)
    elif capturado:
        report = capturado.model_copy(update={"metrics": metrics})
    else:
        report = assemble_report(draft, stats, config, metrics, previous)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2))

    if not args.entrevista:
        report = _edit(path)

    for aviso in review_report(report):
        print(f"  ojo: {aviso}")
    _save(report, args.pdf)


def _existing(path: Path) -> Report | None:
    if not path.exists():
        return None
    print(f"Ya tenías capturada esta semana: se conserva {path}.")
    return Report.model_validate_json(path.read_text())


def _edit(path: Path) -> Report:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if editor:
        print(f"\nAbriendo {path} en {editor}. Guarda y cierra para continuar.")
        subprocess.run([*shlex.split(editor), str(path)])
    else:
        print(f"\nTu reporte está en {path}.")
        print("Edítalo y corre --render-only para volver a generar el HTML.")
    try:
        return Report.model_validate_json(path.read_text())
    except ValidationError as error:
        raise SystemExit(
            f"\nEl JSON quedó con algo que no cuadra:\n{error}\n"
            "Arréglalo y corre --render-only."
        )


def _draft(cache, stats, config: Config) -> WeekDraft:
    print(f"Pidiéndole el borrador a {config.model}...")
    try:
        draft = draft_week(cache, stats, config.author, config.role, config.model)
    except Exception as error:
        raise SystemExit(
            f"\nNo se pudo usar Ollama ({error}).\n"
            "Revisa que esté corriendo, o usa --no-llm para escribir tú los textos."
        )
    for problema in review_draft(draft, stats, cache):
        print(f"  ojo: {problema}")
    return draft


def _save(report: Report, pdf: bool = False) -> None:
    path = save_report(render_report(report), report.week_start)
    print(f"\nListo: {path}")
    if pdf:
        print(f"Listo: {save_pdf(path)}")


def _json_path(week_start: date) -> Path:
    return OUTPUT_DIR / f"{week_start:%G-W%V}.json"


def _last_report(week_start: date) -> Report | None:
    path = _json_path(week_start - timedelta(days=7))
    if not path.exists():
        return None
    print(f"Tomando como base tu reporte de {path.stem}.")
    return Report.model_validate_json(path.read_text())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera tu reporte semanal.")
    parser.add_argument(
        "--week",
        type=_monday,
        help="Un día de la semana a reportar (AAAA-MM-DD). Por omisión, esta semana.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Vuelve a leer git aunque ya haya caché de esa semana.",
    )
    parser.add_argument(
        "--entrevista",
        action="store_true",
        help="Captura el reporte respondiendo preguntas, en vez de editar el JSON.",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="No usa Ollama: los textos los escribes tú.",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Además del HTML, exporta el reporte a PDF.",
    )
    parser.add_argument(
        "--render-only",
        action="store_true",
        help="Vuelve a generar el HTML del reporte ya capturado, sin entrevista.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.toml"),
        help="Ruta del archivo de configuración.",
    )
    return parser.parse_args()


def _monday(text: str) -> date:
    return monday_of(date.fromisoformat(text))
