"""Core analysis engine — walks git history and collects commit data."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .models import (
    Commit,
    DayActivity,
    WeekActivity,
    MonthActivity,
    AuthorStats,
    FileChurn,
    ExtensionChurn,
    RepoHealth,
    FileChange,
    ChangeType,
)


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

        # Core data
        self.commits: list[Commit] = []
        self.daily: dict[str, DayActivity] = {}
        self.weekly: dict[tuple[int, int], WeekActivity] = {}
        self.monthly: dict[tuple[int, int], MonthActivity] = {}
        self.authors: dict[str, AuthorStats] = {}
        self.file_churn: dict[str, FileChurn] = {}
        self.extension_churn: dict[str, ExtensionChurn] = {}
        self.repo_count: int = 0
        self.total_commits: int = 0
        self.total_insertions: int = 0
        self.total_deletions: int = 0
        self.longest_streak: int = 0
        self.current_streak: int = 0
        self.active_days: int = 0
        self.health: RepoHealth = RepoHealth()
        self._repo_paths: list[Path] = []

    def analyze(self) -> None:
        """Run the full analysis across one or more repos."""
        repos = self._find_repos()
        self._repo_paths = repos
        self.repo_count = len(repos)

        for repo in repos:
            self._analyze_repo(repo)

        self._compute_streaks()
        self._compute_time_buckets()
        self._compute_churn()
        self._compute_health()

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
                    for grandchild in sorted(child.iterdir()):
                        if grandchild.is_dir() and (grandchild / ".git").exists():
                            repos.append(grandchild)
            return repos
        git_dir = self.path / ".git"
        if git_dir.exists():
            return [self.path]
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
            "-M",  # detect renames
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
        file_details: list[FileChange] = []

        for line in lines:
            if line.startswith("__COMMIT_START__") and "|" in line:
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
                        file_details=file_details,
                    )
                    self._record_commit(commit)

                content = line[len("__COMMIT_START__"):]
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
                    file_details = []
            elif "\t" in line and current_hash:
                # numstat line: insertions\tdeletions\tfilename
                parts = line.split("\t")
                if len(parts) >= 3:
                    try:
                        i = int(parts[0]) if parts[0] != "-" else 0
                        d = int(parts[1]) if parts[1] != "-" else 0
                    except ValueError:
                        continue
                    file_path = parts[2]
                    # Handle renames: "old_path => new_path"
                    old_path = ""
                    change_type = ChangeType.MODIFY
                    if "=>" in file_path:
                        rename_match = re.match(r"(.+?)\s*=>\s*(.+)", file_path)
                        if rename_match:
                            old_path = rename_match.group(1).strip()
                            file_path = rename_match.group(2).strip()
                            # Strip { } braces if present
                            file_path = file_path.strip("{}")
                            old_path = old_path.strip("{}")
                            change_type = ChangeType.RENAME
                    elif i > 0 and d == 0:
                        change_type = ChangeType.ADD
                    elif i == 0 and d > 0:
                        change_type = ChangeType.DELETE

                    fc = FileChange(
                        path=file_path,
                        old_path=old_path,
                        insertions=i,
                        deletions=d,
                        change_type=change_type,
                    )
                    file_details.append(fc)
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
                file_details=file_details,
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
        self.daily[day_key].authors.add(commit.author_email)
        self.daily[day_key].files_changed += commit.files_changed

        # Author bucket
        author_key = f"{commit.author_name} <{commit.author_email}>"
        if author_key not in self.authors:
            self.authors[author_key] = AuthorStats(
                name=commit.author_name,
                email=commit.author_email,
            )
        a = self.authors[author_key]
        a.commits += 1
        a.insertions += commit.insertions
        a.deletions += commit.deletions
        a.files_changed += commit.files_changed
        a.active_days.add(day_key)
        if a.first_commit is None or commit.date < a.first_commit:
            a.first_commit = commit.date
        if a.last_commit is None or commit.date > a.last_commit:
            a.last_commit = commit.date

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

    def _compute_time_buckets(self) -> None:
        """Compute weekly and monthly activity buckets."""
        for day_key, activity in self.daily.items():
            dt = datetime.strptime(day_key, "%Y-%m-%d")
            iso = dt.isocalendar()
            week_key = (iso[0], iso[1])

            if week_key not in self.weekly:
                self.weekly[week_key] = WeekActivity(year=iso[0], week=iso[1])
            self.weekly[week_key].commits += activity.commits
            self.weekly[week_key].insertions += activity.insertions
            self.weekly[week_key].deletions += activity.deletions
            self.weekly[week_key].active_days += 1

            month_key = (dt.year, dt.month)
            if month_key not in self.monthly:
                self.monthly[month_key] = MonthActivity(year=dt.year, month=dt.month)
            self.monthly[month_key].commits += activity.commits
            self.monthly[month_key].insertions += activity.insertions
            self.monthly[month_key].deletions += activity.deletions
            self.monthly[month_key].active_days += 1

    def _compute_churn(self) -> None:
        """Compute file and extension churn from commit data."""
        for commit in self.commits:
            author_key = f"{commit.author_name} <{commit.author_email}>"
            for fc in commit.file_details:
                # File churn
                if fc.path not in self.file_churn:
                    self.file_churn[fc.path] = FileChurn(path=fc.path)
                self.file_churn[fc.path].insertions += fc.insertions
                self.file_churn[fc.path].deletions += fc.deletions
                self.file_churn[fc.path].commits += 1
                self.file_churn[fc.path].authors.add(author_key)

                # Extension churn
                ext = fc.extension
                if ext:
                    if ext not in self.extension_churn:
                        self.extension_churn[ext] = ExtensionChurn(extension=ext)
                    self.extension_churn[ext].insertions += fc.insertions
                    self.extension_churn[ext].deletions += fc.deletions
                    self.extension_churn[ext].commits += 1
                    self.extension_churn[ext].files += 1

    def _compute_health(self) -> None:
        """Compute repository health metrics."""
        total_days = (self.until - self.since).days + 1
        self.health.total_commits = self.total_commits
        self.health.active_days = self.active_days
        self.health.total_days = total_days
        self.health.unique_authors = len(self.authors)
        self.health.longest_streak = self.longest_streak
        self.health.current_streak = self.current_streak
        self.health.freshness_days = 0

        if self.commits:
            last_commit_date = max(c.date for c in self.commits)
            # Handle both timezone-aware and naive datetimes
            now = datetime.now(last_commit_date.tzinfo) if last_commit_date.tzinfo else datetime.now()
            self.health.freshness_days = (now - last_commit_date).days

        if self.total_commits > 0:
            self.health.avg_commits_per_day = round(
                self.total_commits / max(self.active_days, 1), 2
            )

        # Bus factor: minimum number of authors whose departure would reduce
        # total commits by 50%+
        sorted_authors = sorted(
            self.authors.values(), key=lambda a: a.commits, reverse=True
        )
        if sorted_authors:
            total = self.total_commits
            accumulated = 0
            for i, a in enumerate(sorted_authors):
                accumulated += a.commits
                if accumulated >= total * 0.5:
                    self.health.bus_factor = i + 1
                    break

        # Churn ratio: deletions / (insertions + deletions)
        total_lines = self.total_insertions + self.total_deletions
        if total_lines > 0:
            self.health.churn_ratio = round(self.total_deletions / total_lines, 3)

        # Check repo metadata files (only for single-repo mode)
        if self._repo_paths:
            repo = self._repo_paths[0]
            self.health.has_readme = any(
                (repo / f).exists() for f in ["README.md", "README.rst", "README.txt", "README"]
            )
            self.health.has_contributing = any(
                (repo / f).exists()
                for f in ["CONTRIBUTING.md", "CONTRIBUTING.rst", "CONTRIBUTING"]
            )
            self.health.has_license = any(
                (repo / f).exists()
                for f in ["LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE"]
            )
            self.health.has_ci = (repo / ".github").exists() or (repo / ".travis.yml").exists()

            # File count and depth
            try:
                result = subprocess.run(
                    ["git", "-C", str(repo), "ls-files"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    files_list = [f for f in result.stdout.strip().split("\n") if f]
                    self.health.file_count = len(files_list)
                    if files_list:
                        depths = [f.count("/") for f in files_list]
                        self.health.directory_depth = max(depths) if depths else 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

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
            "authors": {
                k: {
                    "commits": v.commits,
                    "insertions": v.insertions,
                    "deletions": v.deletions,
                    "first_commit": v.first_commit.isoformat() if v.first_commit else None,
                    "last_commit": v.last_commit.isoformat() if v.last_commit else None,
                    "active_days": len(v.active_days),
                }
                for k, v in self.authors.items()
            },
            "daily": {
                k: {
                    "commits": v.commits,
                    "insertions": v.insertions,
                    "deletions": v.deletions,
                }
                for k, v in self.daily.items()
            },
            "weekly": {
                f"{k[0]}-W{k[1]:02d}": {
                    "commits": v.commits,
                    "insertions": v.insertions,
                    "deletions": v.deletions,
                    "active_days": v.active_days,
                }
                for k, v in self.weekly.items()
            },
            "monthly": {
                v.label: {
                    "commits": v.commits,
                    "insertions": v.insertions,
                    "deletions": v.deletions,
                    "active_days": v.active_days,
                }
                for v in self.monthly.values()
            },
            "health": {
                "activity_score": self.health.activity_score,
                "health_grade": self.health.health_grade,
                "bus_factor": self.health.bus_factor,
                "churn_ratio": self.health.churn_ratio,
                "freshness_days": self.health.freshness_days,
                "has_readme": self.health.has_readme,
                "has_contributing": self.health.has_contributing,
                "has_license": self.health.has_license,
                "has_ci": self.health.has_ci,
                "file_count": self.health.file_count,
            },
            "file_churn": {
                k: {
                    "insertions": v.insertions,
                    "deletions": v.deletions,
                    "total_churn": v.total_churn,
                    "commits": v.commits,
                    "authors": len(v.authors),
                }
                for k, v in sorted(
                    self.file_churn.items(),
                    key=lambda x: x[1].total_churn,
                    reverse=True,
                )[:50]
            },
            "extension_churn": {
                k: {
                    "insertions": v.insertions,
                    "deletions": v.deletions,
                    "total_churn": v.total_churn,
                    "commits": v.commits,
                    "files": v.files,
                }
                for k, v in sorted(
                    self.extension_churn.items(),
                    key=lambda x: x[1].total_churn,
                    reverse=True,
                )
            },
        }
        json.dump(data, fp, indent=2)


# Helper
def _parse_iso(s: str) -> datetime:
    """Parse an ISO 8601 datetime string, falling back to now."""
    try:
        # Handle Python 3.10 compatibility: fromisoformat doesn't support all ISO formats
        # Remove timezone offset for parsing if present, or use manual parsing
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        # Try standard fromisoformat first (Python 3.11+)
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        # Fallback: parse common ISO format manually
        try:
            # Format: 2025-06-01T12:00:00+00:00 or 2025-06-01T12:00:00
            return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
        except (ValueError, TypeError):
            return datetime.now()
