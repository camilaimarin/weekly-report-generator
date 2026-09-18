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


def test_solo_cuentan_los_tags_creados_dentro_de_la_semana(tmp_path):
    import subprocess
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from weekly_report.sources.git_local import read_tags

    tz = ZoneInfo("America/Mexico_City")
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
        "GIT_COMMITTER_DATE": "2026-09-15T12:00:00-06:00",
        "PATH": "/usr/bin:/bin:/usr/local/bin",
    }

    def git(*args, **extra):
        subprocess.run(["git", "-C", str(repo), *args], env={**env, **extra},
                       check=True, capture_output=True)

    git("init", "-q")
    (repo / "a.txt").write_text("hola")
    git("add", "a.txt")
    git("commit", "-m", "uno", GIT_AUTHOR_DATE="2026-09-15T12:00:00-06:00")
    git("tag", "-a", "v1.0.0", "-m", "de esta semana",
        GIT_COMMITTER_DATE="2026-09-15T12:00:00-06:00")
    git("tag", "-a", "v0.9.0", "-m", "vieja",
        GIT_COMMITTER_DATE="2026-08-01T12:00:00-06:00")

    start = datetime(2026, 9, 14, tzinfo=tz)
    end = datetime(2026, 9, 21, tzinfo=tz)

    assert read_tags(repo, start, end) == ["v1.0.0"]


def test_un_repo_sin_tags_no_truena(tmp_path):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from weekly_report.sources.git_local import read_tags

    tz = ZoneInfo("America/Mexico_City")
    vacio = read_tags(tmp_path, datetime(2026, 9, 14, tzinfo=tz),
                      datetime(2026, 9, 21, tzinfo=tz))

    assert vacio == []
