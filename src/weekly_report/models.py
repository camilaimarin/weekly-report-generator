from typing import Literal

from pydantic import BaseModel, AwareDatetime, Field


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
