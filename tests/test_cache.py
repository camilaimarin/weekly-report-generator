from datetime import date, datetime
from pathlib import Path

import pytest
from factories import TZ, FakeSource, activity
from pydantic import ValidationError

from weekly_report.cache import (
    WeekCache, cache_path, collect_week, get_week, load_week, monday_of, save_week,
    week_range,
)

LUNES = date(2026, 9, 14)


def test_el_lunes_de_cualquier_dia():
    assert monday_of(date(2026, 9, 17)) == LUNES
    assert monday_of(LUNES) == LUNES


def test_la_semana_va_del_lunes_al_lunes_siguiente(tz):
    start, end = week_range(LUNES, tz)

    assert start == datetime(2026, 9, 14, tzinfo=TZ)
    assert end == datetime(2026, 9, 21, tzinfo=TZ)


def test_el_archivo_se_llama_por_semana_iso():
    assert cache_path(LUNES, Path("data")) == Path("data/2026-W38.json")


def test_el_mismo_repo_configurado_dos_veces_no_duplica(tz):
    misma = activity(ref="a1")
    fuentes = [FakeSource("git_local", [misma]), FakeSource("git_local", [misma])]

    cache = collect_week(fuentes, LUNES, tz)

    assert len(cache.activities) == 1


def test_las_actividades_quedan_ordenadas_por_fecha(tz):
    fuentes = [
        FakeSource("a", [activity(day=17, ref="tarde")]),
        FakeSource("b", [activity(day=14, ref="temprano")]),
    ]

    cache = collect_week(fuentes, LUNES, tz)

    assert [a.ref for a in cache.activities] == ["temprano", "tarde"]


def test_solo_entra_lo_que_cae_en_la_semana(tz):
    fuente = FakeSource("a", [activity(day=14), activity(day=21, ref="otra")])

    cache = collect_week([fuente], LUNES, tz)

    assert [a.ref for a in cache.activities] == ["abc"]


def test_ida_y_vuelta_a_disco_conserva_todo(tmp_path, semana):
    save_week(semana, tmp_path)

    assert load_week(LUNES, tmp_path) == semana


def test_una_semana_que_no_se_guardo_es_none(tmp_path):
    assert load_week(LUNES, tmp_path) is None


def test_la_carpeta_se_crea_sola(tmp_path, semana):
    destino = tmp_path / "nueva" / "data"

    save_week(semana, destino)

    assert (destino / "2026-W38.json").exists()


def test_un_json_corrupto_no_pasa_como_bueno(tmp_path):
    (tmp_path / "2026-W38.json").write_text('{"week_start": "2026-09-14"}')

    with pytest.raises(ValidationError):
        load_week(LUNES, tmp_path)


def test_si_hay_cache_no_se_vuelve_a_leer_la_fuente(tmp_path, tz, semana):
    save_week(semana, tmp_path)
    fuente = FakeSource("a", [activity()])

    get_week([fuente], LUNES, tz, tmp_path)

    assert fuente.calls == 0


def test_con_refresh_se_vuelve_a_leer(tmp_path, tz, semana):
    save_week(semana, tmp_path)
    fuente = FakeSource("a", [activity()])

    cache = get_week([fuente], LUNES, tz, tmp_path, refresh=True)

    assert fuente.calls == 1
    assert len(cache.activities) == 1


def test_sin_cache_se_recolecta_y_se_guarda(tmp_path, tz):
    fuente = FakeSource("a", [activity()])

    get_week([fuente], LUNES, tz, tmp_path)

    assert fuente.calls == 1
    assert isinstance(load_week(LUNES, tmp_path), WeekCache)
