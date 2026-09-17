from datetime import date

import pytest
from factories import TZ

from weekly_report.aggregate import summarize
from weekly_report.config import Config
from weekly_report.interview import (
    ask, ask_int, ask_percent, ask_weekdays, ask_yes_no, review_report, run_interview,
)
from weekly_report.llm import AchievementDraft, DayDraft, WeekDraft
from weekly_report.models import ProjectStatus, Report

LUNES = date(2026, 9, 14)
PROXIMO_LUNES = date(2026, 9, 21)


@pytest.fixture
def responde(monkeypatch):
    def _responde(*respuestas: str):
        pendientes = iter(respuestas)
        monkeypatch.setattr("builtins.input", lambda _="": next(pendientes))

    return _responde


@pytest.fixture
def config() -> Config:
    return Config(author="Camila", role="Ingeniería", emails=["c@example.com"])


def test_enter_acepta_lo_propuesto(responde):
    responde("")

    assert ask("Foco", "Pipeline") == "Pipeline"


def test_lo_que_escribes_gana_al_default(responde):
    responde("Otra cosa")

    assert ask("Foco", "Pipeline") == "Otra cosa"


def test_un_numero_mal_escrito_se_vuelve_a_preguntar(responde):
    responde("cuatro", "4")

    assert ask_int("¿Cuántos?", 0) == 4


def test_un_numero_fuera_de_rango_se_vuelve_a_preguntar(responde):
    responde("120", "80")

    assert ask_int("Avance", 0, maximo=100) == 80


def test_el_porcentaje_puede_quedar_vacio(responde):
    responde("")

    assert ask_percent("Avance") is None


def test_el_porcentaje_acepta_coma_decimal(responde):
    responde("99,4")

    assert ask_percent("Avance") == 99


@pytest.mark.parametrize("respuesta, esperado", [("s", True), ("n", False),
                                                 ("", True), ("sí", True)])
def test_las_preguntas_de_si_o_no(responde, respuesta, esperado):
    responde(respuesta)

    assert ask_yes_no("¿Sí?") is esperado


def test_los_dias_se_escriben_con_comas_o_espacios(responde):
    responde("1,2")
    assert ask_weekdays("¿Qué días?", PROXIMO_LUNES) == [PROXIMO_LUNES,
                                                         date(2026, 9, 22)]

    responde("2 4")
    assert ask_weekdays("¿Qué días?", PROXIMO_LUNES) == [date(2026, 9, 22),
                                                         date(2026, 9, 24)]


def test_un_dia_invalido_se_vuelve_a_preguntar(responde):
    responde("9", "hola", "1")

    assert ask_weekdays("¿Qué días?", PROXIMO_LUNES) == [PROXIMO_LUNES]


def test_la_entrevista_arma_un_reporte_valido(responde, config, semana):
    stats = summarize(semana, TZ)
    draft = WeekDraft(
        focus="Clústeres",
        focus_context="Contexto.",
        summary="Resumen del modelo.",
        achievements=[AchievementDraft(project="PIPE", title="Logro", result="R")],
        days=[DayDraft(day=LUNES, project="PIPE", summary="Lo del lunes")],
    )
    responde(
        "1", "2", "1",                        # estado, objetivos, cerrados
        "", "", "",                           # foco, contexto, resumen
        "Ingesta", "1", "70", "Hito", "",     # PIPE
        "Panel", "2", "50", "Hito", "",       # AI
        "n",                                  # sin proyectos extra
        "",                                   # acepta el logro tal cual
        "n", "n",                             # sin obstáculos ni arrastre
        "", "1", "1",                         # lunes: acepta texto, proyecto, semáforo
        "", "", "", "",                       # martes a viernes: omitidos
        "s", "Pruebas E2E", "1", "1", "1,2",  # una actividad del cronograma
        "n",
        "Una nota.", "",
    )

    report = run_interview(draft, stats, config, [])

    assert report.summary == "Resumen del modelo."
    assert [p.project for p in report.projects] == ["PIPE", "AI"]
    assert [d.day for d in report.days] == [LUNES]
    assert report.days[0].refs == ["a1", "a2"]
    assert report.plan[0].days == [PROXIMO_LUNES, date(2026, 9, 22)]
    assert report.notes == ["Una nota."]


