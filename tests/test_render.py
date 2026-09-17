import re
from datetime import date

import pytest

from weekly_report.models import (
    Achievement, CarryOver, DayLog, Metric, Obstacle, PlannedActivity, ProjectStatus,
    Report,
)
from weekly_report.render import (
    AMBAR, GRIS, ROJO, VERDE, change_color, change_text, metric_value, plan_bars,
    plan_days, render_report,
)

LUNES = date(2026, 9, 14)
L, M, X, J, V, S = [date(2026, 9, d) for d in (21, 22, 23, 24, 25, 26)]


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
            ProjectStatus(project="PIPE", name="Ingesta", status="en_curso",
                          progress=50, milestone="Hito")
        ],
    )
    return Report(**(base | cambios))


def secciones(html: str) -> list[str]:
    return re.findall(r'class="section"[^>]*>([^<]+)<', html)


def test_el_texto_del_reporte_no_puede_inyectar_html():
    html = render_report(report(summary="<script>alert(1)</script>"))

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_las_secciones_sin_datos_no_se_pintan():
    titulos = secciones(render_report(report()))

    assert titulos == ["01 · Resumen de la semana", "02 · Estado por proyecto"]


def test_las_secciones_se_numeran_sin_huecos():
    completo = report(
        achievements=[Achievement(project="PIPE", title="t", result="r")],
        obstacles=[Obstacle(project="PIPE", title="o", impact="alto", owner="Yo",
                            need="n")],
        metrics=[Metric(label="Commits", value=5)],
        carry_over=[CarryOver(project="PIPE", title="c", remaining="falta")],
        days=[DayLog(day=LUNES, project="PIPE", summary="s", status="cumplido")],
        plan=[PlannedActivity(project="PIPE", title="p", kind="critico", days=[L])],
        notes=["una nota"],
    )

    numeros = [t.split(" ·")[0] for t in secciones(render_report(completo))]

    assert numeros == [f"0{i}" for i in range(1, 10)]


def test_un_bloqueo_activo_se_anuncia_arriba():
    bloqueo = Obstacle(project="PIPE", title="permisos", impact="alto",
                       owner="Plataforma", need="acceso", blocking=True)

    html = render_report(report(obstacles=[bloqueo]))

    assert "1 bloqueo activo" in html
    assert "permisos" in html


def test_sin_bloqueos_la_caja_lo_dice():
    assert "0 bloqueos activos" in render_report(report())


def test_los_dias_contiguos_son_una_sola_barra():
    actividad = PlannedActivity(project="PIPE", title="x", kind="critico",
                                days=[L, M])
    dias = plan_days(report(plan=[actividad]))

    assert plan_bars(actividad, dias) == [(1, 2)]


def test_los_dias_sueltos_son_barras_separadas():
    actividad = PlannedActivity(project="PIPE", title="x", kind="critico",
                                days=[M, J])
    dias = plan_days(report(plan=[actividad]))

    assert plan_bars(actividad, dias) == [(2, 1), (4, 1)]


def test_el_cronograma_crece_si_planeas_en_sabado():
    actividad = PlannedActivity(project="PIPE", title="x", kind="critico", days=[S])

    dias = plan_days(report(plan=[actividad]))

    assert len(dias) == 6
    assert plan_bars(actividad, dias) == [(6, 1)]


def test_el_cronograma_siempre_tiene_de_lunes_a_viernes():
    assert plan_days(report()) == [L, M, X, J, V]


@pytest.mark.parametrize(
    "value, previous, unit, better, texto, color",
    [
        (19, 52, "min", "baja", "−63 %", VERDE),
        (91, 87, "%", "sube", "+4 pts", VERDE),
        (52, 143, "", "sube", "−64 %", ROJO),
        (9, 4, "", "baja", "+125 %", ROJO),
        (9, 4, "", None, "+125 %", GRIS),
        (9, 9, "", "sube", "estable", GRIS),
        (9, 0, "commits", "sube", "+9 commits", VERDE),
    ],
)
def test_el_cambio_se_lee_y_se_pinta_segun_que_sea_mejor(
    value, previous, unit, better, texto, color
):
    metric = Metric(label="x", value=value, previous=previous, unit=unit, better=better)

    assert change_text(metric) == texto
    assert change_color(metric) == color


def test_una_metrica_con_meta_se_lee_como_fraccion():
    assert metric_value(Metric(label="x", value=11, target=14)) == "11 / 14"


def test_una_metrica_sin_semana_anterior_no_pinta_cambio():
    html = render_report(report(metrics=[Metric(label="Commits", value=5)]))

    assert 'class="change"' not in html


def test_el_semaforo_del_dia_usa_su_color():
    dia = DayLog(day=LUNES, project="PIPE", summary="s", status="parcial")

    assert AMBAR in render_report(report(days=[dia]))
