from pydantic import BaseModel, AwareDatetime


class Activity(BaseModel):
    source: str
    project: str | None = None
    timestamp: AwareDatetime
    title: str
    kind: str
    ref: str
    body: str | None = None
    extra: dict = {}
