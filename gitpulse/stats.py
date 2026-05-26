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

    @property
    def net_lines(self) -> int:
        return self.total_insertions - self.total_deletions

    def format_numbers(self) -> str:
        """Human-friendly number formatting."""
        return (
            f"Commits:       {self.total_commits:,}\n"
            f"Insertions:    {self.total_insertions:,} +\n"
            f"Deletions:     {self.total_deletions:,} -\n"
            f"Net lines:     {self.net_lines:,}\n"
            f"Active days:   {self.active_days:,}\n"
            f"Longest streak:{self.longest_streak} days\n"
            f"Current streak:{self.current_streak} days"
        )
