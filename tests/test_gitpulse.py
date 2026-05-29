"""Test suite for gitpulse — comprehensive tests for all modules."""

import io
import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from gitpulse.core import GitPulse
from gitpulse.models import (
    Commit,
    DayActivity,
    AuthorStats,
    FileChurn,
    ExtensionChurn,
    RepoHealth,
    FileChange,
    ChangeType,
    WeekActivity,
    MonthActivity,
)


def _git_env(date_str: str) -> dict:
    """Return environment with both author and committer dates set."""
    return {
        **os.environ,
        "GIT_AUTHOR_DATE": date_str,
        "GIT_COMMITTER_DATE": date_str,
    }


def _make_repo(tmp: Path) -> Path:
    """Create a temporary git repo with a few commits."""
    repo = tmp / "test-repo"
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@test.com"], check=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test User"], check=True
    )

    # Create a file and commit
    (repo / "hello.txt").write_text("hello\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "Initial commit"],
        check=True,
        env=_git_env("2025-06-01T12:00:00"),
    )

    # Second commit
    (repo / "hello.txt").write_text("hello world\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "Add world"],
        check=True,
        env=_git_env("2025-06-02T12:00:00"),
    )

    # Third commit
    (repo / "foo.py").write_text("print('foo')\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "Add foo"],
        check=True,
        env=_git_env("2025-06-03T12:00:00"),
    )

    return repo


def _make_repo_multi_author(tmp: Path) -> Path:
    """Create a repo with commits from multiple authors."""
    repo = tmp / "multi-author-repo"
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)

    # Author 1 commits
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "alice@test.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Alice"], check=True)
    (repo / "a.txt").write_text("aaa\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "Alice commit 1"],
        check=True,
        env=_git_env("2025-06-01T10:00:00"),
    )
    (repo / "a.txt").write_text("aaa bbb\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "Alice commit 2"],
        check=True,
        env=_git_env("2025-06-02T10:00:00"),
    )

    # Author 2 commits
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "bob@test.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Bob"], check=True)
    (repo / "b.txt").write_text("bbb\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "Bob commit 1"],
        check=True,
        env=_git_env("2025-06-03T10:00:00"),
    )

    return repo


# ============================================================
# Core analysis tests
# ============================================================


def test_gitpulse_analyze_single_repo():
    """Test that GitPulse correctly analyzes a single repo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()

        assert pulse.total_commits == 3
        assert pulse.repo_count == 1
        assert pulse.active_days == 3
        assert pulse.longest_streak == 3
        key = "Test User <test@test.com>"
        assert key in pulse.authors
        assert pulse.authors[key].commits == 3
        assert pulse.authors[key].insertions == 3
        assert pulse.authors[key].deletions == 1


def test_gitpulse_scan_multiple_repos():
    """Test scanning a directory for multiple repos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        repo1 = base / "repo1"
        repo1.mkdir(parents=True, exist_ok=True)
        _make_repo(repo1)
        repo2 = base / "repo2"
        repo2.mkdir(parents=True, exist_ok=True)
        _make_repo(repo2)

        pulse = GitPulse(
            path=base,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=True,
        )
        pulse.analyze()

        assert pulse.repo_count == 2
        assert pulse.total_commits == 6


def test_gitpulse_author_filter():
    """Test filtering commits by author."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author="NonExistent",
            scan_repos=False,
        )
        pulse.analyze()
        assert pulse.total_commits == 0

        pulse2 = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author="Test User",
            scan_repos=False,
        )
        pulse2.analyze()
        assert pulse2.total_commits == 3


def test_gitpulse_json_output():
    """Test JSON output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()

        buf = io.StringIO()
        pulse.to_json(buf)
        data = json.loads(buf.getvalue())

        assert data["total_commits"] == 3
        assert data["repo_count"] == 1
        assert data["active_days"] == 3
        # New fields in JSON output
        assert "weekly" in data
        assert "monthly" in data
        assert "health" in data
        assert "file_churn" in data
        assert "extension_churn" in data


