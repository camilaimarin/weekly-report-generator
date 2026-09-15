import subprocess
from datetime import datetime
from pathlib import Path

from weekly_report.models import Activity
from weekly_report.sources.base import Source

FIELD_SEP = "\x1f"
RECORD_SEP = "\x1e"
LOG_FORMAT = "%x1e%H%x1f%aI%x1f%s%x1f%b%x1f"


class GitLocalSource(Source):
    name = "git"

    def __init__(
        self, repo_path: Path, author_emails: list[str], project: str | None = None
    ):
        self.repo_path = Path(repo_path).expanduser().resolve()
        self.author_emails = author_emails
        self.project = project

    def collect(self, start: datetime, end: datetime) -> list[Activity]:
        activities = []
        for record in self._git_log(since=start).split(RECORD_SEP):
            record = record.strip("\n")
            if not record:
                continue
            ref, timestamp, title, body, numstat = record.split(FIELD_SEP, maxsplit=4)
            activity = Activity(
                source=self.name,
                project=self.project,
                timestamp=timestamp,
                title=title,
                kind="commit",
                ref=ref,
                body=body.strip() or None,
                extra={"repo": self.repo_path.name, **_parse_numstat(numstat)},
            )
            if start <= activity.timestamp < end:
                activities.append(activity)
        return activities

    def _git_log(self, since: datetime) -> str:
        command = [
            "git", "-C", str(self.repo_path), "log",
            "--all",
            "--no-merges",
            "--fixed-strings",
            "--numstat",
            f"--since={since.isoformat()}",
            f"--format={LOG_FORMAT}",
        ]
        command += [f"--author=<{email}>" for email in self.author_emails]
        result = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8"
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"git log falló en {self.repo_path}: {result.stderr.strip()}"
            )
        return result.stdout


def _parse_numstat(block: str) -> dict[str, int]:
    added = deleted = files = 0
    for line in block.strip().splitlines():
        lines_added, lines_deleted, _path = line.split("\t", maxsplit=2)
        files += 1
        if lines_added != "-":
            added += int(lines_added)
            deleted += int(lines_deleted)
    return {"lines_added": added, "lines_deleted": deleted, "files_changed": files}
