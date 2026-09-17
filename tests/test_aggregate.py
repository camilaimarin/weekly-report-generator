from datetime import date
from zoneinfo import ZoneInfo

from conftest import activity, cache_with

from weekly_report.aggregate import NO_PROJECT, git_metrics, summarize

UTC = ZoneInfo("UTC")


def test_siempre_de_lunes_a_viernes(tz):
    stats = summarize(cache_with(), tz)

    assert [d.day.isoweekday() for d in stats.by_day] == [1, 2, 3, 4, 5]
    assert stats.commits == 0


def test_el_fin_de_semana_solo_aparece_si_hubo_trabajo(tz):
    stats = summarize(cache_with(activity(day=19)), tz)

    assert stats.by_day[-1].day == date(2026, 9, 19)
    assert len(stats.by_day) == 6


def test_el_dia_se_decide_en_la_zona_local_no_en_utc(tz):
    domingo_2330 = activity(day=21, hour=5, tz=UTC)

    stats = summarize(cache_with(domingo_2330), tz)
    dias_con_commits = [d.day for d in stats.by_day if d.commits]

    assert dias_con_commits == [date(2026, 9, 20)]
    assert stats.by_project[0].days == [date(2026, 9, 20)]


def test_el_proyecto_principal_del_dia_desempata_por_orden_alfabetico(tz):
    stats = summarize(
        cache_with(
            activity(day=14, ref="z1", project="ZETA"),
            activity(day=14, ref="a1", project="ALFA"),
        ),
        tz,
    )

    assert stats.by_day[0].main_project == "ALFA"


def test_una_actividad_sin_proyecto_no_se_pierde(tz):
    stats = summarize(cache_with(activity(project=None)), tz)

    assert stats.by_project[0].project == NO_PROJECT


def test_una_fuente_sin_lineas_suma_cero(tz):
    reunion = activity(project="PIPE", **{"asistentes": 3})

    stats = summarize(cache_with(reunion), tz)

    assert stats.commits == 1
    assert stats.lines_added == 0


def test_los_proyectos_se_ordenan_por_commits(tz, semana):
    stats = summarize(semana, tz)

    assert [p.project for p in stats.by_project] == ["PIPE", "AI"]
    assert stats.by_project[0].commits == 2


def test_las_metricas_sin_semana_anterior_no_comparan(tz, semana):
    metrics = git_metrics(summarize(semana, tz))

    assert all(m.previous is None for m in metrics)


def test_las_metricas_comparan_contra_la_semana_anterior(tz, semana):
    actual = summarize(semana, tz)
    anterior = summarize(cache_with(activity(day=7), week_start=date(2026, 9, 7)), tz)

    commits = git_metrics(actual, anterior)[0]

    assert (commits.value, commits.previous) == (3, 1)