def test_gitpulse_no_repo():
    """Test behavior when no git repo is found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pulse = GitPulse(
            path=Path(tmpdir),
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()
        assert pulse.total_commits == 0
        assert pulse.repo_count == 0


# ============================================================
# Model tests
# ============================================================


def test_commit_dataclass():
    """Test Commit dataclass creation and properties."""
    c = Commit(
        hash="abc123def456",
        date=datetime(2025, 6, 1),
        author_name="Test",
        author_email="test@test.com",
        subject="Test commit",
        insertions=10,
        deletions=5,
        files_changed=2,
    )
    assert c.hash == "abc123def456"
    assert c.short_hash == "abc123d"
    assert c.insertions == 10
    assert c.deletions == 5
    assert c.net_lines == 5


def test_commit_with_file_details():
    """Test Commit with file details."""
    fc = FileChange(path="src/main.py", insertions=20, deletions=5)
    c = Commit(
        hash="abc123",
        date=datetime(2025, 6, 1),
        author_name="Test",
        author_email="test@test.com",
        subject="Test commit",
        insertions=20,
        deletions=5,
        files_changed=1,
        file_details=[fc],
    )
    assert len(c.file_details) == 1
    assert c.file_details[0].path == "src/main.py"
    assert c.file_details[0].extension == "py"


def test_file_change_extension():
    """Test FileChange extension extraction."""
    fc1 = FileChange(path="src/main.py")
    assert fc1.extension == "py"
    fc2 = FileChange(path="Makefile")
    assert fc2.extension == ""
    fc3 = FileChange(path="src/.hidden")
    assert fc3.extension == "hidden"  # dotfiles get their name as extension
    fc4 = FileChange(path="data.csv")
    assert fc4.extension == "csv"


def test_file_change_is_binary():
    """Test FileChange is_binary property."""
    fc1 = FileChange(path="image.png", insertions=0, deletions=0)
    assert fc1.is_binary is True
    fc2 = FileChange(path="main.py", insertions=10, deletions=5)
    assert fc2.is_binary is False
    fc3 = FileChange(path="new.txt", insertions=5, deletions=0, change_type=ChangeType.ADD)
    assert fc3.is_binary is False


def test_day_activity():
    """Test DayActivity dataclass."""
    d = DayActivity(date="2025-06-01")
    assert d.commits == 0
    d.commits = 5
    assert d.commits == 5
    assert d.net_lines == 0
    d.insertions = 10
    d.deletions = 3
    assert d.net_lines == 7


def test_author_stats():
    """Test AuthorStats dataclass."""
    a = AuthorStats(name="Alice", email="alice@test.com", commits=5, insertions=100, deletions=20)
    assert a.key == "Alice <alice@test.com>"
    assert a.net_lines == 80
    assert a.avg_commits_per_day == 0.0
    a.active_days.add("2025-06-01")
    a.active_days.add("2025-06-02")
    assert a.avg_commits_per_day == 2.5


def test_file_churn():
    """Test FileChurn dataclass."""
    fc = FileChurn(path="main.py", insertions=100, deletions=50, commits=10)
    assert fc.total_churn == 150
    assert fc.net_lines == 50


def test_extension_churn():
    """Test ExtensionChurn dataclass."""
    ec = ExtensionChurn(extension="py", insertions=500, deletions=200, commits=30, files=10)
    assert ec.total_churn == 700


def test_repo_health():
    """Test RepoHealth dataclass and properties."""
    h = RepoHealth(
        total_commits=100,
        active_days=50,
        total_days=365,
        unique_authors=4,
        longest_streak=15,
        current_streak=3,
        freshness_days=5,
        bus_factor=2,
    )
    assert h.activity_score > 0
    assert h.health_grade in ("A", "B", "C", "D", "F")
    # With recent commits, multiple authors, good streak
    assert h.activity_score >= 20


def test_repo_health_grade():
    """Test RepoHealth grade thresholds."""
    # High score → A or B
    h_good = RepoHealth(
        active_days=300, total_days=365, freshness_days=1,
        longest_streak=60, unique_authors=5,
    )
    assert h_good.health_grade in ("A", "B")

    # Low score → D or F
    h_bad = RepoHealth(
        active_days=5, total_days=365, freshness_days=200,
        longest_streak=2, unique_authors=1,
    )
    assert h_bad.health_grade in ("D", "F")


# ============================================================
# Time bucket tests
# ============================================================


def test_weekly_buckets():
    """Test that weekly activity buckets are computed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()
        assert len(pulse.weekly) > 0
        total_weekly_commits = sum(w.commits for w in pulse.weekly.values())
        assert total_weekly_commits == 3


