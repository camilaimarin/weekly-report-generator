from datetime import date

from factories import TZ, activity, cache_with

from weekly_report.aggregate import summarize
from weekly_report.assemble import assemble_report
from weekly_report.config import Config
from weekly_report.llm import (
    AchievementDraft, CarryDraft, DayDraft, PlanDraft, ProjectDraft, WeekDraft,
)
from weekly_report.models import Metric, ProjectStatus, Report

LUNES = date(2026, 9, 14)
JUEVES = date(2026, 9, 17)
MIERCOLES = date(2026, 9, 16)


def config() -> Config:
    return Config(author="Camila", role="Ingeniería", emails=["c@example.com"])


def draft(**cambios) -> WeekDraft:
    base = dict(
        focus="Clústeres",
        focus_context="Contexto.",
        summary="Resumen del modelo.",
        projects=[],
        achievements=[AchievementDraft(project="PIPE", title="Logro", result="R")],
        days=[DayDraft(day=LUNES, project="PIPE", summary="Lo del lunes")],
    )
    return WeekDraft(**(base | cambios))


def test_se_arma_un_reporte_valido_sin_preguntar_nada(semana):
    stats = summarize(semana, TZ)

    report = assemble_report(draft(), stats, config(), [])

    assert report.summary == "Resumen del modelo."
    assert [p.project for p in report.projects] == ["PIPE", "AI"]
    assert report.days[0].summary == "Lo del lunes"


def test_los_dias_traen_sus_refs_para_rastrear(semana):
    stats = summarize(semana, TZ)

    report = assemble_report(draft(), stats, config(), [])

    assert report.days[0].refs == ["a1", "a2"]


def test_lo_que_no_se_sabe_queda_en_blanco_no_inventado(semana):
    stats = summarize(semana, TZ)

    report = assemble_report(draft(), stats, config(), [])

    assert (report.goals_done, report.goals_total) == (0, 0)
    assert report.overall_status == "en_curso"
    assert report.obstacles == []
    assert report.plan == []
    assert report.notes == []


def test_los_proyectos_heredan_lo_de_la_semana_pasada(semana):
    stats = summarize(semana, TZ)
    anterior = Report(
        author="Camila", week_start=date(2026, 9, 7), overall_status="en_curso",
        goals_done=1, goals_total=1, focus="x", summary="x",
        projects=[
            ProjectStatus(project="PIPE", name="Ingesta v2", status="en_riesgo",
                          progress=60, milestone="Lo viejo",
                          next_milestone="Pruebas E2E"),
        ],
    )

    report = assemble_report(draft(), stats, config(), [], anterior)
    pipe, ai = report.projects

    assert pipe.name == "Ingesta v2"
    assert (pipe.status, pipe.progress) == ("en_riesgo", 60)
    assert pipe.milestone == "Pruebas E2E"
    assert (ai.name, ai.progress) == ("AI", None)


def test_un_logro_de_un_proyecto_que_no_existe_no_entra(semana):
    stats = summarize(semana, TZ)
    inventado = draft(
        achievements=[AchievementDraft(project="FANTASMA", title="t", result="r")]
    )

    assert assemble_report(inventado, stats, config(), []).achievements == []


def test_un_dia_sin_commits_no_entra_aunque_el_modelo_lo_redacte(semana):
    stats = summarize(semana, TZ)
    con_miercoles = draft(
        days=[DayDraft(day=MIERCOLES, project="PIPE", summary="Sin commits")]
    )

    assert assemble_report(con_miercoles, stats, config(), []).days == []


def test_las_metricas_llegan_tal_cual(semana):
    stats = summarize(semana, TZ)
    metrics = [Metric(label="Commits", value=3, previous=143)]

    report = assemble_report(draft(), stats, config(), metrics)

    assert report.metrics == metrics


def test_rearmar_incorpora_los_dias_nuevos(semana):
    stats = summarize(semana, TZ)
    con_viernes = cache_with(*semana.activities, activity(day=18, ref="a4"))
    stats_viernes = summarize(con_viernes, TZ)
    nuevo_draft = draft(days=[
        DayDraft(day=LUNES, project="PIPE", summary="Lo del lunes"),
        DayDraft(day=date(2026, 9, 18), project="PIPE", summary="Lo del viernes"),
    ])

    antes = assemble_report(draft(), stats, config(), [])
    despues = assemble_report(nuevo_draft, stats_viernes, config(), [])

    assert len(antes.days) == 1
    assert [d.day.day for d in despues.days] == [14, 18]


def test_el_plan_se_convierte_a_fechas_reales(semana):
    stats = summarize(semana, TZ)
    con_plan = draft(plan=[
        PlanDraft(project="PIPE", title="Pruebas E2E", kind="critico",
                  weekdays=[1, 2]),
    ])

    plan = assemble_report(con_plan, stats, config(), []).plan[0]

    assert plan.days == [date(2026, 9, 21), date(2026, 9, 22)]


def test_un_dia_de_la_semana_imposible_se_descarta(semana):
    stats = summarize(semana, TZ)
    con_basura = draft(plan=[
        PlanDraft(project="PIPE", title="Válida", kind="critico",
                  weekdays=[0, 3, 99]),
        PlanDraft(project="PIPE", title="Toda mal", kind="critico",
                  weekdays=[0, 42]),
    ])

    plan = assemble_report(con_basura, stats, config(), []).plan

    assert [p.title for p in plan] == ["Válida"]
    assert plan[0].days == [date(2026, 9, 23)]


def test_el_arrastre_de_un_proyecto_que_no_existe_no_entra(semana):
    stats = summarize(semana, TZ)
    con_basura = draft(carry_over=[
        CarryDraft(project="FANTASMA", title="t", remaining="r"),
        CarryDraft(project="PIPE", title="Real", remaining="falta"),
    ])

    carry = assemble_report(con_basura, stats, config(), []).carry_over

    assert [c.title for c in carry] == ["Real"]


def test_el_hito_lo_redacta_el_modelo(semana):
    stats = summarize(semana, TZ)
    con_hitos = draft(projects=[
        ProjectDraft(project="PIPE", milestone="v1.5.4 publicada",
                     next_milestone="Pruebas E2E"),
    ])

    pipe = assemble_report(con_hitos, stats, config(), []).projects[0]

    assert pipe.milestone == "v1.5.4 publicada"
    assert pipe.next_milestone == "Pruebas E2E"


def test_sin_hito_del_modelo_se_usa_el_que_quedo_pendiente(semana):
    stats = summarize(semana, TZ)
    anterior = Report(
        author="Camila", week_start=date(2026, 9, 7), overall_status="en_curso",
        goals_done=0, goals_total=0, focus="x", summary="x",
        projects=[ProjectStatus(project="PIPE", name="Ingesta", status="en_curso",
                                progress=50, milestone="Viejo",
                                next_milestone="Lo prometido")],
    )

    pipe = assemble_report(draft(), stats, config(), [], anterior).projects[0]

    assert pipe.milestone == "Lo prometido"
