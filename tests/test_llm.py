from datetime import date

from factories import activity, cache_with

from weekly_report.aggregate import summarize
from weekly_report.llm import (
    MAX_COMMITS_POR_DIA, AchievementDraft, DayDraft, WeekDraft, build_prompt,
    review_draft,
)

LUNES = date(2026, 9, 14)
JUEVES = date(2026, 9, 17)


def draft(**cambios) -> WeekDraft:
    base = dict(
        focus="Clústeres",
        focus_context="Separación de clústeres.",
        summary="Arreglamos la sincronización.",
        achievements=[AchievementDraft(project="PIPE", title="t", result="r")],
        days=[
            DayDraft(day=LUNES, project="PIPE", summary="s"),
            DayDraft(day=JUEVES, project="PIPE", summary="s"),
        ],
    )
    return WeekDraft(**(base | cambios))


def test_el_modelo_no_tiene_donde_escribir_una_metrica():
    campos = WeekDraft.model_json_schema()["properties"]

    assert sorted(campos) == [
        "achievements", "carry_over", "days", "focus", "focus_context", "plan",
        "summary",
    ]
    assert all(
        campo not in campos
        for campo in ("metrics", "commits", "progress", "goals_done", "lines_added")
    )


def test_lo_unico_numerico_que_puede_escribir_son_dias_de_la_semana():
    plan = WeekDraft.model_json_schema()["$defs"]["PlanDraft"]["properties"]

    assert sorted(plan) == ["kind", "project", "title", "weekdays"]


def test_el_prompt_lleva_los_commits_agrupados_por_dia(tz, semana):
    prompt = build_prompt(semana, summarize(semana, tz))

    assert "2026-09-14 (2 commits):" in prompt
    assert "PIPE: arregla el reintento" in prompt
    assert "2026-09-16: sin commits." in prompt


def test_el_prompt_recorta_los_dias_con_muchos_commits(tz):
    muchos = [activity(ref=f"c{i}", title=f"commit {i}") for i in range(30)]
    cache = cache_with(*muchos)

    prompt = build_prompt(cache, summarize(cache, tz))

    assert prompt.count("commit ") >= MAX_COMMITS_POR_DIA
    assert f"(y {30 - MAX_COMMITS_POR_DIA} commits más)" in prompt


def test_un_borrador_fiel_a_los_datos_pasa_limpio(tz, semana):
    stats = summarize(semana, tz)

    assert review_draft(draft(), stats, semana) == []


def test_se_detecta_un_proyecto_inventado(tz, semana):
    inventado = draft(
        achievements=[AchievementDraft(project="FANTASMA", title="t", result="r")]
    )

    problemas = review_draft(inventado, summarize(semana, tz), semana)

    assert problemas == ["proyecto que no existe: FANTASMA"]


def test_se_detecta_un_dia_de_otra_semana(tz, semana):
    fuera = draft(days=[DayDraft(day=date(2026, 9, 30), project="PIPE", summary="s")])

    problemas = review_draft(fuera, summarize(semana, tz), semana)

    assert "día fuera de la semana: 2026-09-30" in problemas


def test_se_detecta_un_dia_con_commits_que_el_modelo_ignoro(tz, semana):
    solo_lunes = draft(days=[DayDraft(day=LUNES, project="PIPE", summary="s")])

    problemas = review_draft(solo_lunes, summarize(semana, tz), semana)

    assert problemas == ["día con commits que no redactó: 2026-09-17"]


def test_se_detecta_un_numero_que_nadie_dijo(tz, semana):
    inventado = draft(summary="Subimos la cobertura al 92 %.")

    problemas = review_draft(inventado, summarize(semana, tz), semana)

    assert problemas == ["número que no está en los datos: 92"]


def test_un_numero_que_si_esta_en_un_commit_no_se_marca(tz):
    cache = cache_with(activity(title="baja de 144 a 44 paquetes"))
    resumen = draft(
        summary="Las dependencias bajaron de 144 a 44.",
        days=[DayDraft(day=LUNES, project="PIPE", summary="s")],
    )

    assert review_draft(resumen, summarize(cache, tz), cache) == []


def test_los_hashes_de_commit_no_valen_como_numeros_conocidos(tz):
    cache = cache_with(activity(ref="a3f92b17c", title="sin números"))
    inventado = draft(
        summary="Subimos 92 puntos.",
        days=[DayDraft(day=LUNES, project="PIPE", summary="s")],
    )

    problemas = review_draft(inventado, summarize(cache, tz), cache)

    assert "número que no está en los datos: 92" in problemas
