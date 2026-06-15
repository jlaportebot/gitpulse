"""Data models for gitpulse — commit, file change, author, and time-bucket dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ChangeType(Enum):
    """Type of file change."""

    ADD = "A"
    MODIFY = "M"
    DELETE = "D"
    RENAME = "R"
    COPY = "C"


@dataclass
class Commit:
    """A single commit record."""

    hash: str
    date: datetime
    author_name: str
    author_email: str
    subject: str
    insertions: int = 0
    deletions: int = 0
    files_changed: int = 0
    file_details: list[FileChange] = field(default_factory=list)
    branch: str = ""

    @property
    def short_hash(self) -> str:
        return self.hash[:7]

    @property
    def net_lines(self) -> int:
        return self.insertions - self.deletions


@dataclass
class FileChange:
    """A single file change within a commit."""

    path: str
    old_path: str = ""  # for renames
    insertions: int = 0
    deletions: int = 0
    change_type: ChangeType = ChangeType.MODIFY

    @property
    def is_binary(self) -> bool:
        return self.insertions == 0 and self.deletions == 0 and self.change_type != ChangeType.ADD

    @property
    def extension(self) -> str:
        """File extension (lowercase, without dot)."""
        parts = self.path.rsplit(".", 1)
        if len(parts) == 2 and parts[1]:
            return parts[1].lower()
        return ""


@dataclass
class DayActivity:
    """Activity bucket for one calendar day."""

    date: str  # YYYY-MM-DD
    commits: int = 0
    insertions: int = 0
    deletions: int = 0
    authors: set[str] = field(default_factory=set)
    files_changed: int = 0

    @property
    def net_lines(self) -> int:
        return self.insertions - self.deletions


@dataclass
class WeekActivity:
    """Activity bucket for one ISO week."""

    year: int
    week: int
    commits: int = 0
    insertions: int = 0
    deletions: int = 0
    active_days: int = 0


@dataclass
class MonthActivity:
    """Activity bucket for one calendar month."""

    year: int
    month: int
    commits: int = 0
    insertions: int = 0
    deletions: int = 0
    active_days: int = 0

    @property
    def label(self) -> str:
        return f"{self.year}-{self.month:02d}"


@dataclass
class AuthorStats:
    """Statistics for a single author."""

    name: str
    email: str
    commits: int = 0
    insertions: int = 0
    deletions: int = 0
    files_changed: int = 0
    first_commit: datetime | None = None
    last_commit: datetime | None = None
    active_days: set[str] = field(default_factory=set)

    @property
    def net_lines(self) -> int:
        return self.insertions - self.deletions

    @property
    def key(self) -> str:
        return f"{self.name} <{self.email}>"

    @property
    def avg_commits_per_day(self) -> float:
        if not self.active_days:
            return 0.0
        return self.commits / len(self.active_days)


@dataclass
class FileChurn:
    """Churn statistics for a single file."""

    path: str
    insertions: int = 0
    deletions: int = 0
    commits: int = 0
    authors: set[str] = field(default_factory=set)

    @property
    def total_churn(self) -> int:
        return self.insertions + self.deletions

    @property
    def net_lines(self) -> int:
        return self.insertions - self.deletions


@dataclass
class ExtensionChurn:
    """Churn statistics for a file extension."""

    extension: str
    insertions: int = 0
    deletions: int = 0
    commits: int = 0
    files: int = 0

    @property
    def total_churn(self) -> int:
        return self.insertions + self.deletions


@dataclass
class RepoHealth:
    """Health metrics for a repository."""

    total_commits: int = 0
    active_days: int = 0
    total_days: int = 0
    unique_authors: int = 0
    avg_commits_per_day: float = 0.0
    longest_streak: int = 0
    current_streak: int = 0
    bus_factor: int = 0
    churn_ratio: float = 0.0
    freshness_days: int = 0  # days since last commit
    has_readme: bool = False
    has_contributing: bool = False
    has_license: bool = False
    has_ci: bool = False
    file_count: int = 0
    directory_depth: int = 0
    avg_file_size: float = 0.0

    @property
    def activity_score(self) -> float:
        """0-100 score based on commit frequency and recency."""
        if self.total_days == 0:
            return 0.0
        frequency = min(self.active_days / max(self.total_days, 1), 1.0) * 40
        recency = max(0, 30 - self.freshness_days) / 30 * 30
        streak = min(self.longest_streak / 30, 1.0) * 15
        diversity = min(self.unique_authors / 5, 1.0) * 15
        return round(frequency + recency + streak + diversity, 1)

    @property
    def health_grade(self) -> str:
        """Letter grade based on activity score."""
        score = self.activity_score
        if score >= 80:
            return "A"
        if score >= 60:
            return "B"
        if score >= 40:
            return "C"
        if score >= 20:
            return "D"
        return "F"
