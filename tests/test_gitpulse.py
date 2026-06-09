"""Test suite for gitpulse."""

import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from gitpulse.core import GitPulse, Commit, DayActivity


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
        assert pulse.longest_streak == 3  # consecutive days
        assert "Test User <test@test.com>" in pulse.authors
        assert pulse.authors["Test User <test@test.com>"] == 3


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
        assert pulse.total_commits == 6  # 3 per repo


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

        # Now filter by actual author
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

        import io

        buf = io.StringIO()
        pulse.to_json(buf)
        data = json.loads(buf.getvalue())

        assert data["total_commits"] == 3
        assert data["repo_count"] == 1
        assert data["active_days"] == 3


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


def test_commit_dataclass():
    """Test Commit dataclass creation."""
    c = Commit(
        hash="abc123",
        date=datetime(2025, 6, 1),
        author_name="Test",
        author_email="test@test.com",
        subject="Test commit",
        insertions=10,
        deletions=5,
        files_changed=2,
    )
    assert c.hash == "abc123"
    assert c.insertions == 10
    assert c.deletions == 5


def test_day_activity():
    """Test DayActivity dataclass."""
    d = DayActivity(date="2025-06-01")
    assert d.commits == 0
    d.commits = 5
    assert d.commits == 5


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
        # Commits are on June 1, 2, 3 — consecutive
        assert pulse.longest_streak == 3


if __name__ == "__main__":
    test_gitpulse_analyze_single_repo()
    test_gitpulse_scan_multiple_repos()
    test_gitpulse_author_filter()
    test_gitpulse_json_output()
    test_gitpulse_no_repo()
    test_commit_dataclass()
    test_day_activity()
    test_streak_consecutive()
    print("All tests passed!")
