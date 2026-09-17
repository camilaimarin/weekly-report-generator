from datetime import date

import pytest

from weekly_report.formats import (
    format_day, format_number, format_week_range, parse_number,
)


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("99,4", 99.4),
        ("99.4", 99.4),
        ("1,234.56", 1234.56),
        ("  42 ", 42.0),
        ("1 234", 1234.0),
    ],
)
def test_los_numeros_se_pueden_escribir_con_coma_decimal(texto, esperado):
    assert parse_number(texto) == esperado


def test_un_texto_que_no_es_numero_truena():
    with pytest.raises(ValueError):
        parse_number("cuatro")


def test_los_miles_van_con_coma_y_los_decimales_con_punto():
    assert format_number(45643) == "45,643"
    assert format_number(99.4) == "99.4"
    assert format_number(52.0) == "52"


def test_el_dia_lleva_su_nombre_en_espanol():
    assert format_day(date(2026, 9, 14)) == "Lun 14"
    assert format_day(date(2026, 9, 20)) == "Dom 20"


def test_el_rango_de_la_semana_no_repite_el_mes():
    assert format_week_range(date(2026, 9, 14), date(2026, 9, 18)) == "14–18 sep 2026"


def test_el_rango_que_cruza_de_mes_nombra_los_dos():
    rango = format_week_range(date(2026, 9, 28), date(2026, 10, 2))

    assert rango == "28 sep – 2 oct 2026"