def test_monthly_buckets():
    """Test that monthly activity buckets are computed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()
        assert len(pulse.monthly) > 0
        # All 3 commits are in June 2025
        june_key = (2025, 6)
        assert june_key in pulse.monthly
        assert pulse.monthly[june_key].commits == 3


def test_monthly_label():
    """Test MonthActivity label property."""
    m = MonthActivity(year=2025, month=6)
    assert m.label == "2025-06"


# ============================================================
# Churn tests
# ============================================================


def test_file_churn_computed():
    """Test that file churn is computed from commits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()
        assert len(pulse.file_churn) > 0
        assert "hello.txt" in pulse.file_churn or "foo.py" in pulse.file_churn


def test_extension_churn_computed():
    """Test that extension churn is computed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()
        assert len(pulse.extension_churn) > 0
        # foo.py was added, so .py should be in extension churn
        assert "py" in pulse.extension_churn


# ============================================================
# Health tests
# ============================================================


def test_health_computed():
    """Test that health metrics are computed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()
        assert pulse.health.total_commits == 3
        assert pulse.health.unique_authors == 1
        assert pulse.health.bus_factor >= 1
        assert pulse.health.activity_score >= 0
        assert pulse.health.health_grade in ("A", "B", "C", "D", "F")
        # The test repo has a README? No, just hello.txt and foo.py
        assert pulse.health.has_readme is False
        assert pulse.health.has_license is False


def test_health_metadata_checks():
    """Test health metadata file detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        # Add a README
        (repo / "README.md").write_text("# Test Repo\n")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-m", "Add README"],
            check=True,
            env=_git_env("2025-06-04T12:00:00"),
        )

        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()
        assert pulse.health.has_readme is True
        assert pulse.total_commits == 4


def test_bus_factor_single_author():
    """Test bus factor with a single author."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()
        assert pulse.health.bus_factor == 1


def test_bus_factor_multi_author():
    """Test bus factor with multiple authors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo_multi_author(Path(tmpdir))
        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()
        assert pulse.health.bus_factor >= 1
        assert pulse.health.unique_authors == 2


# ============================================================
# Author stats tests
# ============================================================


def test_author_detailed_stats():
    """Test detailed author statistics are computed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()
        key = "Test User <test@test.com>"
        assert key in pulse.authors
        a = pulse.authors[key]
        assert a.first_commit is not None
        assert a.last_commit is not None
        assert len(a.active_days) == 3


# ============================================================
# CLI tests
# ============================================================


def test_cli_summary():
    """Test the summary subcommand."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        result = main(["summary", str(repo), "--since", "2025-01-01", "--until", "2025-12-31"])
        assert result == 0


def test_cli_authors():
    """Test the authors subcommand."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        result = main(["authors", str(repo), "--since", "2025-01-01", "--until", "2025-12-31"])
        assert result == 0


def test_cli_timeline():
    """Test the timeline subcommand."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        result = main(["timeline", str(repo), "--since", "2025-01-01", "--until", "2025-12-31"])
        assert result == 0


def test_cli_timeline_weekly():
    """Test the timeline subcommand with weekly granularity."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        result = main(["timeline", str(repo), "--since", "2025-01-01", "--until", "2025-12-31", "--granularity", "week"])
        assert result == 0


def test_cli_activity():
    """Test the activity subcommand."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        result = main(["activity", str(repo), "--since", "2025-01-01", "--until", "2025-12-31"])
        assert result == 0


def test_cli_compare():
    """Test the compare subcommand."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        result = main(["compare", str(repo), "--since", "2025-01-01", "--until", "2025-12-31"])
        assert result == 0


def test_cli_report():
    """Test the report subcommand."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        result = main(["report", str(repo), "--since", "2025-01-01", "--until", "2025-12-31"])
        assert result == 0


def test_cli_report_markdown():
    """Test the report subcommand with markdown output."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        result = main(["report", str(repo), "--since", "2025-01-01", "--until", "2025-12-31", "--output", "markdown"])
        assert result == 0


def test_cli_health():
    """Test the health subcommand."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        result = main(["health", str(repo), "--since", "2025-01-01", "--until", "2025-12-31"])
        assert result == 0


def test_cli_churn():
    """Test the churn subcommand."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        result = main(["churn", str(repo), "--since", "2025-01-01", "--until", "2025-12-31"])
        assert result == 0


def test_cli_heatmap():
    """Test the heatmap subcommand."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        result = main(["heatmap", str(repo), "--since", "2025-01-01", "--until", "2025-12-31"])
        assert result == 0


def test_cli_dashboard():
    """Test the dashboard subcommand."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        result = main(["dashboard", str(repo), "--since", "2025-01-01", "--until", "2025-12-31"])
        assert result == 0


