from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest
from factories import LUNES, TZ, activity, cache_with

from weekly_report.cache import WeekCache


@pytest.fixture
def tz() -> ZoneInfo:
    return TZ


@pytest.fixture
def lunes():
    return LUNES


@pytest.fixture
def next_monday():
    return LUNES + timedelta(days=7)


@pytest.fixture
def semana() -> WeekCache:
    return cache_with(
        activity(day=14, ref="a1", project="PIPE", title="arregla el reintento"),
        activity(day=14, ref="a2", project="AI", title="etiquetas del panel"),
        activity(day=17, ref="a3", project="PIPE", title="mueve la cola"),
    )
