"""Core analysis engine — walks git history and collects commit data."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


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


@dataclass
class DayActivity:
    """Activity bucket for one calendar day."""

    date: str  # YYYY-MM-DD
    commits: int = 0
    insertions: int = 0
    deletions: int = 0


class GitPulse:
    """Analyze a git repository (or directory of repos) and produce activity data."""

    def __init__(
        self,
        path: Path,
        since: datetime,
        until: datetime,
        author: str | None = None,
        scan_repos: bool = False,
    ):
        self.path = path
        self.since = since
        self.until = until
        self.author = author
        self.scan_repos = scan_repos

        self.commits: list[Commit] = []
        self.daily: dict[str, DayActivity] = {}
        self.authors: dict[str, int] = {}
        self.repo_count: int = 0
        self.total_commits: int = 0
        self.total_insertions: int = 0
        self.total_deletions: int = 0
        self.longest_streak: int = 0
        self.current_streak: int = 0
        self.active_days: int = 0

    def analyze(self) -> None:
        """Run the analysis across one or more repos."""
        repos = self._find_repos()
        self.repo_count = len(repos)

        for repo in repos:
            self._analyze_repo(repo)

        self._compute_streaks()

    def _find_repos(self) -> list[Path]:
        """Find git repositories under the given path."""
        if self.scan_repos:
            repos = []
            for child in sorted(self.path.iterdir()):
                if not child.is_dir():
                    continue
                if (child / ".git").exists():
                    repos.append(child)
                else:
                    # Check one level deeper (e.g., parent/repo-name/repo-name/.git)
                    for grandchild in sorted(child.iterdir()):
                        if grandchild.is_dir() and (grandchild / ".git").exists():
                            repos.append(grandchild)
            return repos
        git_dir = self.path / ".git"
        if git_dir.exists():
            return [self.path]
        # Maybe it's a worktree or bare repo
        return []

    def _analyze_repo(self, repo: Path) -> None:
        """Collect commits from a single repository."""
        since_fmt = self.since.strftime("%Y-%m-%d")
        until_fmt = self.until.strftime("%Y-%m-%d")

        log_cmd = [
            "git",
            "-C",
            str(repo),
            "log",
            "--since",
            since_fmt,
            "--until",
            until_fmt,
            "--format=__COMMIT_START__%H|%aI|%aN|%aE|%s",
            "--numstat",
        ]
        if self.author:
            log_cmd.extend(["--author", self.author])

        try:
            result = subprocess.run(
                log_cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return

        if result.returncode != 0:
            return

        self._parse_log(result.stdout)

    def _parse_log(self, raw: str) -> None:
        """Parse the combined log+numstat output."""
        lines = raw.strip().split("\n") if raw.strip() else []
        if not lines:
            return

        current_hash = ""
        current_date = ""
        current_name = ""
        current_email = ""
        current_subject = ""
        ins = 0
        dels = 0
        files = 0

        for line in lines:
            if line.startswith("__COMMIT_START__") and "|" in line:
                # Commit header line
                # Flush previous commit
                if current_hash:
                    commit = Commit(
                        hash=current_hash,
                        date=_parse_iso(current_date),
                        author_name=current_name,
                        author_email=current_email,
                        subject=current_subject,
                        insertions=ins,
                        deletions=dels,
                        files_changed=files,
                    )
                    self._record_commit(commit)

                # Strip the marker prefix
                content = line[len("__COMMIT_START__") :]
                parts = content.split("|", 4)
                if len(parts) >= 5:
                    current_hash = parts[0]
                    current_date = parts[1]
                    current_name = parts[2]
                    current_email = parts[3]
                    current_subject = parts[4]
                    ins = 0
                    dels = 0
                    files = 0
            elif "\t" in line and current_hash:
                # numstat line: insertions\tdeletions\tfilename
                parts = line.split("\t")
                if len(parts) >= 3:
                    try:
                        i = int(parts[0]) if parts[0] != "-" else 0
                        d = int(parts[1]) if parts[1] != "-" else 0
                    except ValueError:
                        continue
                    ins += i
                    dels += d
                    files += 1

        # Flush last commit
        if current_hash:
            commit = Commit(
                hash=current_hash,
                date=_parse_iso(current_date),
                author_name=current_name,
                author_email=current_email,
                subject=current_subject,
                insertions=ins,
                deletions=dels,
                files_changed=files,
            )
            self._record_commit(commit)

    def _record_commit(self, commit: Commit) -> None:
        """Record a commit in our data structures."""
        self.commits.append(commit)
        self.total_commits += 1
        self.total_insertions += commit.insertions
        self.total_deletions += commit.deletions

        # Daily bucket
        day_key = commit.date.strftime("%Y-%m-%d")
        if day_key not in self.daily:
            self.daily[day_key] = DayActivity(date=day_key)
        self.daily[day_key].commits += 1
        self.daily[day_key].insertions += commit.insertions
        self.daily[day_key].deletions += commit.deletions

        # Author bucket
        key = f"{commit.author_name} <{commit.author_email}>"
        self.authors[key] = self.authors.get(key, 0) + 1

    def _compute_streaks(self) -> None:
        """Compute longest and current streaks from daily activity."""
        if not self.daily:
            return

        sorted_days = sorted(self.daily.keys())
        self.active_days = len(sorted_days)

        # Longest streak
        streak = 1
        max_streak = 1
        for i in range(1, len(sorted_days)):
            prev = datetime.strptime(sorted_days[i - 1], "%Y-%m-%d")
            curr = datetime.strptime(sorted_days[i], "%Y-%m-%d")
            if (curr - prev).days == 1:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 1
        self.longest_streak = max_streak

        # Current streak (ending today or yesterday)
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if sorted_days[-1] not in (today, yesterday):
            self.current_streak = 0
            return

        streak = 0
        for i in range(len(sorted_days) - 1, -1, -1):
            if i == len(sorted_days) - 1:
                streak = 1
            else:
                prev = datetime.strptime(sorted_days[i], "%Y-%m-%d")
                curr = datetime.strptime(sorted_days[i + 1], "%Y-%m-%d")
                if (curr - prev).days == 1:
                    streak += 1
                else:
                    break
        self.current_streak = streak

    def to_json(self, fp) -> None:
        """Write results as JSON to a file-like object."""
        data = {
            "total_commits": self.total_commits,
            "total_insertions": self.total_insertions,
            "total_deletions": self.total_deletions,
            "active_days": self.active_days,
            "longest_streak": self.longest_streak,
            "current_streak": self.current_streak,
            "repo_count": self.repo_count,
            "authors": self.authors,
            "daily": {
                k: {
                    "commits": v.commits,
                    "insertions": v.insertions,
                    "deletions": v.deletions,
                }
                for k, v in self.daily.items()
            },
        }
        json.dump(data, fp, indent=2)


# Helper
def _parse_iso(s: str) -> datetime:
    """Parse an ISO 8601 datetime string, falling back to now."""
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return datetime.now()
