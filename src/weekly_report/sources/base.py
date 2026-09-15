from abc import ABC, abstractmethod
from datetime import datetime

from weekly_report.models import Activity


class Source(ABC):
    name: str

    @abstractmethod
    def collect(self, start: datetime, end: datetime) -> list[Activity]:
        """Actividades con timestamp en [start, end): start incluido, end excluido."""