def test_cli_json_output():
    """Test JSON output flag."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        result = main(["summary", str(repo), "--since", "2025-01-01", "--until", "2025-12-31", "--json"])
        assert result == 0


def test_cli_default_to_summary():
    """Test that running with no subcommand defaults to summary."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        result = main([str(repo), "--since", "2025-01-01", "--until", "2025-12-31"])
        assert result == 0


def test_cli_nonexistent_path():
    """Test error handling for nonexistent path."""
    from gitpulse.cli import main
    result = main(["summary", "/nonexistent/path/xyz123"])
    assert result == 1


def test_cli_author_sort():
    """Test authors with different sort options."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        for sort_by in ["commits", "insertions", "deletions", "net", "active_days", "recent"]:
            result = main(["authors", str(repo), "--since", "2025-01-01", "--until", "2025-12-31", "--sort-by", sort_by])
            assert result == 0


def test_cli_churn_sort():
    """Test churn with different sort options."""
    from gitpulse.cli import main
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        for sort_by in ["total", "insertions", "deletions", "commits", "authors"]:
            result = main(["churn", str(repo), "--since", "2025-01-01", "--until", "2025-12-31", "--sort-by", sort_by])
            assert result == 0


# ============================================================
# Streak tests
# ============================================================


def test_streak_consecutive():
    """Test streak calculation with consecutive days."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()
        assert pulse.longest_streak == 3


def test_streak_non_consecutive():
    """Test streak with non-consecutive days."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir) / "gap-repo"
        repo.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", str(repo)], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test.com"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test User"], check=True)

        # Day 1
        (repo / "a.txt").write_text("a\n")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-m", "Day 1"],
            check=True, env=_git_env("2025-06-01T12:00:00"),
        )
        # Day 2
        (repo / "b.txt").write_text("b\n")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-m", "Day 2"],
            check=True, env=_git_env("2025-06-02T12:00:00"),
        )
        # Skip day 3
        # Day 4
        (repo / "c.txt").write_text("c\n")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-m", "Day 4"],
            check=True, env=_git_env("2025-06-04T12:00:00"),
        )
        # Day 5
        (repo / "d.txt").write_text("d\n")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-m", "Day 5"],
            check=True, env=_git_env("2025-06-05T12:00:00"),
        )

        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()
        assert pulse.total_commits == 4
        assert pulse.longest_streak == 2  # days 1-2 and days 4-5


# ============================================================
# RepoStats tests
# ============================================================


def test_repo_stats_from_pulse():
    """Test RepoStats.from_pulse factory method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()

        from gitpulse.stats import RepoStats
        stats = RepoStats.from_pulse(pulse)
        assert stats.total_commits == 3
        assert stats.unique_authors == 1
        assert stats.bus_factor >= 1


def test_repo_stats_format_numbers():
    """Test RepoStats.format_numbers output."""
    from gitpulse.stats import RepoStats
    stats = RepoStats(
        total_commits=100,
        total_insertions=5000,
        total_deletions=2000,
        active_days=50,
        longest_streak=10,
        current_streak=3,
        unique_authors=5,
        bus_factor=2,
        churn_ratio=0.286,
        freshness_days=2,
    )
    output = stats.format_numbers()
    assert "100" in output
    assert "5,000" in output
    assert "2,000" in output
    assert "28.6%" in output


# ============================================================
# Change type enum test
# ============================================================


def test_change_type_enum():
    """Test ChangeType enum values."""
    assert ChangeType.ADD.value == "A"
    assert ChangeType.MODIFY.value == "M"
    assert ChangeType.DELETE.value == "D"
    assert ChangeType.RENAME.value == "R"
    assert ChangeType.COPY.value == "C"


# ============================================================
# Heatmap module test
# ============================================================


def test_heatmap_render():
    """Test heatmap rendering doesn't crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()

        from gitpulse.heatmap import render_heatmap
        # Should not raise
        render_heatmap(pulse, datetime(2025, 1, 1), datetime(2025, 12, 31))


# ============================================================
# Display module test
# ============================================================


def test_dashboard_render():
    """Test dashboard rendering doesn't crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _make_repo(Path(tmpdir))
        pulse = GitPulse(
            path=repo,
            since=datetime(2025, 1, 1),
            until=datetime(2025, 12, 31),
            author=None,
            scan_repos=False,
        )
        pulse.analyze()

        from gitpulse.display import render_dashboard
        render_dashboard(pulse, datetime(2025, 1, 1), datetime(2025, 12, 31))


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
