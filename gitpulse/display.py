"""Dashboard renderer — pretty terminal output for gitpulse."""

from __future__ import annotations

from datetime import datetime

from .core import GitPulse


def render_dashboard(pulse: GitPulse, since: datetime, until: datetime) -> None:
    """Render the full gitpulse dashboard."""
    print()
    print(_bold(" ╔══════════════════════════════════════════╗"))
    print(_bold(" ║ 🫀 gitpulse dashboard                  ║"))
    print(_bold(" ╚══════════════════════════════════════════╝"))
    print()

    # Overview
    range_str = f"{since.strftime('%Y-%m-%d')} → {until.strftime('%Y-%m-%d')}"
    print(f" Period: {range_str}")
    if pulse.repo_count > 1:
        print(f" Repos: {pulse.repo_count}")
    print()

    # Stats box
    print(_bold(" ── Overview ──"))
    print(f" Total commits: {_cyan(str(pulse.total_commits))}")
    print(f" Lines added: {_green(f'+{pulse.total_insertions:,}')}")
    print(f" Lines removed: {_red(f'-{pulse.total_deletions:,}')}")
    net = pulse.total_insertions - pulse.total_deletions
    net_str = f"+{net:,}" if net >= 0 else f"{net:,}"
    print(f" Net lines: {_yellow(net_str)}")
    print(f" Active days: {_cyan(str(pulse.active_days))}")
    print(f" Longest streak: {_magenta(str(pulse.longest_streak) + ' days')}")
    print(f" Current streak: {_magenta(str(pulse.current_streak) + ' days')}")
    if pulse.authors:
        print(f" Unique authors: {_cyan(str(len(pulse.authors)))}")
    print()

    # Top authors
    if pulse.authors:
        print(_bold(" ── Top Authors ──"))
        sorted_authors = sorted(pulse.authors.items(), key=lambda x: x[1].commits, reverse=True)
        for author_key, a in sorted_authors[:5]:
            bar = "█" * min(a.commits, 30)
            display_name = a.name if len(a.name) <= 35 else a.name[:32] + "..."
            print(f" {display_name:<36} {_cyan(str(a.commits)):>4} {bar}")
        print()

    # Recent commits
    if pulse.commits:
        print(_bold(" ── Recent Commits ──"))
        for commit in pulse.commits[-10:]:
            short_hash = commit.hash[:7]
            date_str = commit.date.strftime("%Y-%m-%d %H:%M")
            subject = commit.subject[:50]
            print(f" {_yellow(short_hash)} {date_str} {subject}")
        print()

    # Health hint
    if pulse.health.activity_score > 0:
        print(
            f" Health: {_bold(str(pulse.health.activity_score))}/100 (Grade: {pulse.health.health_grade})"
        )

    # Hint
    print(
        f" Tip: Run {_bold('gitpulse authors')}, {_bold('gitpulse timeline')}, {_bold('gitpulse health')} for more"
    )
    print()


# ANSI helpers (used by commands.py too)


def _bold(s: str) -> str:
    return f"\033[1m{s}\033[0m"


def _cyan(s: str) -> str:
    return f"\033[36m{s}\033[0m"


def _green(s: str) -> str:
    return f"\033[32m{s}\033[0m"


def _red(s: str) -> str:
    return f"\033[31m{s}\033[0m"


def _yellow(s: str) -> str:
    return f"\033[33m{s}\033[0m"


def _magenta(s: str) -> str:
    return f"\033[35m{s}\033[0m"