def test_un_logro_se_puede_editar_sin_reescribir_los_demas(responde, config, semana):
    stats = summarize(semana, TZ)
    draft = WeekDraft(
        focus="x", focus_context="x", summary="x",
        achievements=[AchievementDraft(project="PIPE", title="Feo", result="R")],
        days=[],
    )
    responde(
        "1", "0", "0", "", "", "",
        "Ingesta", "1", "70", "Hito", "",
        "Panel", "1", "50", "Hito", "",
        "n",
        "e", "Bonito", "",                    # editar: cambia el título, deja el resto
        "n", "n",
        "", "", "", "", "",
        "n",
        "",
    )

    report = run_interview(draft, stats, config, [])

    assert report.achievements[0].title == "Bonito"
    assert report.achievements[0].result == "R"


def test_lo_de_la_semana_pasada_se_propone(responde, config, semana):
    stats = summarize(semana, TZ)
    anterior = Report(
        author="Camila", week_start=date(2026, 9, 7), overall_status="en_curso",
        goals_done=1, goals_total=1, focus="x", summary="x",
        projects=[
            ProjectStatus(project="PIPE", name="Ingesta v2", status="en_riesgo",
                          progress=60, milestone="Lo de la semana pasada",
                          next_milestone="Pruebas E2E"),
        ],
    )
    draft = WeekDraft(focus="x", focus_context="x", summary="x", achievements=[],
                      days=[])
    responde(
        "1", "0", "0", "", "", "",
        "", "", "", "",                       # PIPE: no pregunta el nombre
        "Panel", "1", "50", "Hito", "",       # AI: no tiene base, pregunta todo
        "n", "n", "n",
        "", "", "", "", "",
        "n", "",
    )

    report = run_interview(draft, stats, config, [], anterior)
    pipe = report.projects[0]

    assert pipe.name == "Ingesta v2"
    assert pipe.status == "en_riesgo"
    assert pipe.progress == 60
    assert pipe.milestone == "Pruebas E2E"


def test_un_logro_de_un_proyecto_que_no_capturaste_se_omite(responde, config, semana):
    stats = summarize(semana, TZ)
    draft = WeekDraft(
        focus="x", focus_context="x", summary="x",
        achievements=[AchievementDraft(project="FANTASMA", title="t", result="r")],
        days=[],
    )
    responde(
        "1", "0", "0", "", "", "",
        "Ingesta", "1", "70", "Hito", "",
        "Panel", "1", "50", "Hito", "",
        "n",
        "n", "n",
        "", "", "", "", "",
        "n",
        "",
    )

    report = run_interview(draft, stats, config, [])

    assert report.achievements == []


def test_un_dia_sin_commits_no_hereda_el_texto_del_modelo(responde, config, semana):
    stats = summarize(semana, TZ)
    miercoles = date(2026, 9, 16)
    draft = WeekDraft(
        focus="x", focus_context="x", summary="x", achievements=[],
        days=[DayDraft(day=miercoles, project="PIPE", summary="Sin commits")],
    )
    responde(
        "1", "0", "0", "", "", "",
        "Ingesta", "1", "70", "Hito", "",
        "Panel", "1", "50", "Hito", "",
        "n", "n", "n",
        "", "", "", "", "",
        "n", "",
    )

    report = run_interview(draft, stats, config, [])

    assert report.days == []


def test_avisa_si_la_semana_esta_bloqueada_sin_bloqueos():
    report = Report(
        author="Camila", week_start=LUNES, overall_status="bloqueado",
        goals_done=0, goals_total=1, focus="x", summary="x",
        projects=[ProjectStatus(project="PIPE", name="Ingesta", status="en_curso",
                                progress=50, milestone="Hito")],
    )

    avisos = review_report(report)

    assert avisos == [
        "la semana quedó marcada como bloqueada, pero ningún obstáculo "
        "está marcado como que te frena"
    ]


def test_avisa_si_un_proyecto_esta_en_riesgo_sin_explicacion():
    report = Report(
        author="Camila", week_start=LUNES, overall_status="en_curso",
        goals_done=1, goals_total=1, focus="x", summary="x",
        projects=[ProjectStatus(project="OPS", name="Clúster", status="detenido",
                                progress=20, milestone="Hito")],
    )

    assert review_report(report) == [
        "OPS está en riesgo o detenido y no dice por qué"
    ]


def test_un_reporte_coherente_no_genera_avisos():
    report = Report(
        author="Camila", week_start=LUNES, overall_status="en_curso",
        goals_done=1, goals_total=1, focus="x", summary="x",
        projects=[ProjectStatus(project="PIPE", name="Ingesta", status="en_curso",
                                progress=50, milestone="Hito")],
    )

    assert review_report(report) == []
