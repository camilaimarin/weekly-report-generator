import tomllib
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator

from weekly_report.sources.base import Source
from weekly_report.sources.git_local import GitLocalSource


class RepoConfig(BaseModel):
    path: Path
    project: str

    @field_validator("path")
    @classmethod
    def expand_and_check(cls, path: Path) -> Path:
        path = path.expanduser()
        if not path.is_dir():
            raise ValueError(f"la carpeta no existe: {path}")
        return path


class Config(BaseModel):
    author: str
    role: str = ""
    timezone: ZoneInfo = ZoneInfo("America/Mexico_City")
    model: str = "qwen3:4b"
    emails: list[str] = Field(min_length=1)
    ignore_files: list[str] = []
    repos: list[RepoConfig] = []


def load_config(path: Path) -> Config:
    if not path.exists():
        raise FileNotFoundError(
            f"No existe {path}. Copia config.example.toml a config.toml y edítalo."
        )
    with path.open("rb") as f:
        return Config.model_validate(tomllib.load(f))


def build_sources(config: Config) -> list[Source]:
    return [
        GitLocalSource(repo.path, config.emails, repo.project, config.ignore_files)
        for repo in config.repos
    ]
