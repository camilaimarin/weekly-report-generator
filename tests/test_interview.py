from datetime import date

import pytest
from factories import TZ

from weekly_report.aggregate import summarize
from weekly_report.config import Config
from weekly_report.interview import (
    ask, ask_int, ask_percent, ask_weekdays, ask_yes_no, run_interview,
)
from weekly_report.llm import AchievementDraft, DayDraft, WeekDraft

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
        "s", "", "",                          # acepta el logro tal cual
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
