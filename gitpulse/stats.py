"""Repository statistics data class and formatters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RepoStats:
    """Summary statistics for a repository or aggregate."""

    total_commits: int = 0
    total_insertions: int = 0
    total_deletions: int = 0
    active_days: int = 0
    longest_streak: int = 0
    current_streak: int = 0
    repo_count: int = 0
    top_authors: list[tuple[str, int]] = ()
    unique_authors: int = 0
    bus_factor: int = 0
    churn_ratio: float = 0.0
    freshness_days: int = 0
    file_count: int = 0

    @property
    def net_lines(self) -> int:
        return self.total_insertions - self.total_deletions

    @property
    def health_grade(self) -> str:
        """Letter grade based on simple heuristics."""
        if self.freshness_days > 180:
            return "F"
        if self.freshness_days > 90:
            return "D"
        if self.active_days < 10:
            return "C"
        if self.unique_authors < 2:
            return "C"
        if self.longest_streak >= 30 and self.unique_authors >= 3:
            return "A"
        return "B"

    def format_numbers(self) -> str:
        """Human-friendly number formatting."""
        return (
            f"Commits: {self.total_commits:,}\n"
            f"Insertions: {self.total_insertions:,} +\n"
            f"Deletions: {self.total_deletions:,} -\n"
            f"Net lines: {self.net_lines:,}\n"
            f"Active days: {self.active_days:,}\n"
            f"Longest streak: {self.longest_streak} days\n"
            f"Current streak: {self.current_streak} days\n"
            f"Unique authors: {self.unique_authors}\n"
            f"Bus factor: {self.bus_factor}\n"
            f"Churn ratio: {self.churn_ratio:.1%}\n"
            f"Last commit: {self.freshness_days} days ago"
        )

    @classmethod
    def from_pulse(cls, pulse) -> "RepoStats":
        """Create RepoStats from a GitPulse instance."""
        return cls(
            total_commits=pulse.total_commits,
            total_insertions=pulse.total_insertions,
            total_deletions=pulse.total_deletions,
            active_days=pulse.active_days,
            longest_streak=pulse.longest_streak,
            current_streak=pulse.current_streak,
            repo_count=pulse.repo_count,
            unique_authors=len(pulse.authors),
            bus_factor=pulse.health.bus_factor,
            churn_ratio=pulse.health.churn_ratio,
            freshness_days=pulse.health.freshness_days,
            file_count=pulse.health.file_count,
            top_authors=[
                (a.name, a.commits)
                for a in sorted(pulse.authors.values(), key=lambda a: a.commits, reverse=True)[:5]
            ]
            if pulse.authors
            else [],
        )
