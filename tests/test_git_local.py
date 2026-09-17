import pytest

from weekly_report.sources.git_local import _is_ignored, _parse_numstat


@pytest.mark.parametrize(
    "path, patrones, ignorado",
    [
        ("uv.lock", ["uv.lock"], True),
        ("src/app.py", ["uv.lock"], False),
        ("web/bundle.min.js", ["*.min.js"], True),
        ("notebooks/analisis.ipynb", ["notebooks/"], True),
        ("src/notebooks/otro.ipynb", ["notebooks/"], True),
        ("src/notebooks.py", ["notebooks/"], False),
        ("data/generado/salida.csv", ["data/"], True),
        ("data.py", ["data/"], False),
        ("migrations/0001.sql", ["migrations/*"], True),
        ("src/app.py", [], False),
    ],
)
def test_que_cuenta_como_archivo_ignorado(path, patrones, ignorado):
    assert _is_ignored(path, patrones) is ignorado


@pytest.mark.parametrize(
    "path",
    [
        "viejo.lock => uv.lock",
        "carpeta/{viejo => nuevo}/uv.lock",
        "{ => nueva}/uv.lock",
    ],
)
def test_un_archivo_renombrado_se_juzga_por_su_nombre_nuevo(path):
    assert _is_ignored(path, ["uv.lock"]) is True


def test_una_carpeta_renombrada_sigue_ignorada():
    assert _is_ignored("{src => data}/generado.csv", ["data/"]) is True


def test_las_lineas_se_suman_sin_los_archivos_ignorados():
    numstat = "10\t2\tsrc/app.py\n5000\t0\tuv.lock\n30\t4\tdata/salida.csv"

    stats = _parse_numstat(numstat, ["uv.lock", "data/"])

    assert stats == {"lines_added": 10, "lines_deleted": 2, "files_changed": 1}


def test_un_binario_cuenta_como_archivo_pero_no_como_lineas():
    stats = _parse_numstat("-\t-\tlogo.png", [])

    assert stats == {"lines_added": 0, "lines_deleted": 0, "files_changed": 1}


def test_un_commit_que_solo_toca_lo_ignorado_sigue_existiendo():
    stats = _parse_numstat("5000\t0\tuv.lock", ["uv.lock"])

    assert stats == {"lines_added": 0, "lines_deleted": 0, "files_changed": 0}
