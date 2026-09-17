from datetime import date

import pytest
from pydantic import ValidationError

from weekly_report.models import (
    DayLog, Obstacle, PlannedActivity, ProjectStatus, Report,
)

LUNES = date(2026, 9, 14)


def report(**cambios) -> Report:
    base = dict(
        author="Camila",
        week_start=LUNES,
        overall_status="en_curso",
        goals_done=1,
        goals_total=2,
        focus="Pipeline",
        summary="Resumen.",
        projects=[
            ProjectStatus(
                project="PIPE", name="Ingesta", status="en_curso",
                progress=50, milestone="Hito",
            )
        ],
    )
    return Report(**(base | cambios))


def test_la_semana_tiene_que_empezar_en_lunes():
    with pytest.raises(ValidationError, match="debe ser lunes"):
        report(week_start=date(2026, 9, 15))


def test_no_puedes_cerrar_mas_objetivos_de_los_que_te_pusiste():
    with pytest.raises(ValidationError, match="mayor que el total"):
        report(goals_done=3, goals_total=2)


def test_un_dia_de_otra_semana_no_pasa():
    otro_dia = DayLog(day=date(2026, 9, 21), project="PIPE", summary="x",
                      status="cumplido")

    with pytest.raises(ValidationError, match="no es de la semana"):
        report(days=[otro_dia])


def test_el_cronograma_va_en_la_semana_siguiente():
    esta_semana = PlannedActivity(project="PIPE", title="x", kind="critico",
                                  days=[date(2026, 9, 16)])

    with pytest.raises(ValidationError, match="fuera de la semana siguiente"):
        report(plan=[esta_semana])


def test_no_puedes_etiquetar_un_proyecto_que_no_esta_en_la_tabla():
    ajeno = DayLog(day=LUNES, project="FANTASMA", summary="x", status="cumplido")

    with pytest.raises(ValidationError, match="FANTASMA"):
        report(days=[ajeno])


def test_los_bloqueos_activos_se_ordenan_por_impacto():
    obstaculos = [
        Obstacle(project="PIPE", title="bajo", impact="bajo", owner="Yo",
                 need="x", blocking=True),
        Obstacle(project="PIPE", title="alto", impact="alto", owner="Yo",
                 need="x", blocking=True),
        Obstacle(project="PIPE", title="no bloquea", impact="alto", owner="Yo",
                 need="x"),
    ]

    activos = report(obstacles=obstaculos).active_blockers

    assert [o.title for o in activos] == ["alto", "bajo"]


def test_las_fechas_derivadas_se_calculan_solas():
    r = report()

    assert (r.week_number, r.week_end) == (38, date(2026, 9, 18))
    assert (r.next_week_start, r.next_week_number) == (date(2026, 9, 21), 39)


def test_maximo_cuatro_logros():
    with pytest.raises(ValidationError):
        report(achievements=[{"project": "PIPE", "title": f"{i}", "result": "x"}
                             for i in range(5)])
