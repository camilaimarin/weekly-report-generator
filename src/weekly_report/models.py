from datetime import date, timedelta
from typing import Literal, Self

from pydantic import BaseModel, AwareDatetime, Field, model_validator


class Activity(BaseModel):
    source: str
    project: str | None = None
    timestamp: AwareDatetime
    title: str
    kind: str
    ref: str
    body: str | None = None
    extra: dict = {}


class ProjectStatus(BaseModel):
    project: str
    name: str
    status: Literal["en_curso", "en_riesgo", "detenido", "completado"]
    progress: int = Field(ge=0, le=100)
    milestone: str
    next_milestone: str | None = None


class Obstacle(BaseModel):
    project: str
    title: str
    impact: Literal["alto", "medio", "bajo"]
    owner: str
    need: str
    blocking: bool = False


class DayLog(BaseModel):
    day: date
    project: str
    summary: str
    status: Literal["cumplido", "parcial", "bloqueado"]
    refs: list[str] = []


class Achievement(BaseModel):
    project: str
    title: str
    result: str
    refs: list[str] = []


class Metric(BaseModel):
    label: str
    value: float
    unit: str = ""
    previous: float | None = None
    target: float | None = None
    better: Literal["sube", "baja"] | None = None
    note: str | None = None


class CarryOver(BaseModel):
    project: str
    title: str
    progress: int | None = Field(default=None, ge=0, le=100)
    remaining: str


class PlannedActivity(BaseModel):
    project: str
    title: str
    kind: Literal["critico", "planificado", "producto"]
    days: list[date] = Field(min_length=1)


class Report(BaseModel):
    author: str
    role: str = ""
    week_start: date
    overall_status: Literal["en_curso", "en_riesgo", "bloqueado"]
    goals_done: int = Field(ge=0)
    goals_total: int = Field(ge=0)
    focus: str
    focus_context: str = ""
    summary: str
    projects: list[ProjectStatus] = []
    achievements: list[Achievement] = Field(default=[], max_length=4)
    obstacles: list[Obstacle] = []
    metrics: list[Metric] = []
    carry_over: list[CarryOver] = []
    days: list[DayLog] = []
    plan: list[PlannedActivity] = []
    notes: list[str] = []

    @property
    def week_number(self) -> int:
        return self.week_start.isocalendar().week

    @property
    def week_end(self) -> date:
        return self.week_start + timedelta(days=4)

    @property
    def next_week_start(self) -> date:
        return self.week_start + timedelta(days=7)

    @property
    def next_week_number(self) -> int:
        return self.next_week_start.isocalendar().week

    @property
    def active_blockers(self) -> list[Obstacle]:
        order = ["alto", "medio", "bajo"]
        blockers = [o for o in self.obstacles if o.blocking]
        return sorted(blockers, key=lambda o: order.index(o.impact))

    @model_validator(mode="after")
    def check_consistency(self) -> Self:
        if self.week_start.weekday() != 0:
            raise ValueError(f"week_start debe ser lunes: {self.week_start}")

        if self.goals_done > self.goals_total:
            raise ValueError(
                f"objetivos cerrados ({self.goals_done}) "
                f"mayor que el total ({self.goals_total})"
            )

        week_last_day = self.week_start + timedelta(days=6)
        for d in self.days:
            if not self.week_start <= d.day <= week_last_day:
                raise ValueError(f"el día {d.day} no es de la semana del reporte")

        next_start = self.next_week_start
        next_last_day = next_start + timedelta(days=6)
        for p in self.plan:
            for day in p.days:
                if not next_start <= day <= next_last_day:
                    raise ValueError(
                        f"'{p.title}' tiene el día {day}, fuera de la semana siguiente"
                    )

        known = {p.project for p in self.projects}
        tagged = [
            *self.achievements,
            *self.obstacles,
            *self.carry_over,
            *self.days,
            *self.plan,
        ]
        unknown = {item.project for item in tagged} - known
        if unknown:
            raise ValueError(
                f"proyectos que no están en la tabla de proyectos: {sorted(unknown)}"
            )

        return self
