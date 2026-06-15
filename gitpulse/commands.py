"""Handlers for gitpulse subcommands — each renders a specific analytics view."""

from __future__ import annotations

from datetime import datetime, timedelta

from .core import GitPulse


def handle_summary(pulse: GitPulse, since: datetime, until: datetime) -> None:
    """Show a quick summary of repository activity."""
    from .display import _bold, _cyan, _green, _magenta, _red, _yellow

    range_str = f"{since.strftime('%Y-%m-%d')} → {until.strftime('%Y-%m-%d')}"
    print()
    print(_bold(" ╔══════════════════════════════════════════╗"))
    print(_bold(" ║        🫀 gitpulse summary              ║"))
    print(_bold(" ╚══════════════════════════════════════════╝"))
    print()
    print(f" Period: {range_str}")
    if pulse.repo_count > 1:
        print(f" Repos: {pulse.repo_count}")
    print()
    print(f" Total commits:   {_cyan(str(pulse.total_commits))}")
    print(f" Lines added:     {_green(f'+{pulse.total_insertions:,}')}")
    print(f" Lines removed:   {_red(f'-{pulse.total_deletions:,}')}")
    net = pulse.total_insertions - pulse.total_deletions
    net_str = f"+{net:,}" if net >= 0 else f"{net:,}"
    print(f" Net lines:       {_yellow(net_str)}")
    print(f" Active days:     {_cyan(str(pulse.active_days))}")
    print(f" Longest streak:  {_magenta(str(pulse.longest_streak) + ' days')}")
    print(f" Current streak:  {_magenta(str(pulse.current_streak) + ' days')}")
    print(f" Unique authors:  {_cyan(str(len(pulse.authors)))}")
    h = pulse.health
    print(f" Bus factor:      {_yellow(str(h.bus_factor))}")
    print(f" Churn ratio:     {_yellow(f'{h.churn_ratio:.1%}')}")
    print(
        f" Last commit:     {_cyan(str(h.freshness_days) + ' days ago') if h.freshness_days > 0 else _green('today')}"
    )
    print()


def handle_authors(
    pulse: GitPulse,
    since: datetime,
    until: datetime,
    sort_by: str = "commits",
    limit: int = 20,
) -> None:
    """Show detailed author breakdown."""
    from .display import _bold, _cyan, _green, _red, _yellow

    print()
    print(_bold(" ╔══════════════════════════════════════════╗"))
    print(_bold(" ║        👥 gitpulse authors              ║"))
    print(_bold(" ╚══════════════════════════════════════════╝"))
    print()

    if not pulse.authors:
        print(" No author data found.")
        print()
        return

    # Sort authors
    authors_list = list(pulse.authors.values())
    sort_key = {
        "commits": lambda a: a.commits,
        "insertions": lambda a: a.insertions,
        "deletions": lambda a: a.deletions,
        "net": lambda a: a.net_lines,
        "active_days": lambda a: len(a.active_days),
        "recent": lambda a: a.last_commit or datetime.min,
    }.get(sort_by, lambda a: a.commits)
    authors_list.sort(key=sort_key, reverse=True)

    # Header
    print(f" {'Author':<30} {'Commits':>8} {'Added':>8} {'Removed':>8} {'Net':>8} {'Days':>6}")
    print(f" {'─' * 30} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 6}")

    for a in authors_list[:limit]:
        name = a.name[:28] if len(a.name) > 28 else a.name
        net = a.net_lines
        net_str = f"+{net:,}" if net >= 0 else f"{net:,}"
        days = len(a.active_days)
        print(
            f" {name:<30} {_cyan(str(a.commits)):>8} {_green(f'+{a.insertions:,}'):>8}"
            f" {_red(f'-{a.deletions:,}'):>8} {_yellow(net_str):>8} {days!s:>6}"
        )

    # Summary line
    total_commits = sum(a.commits for a in authors_list)
    total_ins = sum(a.insertions for a in authors_list)
    total_del = sum(a.deletions for a in authors_list)
    print()
    print(
        f" {'TOTAL':<30} {_cyan(str(total_commits)):>8} {_green(f'+{total_ins:,}'):>8} {_red(f'-{total_del:,}'):>8}"
    )
    print()

    # Commit distribution bar chart
    print(_bold(" ── Commit Distribution ──"))
    max_commits = max(a.commits for a in authors_list) if authors_list else 1
    for a in authors_list[:10]:
        bar_len = int(a.commits / max(max_commits, 1) * 30)
        bar = "█" * bar_len
        name = a.name[:20] if len(a.name) > 20 else a.name
        print(f" {name:<22} {_cyan(str(a.commits)):>5} {bar}")
    print()


def handle_timeline(
    pulse: GitPulse,
    since: datetime,
    until: datetime,
    granularity: str = "month",
) -> None:
    """Show commit activity over time."""
    from .display import _bold, _cyan, _green, _red

    print()
    print(_bold(" ╔══════════════════════════════════════════╗"))
    print(_bold(" ║        📅 gitpulse timeline             ║"))
    print(_bold(" ╚══════════════════════════════════════════╝"))
    print()

    if granularity == "week":
        buckets = sorted(pulse.weekly.items())
        if not buckets:
            print(" No activity data found.")
            print()
            return

        print(
            f" {'Week':<10} {'Commits':>8} {'Added':>10} {'Removed':>10} {'Days':>6} {'Activity':>30}"
        )
        print(f" {'─' * 10} {'─' * 8} {'─' * 10} {'─' * 10} {'─' * 6} {'─' * 30}")

        max_commits = max(w.commits for _, w in buckets) if buckets else 1
        for (year, week), w in buckets:
            label = f"{year}-W{week:02d}"
            bar_len = int(w.commits / max(max_commits, 1) * 30)
            bar = "█" * bar_len
            print(
                f" {label:<10} {_cyan(str(w.commits)):>8} {_green(f'+{w.insertions:,}'):>10}"
                f" {_red(f'-{w.deletions:,}'):>10} {w.active_days!s:>6} {bar}"
            )
    else:
        buckets = sorted(pulse.monthly.items())
        if not buckets:
            print(" No activity data found.")
            print()
            return

        print(
            f" {'Month':<10} {'Commits':>8} {'Added':>10} {'Removed':>10} {'Days':>6} {'Activity':>30}"
        )
        print(f" {'─' * 10} {'─' * 8} {'─' * 10} {'─' * 10} {'─' * 6} {'─' * 30}")

        max_commits = max(m.commits for _, m in buckets) if buckets else 1
        for (year, month), m in buckets:
            label = m.label
            bar_len = int(m.commits / max(max_commits, 1) * 30)
            bar = "█" * bar_len
            print(
                f" {label:<10} {_cyan(str(m.commits)):>8} {_green(f'+{m.insertions:,}'):>10}"
                f" {_red(f'-{m.deletions:,}'):>10} {m.active_days!s:>6} {bar}"
            )

    print()


def handle_activity(
    pulse: GitPulse,
    since: datetime,
    until: datetime,
) -> None:
    """Show hourly and day-of-week activity patterns."""
    from .display import _bold, _cyan, _magenta

    print()
    print(_bold(" ╔══════════════════════════════════════════╗"))
    print(_bold(" ║        ⏰ gitpulse activity             ║"))
    print(_bold(" ╚══════════════════════════════════════════╝"))
    print()

    if not pulse.commits:
        print(" No commit data found.")
        print()
        return

    # Hour-of-day distribution
    hour_counts: dict[int, int] = dict.fromkeys(range(24), 0)
    for commit in pulse.commits:
        hour_counts[commit.date.hour] = hour_counts.get(commit.date.hour, 0) + 1

    max_hour = max(hour_counts.values()) if hour_counts else 1
    print(_bold(" ── Commits by Hour of Day ──"))
    print()
    for hour in range(24):
        count = hour_counts.get(hour, 0)
        bar_len = int(count / max(max_hour, 1) * 40)
        bar = "█" * bar_len
        label = f"{hour:02d}:00"
        color = _cyan if count > 0 else lambda s: s
        print(f" {label} {color(str(count)):>4} {bar}")

    # Peak hour
    peak_hour = max(hour_counts, key=hour_counts.get)  # type: ignore[arg-type]
    print()
    print(f" Peak hour: {_magenta(f'{peak_hour:02d}:00')} ({hour_counts[peak_hour]} commits)")

    # Day-of-week distribution
    print()
    print(_bold(" ── Commits by Day of Week ──"))
    print()
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_counts: dict[int, int] = dict.fromkeys(range(7), 0)
    for commit in pulse.commits:
        day_counts[commit.date.weekday()] = day_counts.get(commit.date.weekday(), 0) + 1

    max_day = max(day_counts.values()) if day_counts else 1
    for d in range(7):
        count = day_counts.get(d, 0)
        bar_len = int(count / max(max_day, 1) * 40)
        bar = "█" * bar_len
        print(f" {day_names[d]:<10} {_cyan(str(count)):>5} {bar}")

    peak_day_idx = max(day_counts, key=day_counts.get)  # type: ignore[arg-type]
    print()
    print(
        f" Most active day: {_magenta(day_names[peak_day_idx])} ({day_counts[peak_day_idx]} commits)"
    )

    # Weekend vs weekday
    weekday_commits = sum(day_counts.get(d, 0) for d in range(5))
    weekend_commits = sum(day_counts.get(d, 0) for d in range(5, 7))
    total = weekday_commits + weekend_commits
    if total > 0:
        print(
            f" Weekday: {weekday_commits} ({weekday_commits / total:.0%}) · Weekend: {weekend_commits} ({weekend_commits / total:.0%})"
        )
    print()


def handle_compare(
    pulse: GitPulse,
    since: datetime,
    until: datetime,
    period_days: int = 30,
) -> None:
    """Compare current period vs previous period of equal length."""
    from .display import _bold, _cyan, _green, _red

    print()
    print(_bold(" ╔══════════════════════════════════════════╗"))
    print(_bold(" ║        📊 gitpulse compare              ║"))
    print(_bold(" ╚══════════════════════════════════════════╝"))
    print()

    # Current period stats
    current_commits = pulse.total_commits
    current_ins = pulse.total_insertions
    current_del = pulse.total_deletions
    current_active = pulse.active_days
    current_authors = len(pulse.authors)

    # Previous period — re-analyze
    prev_until = since
    prev_since = since - timedelta(days=period_days)
    from .core import GitPulse as GP

    prev_pulse = GP(
        path=pulse.path,
        since=prev_since,
        until=prev_until,
        author=pulse.author,
        scan_repos=pulse.scan_repos,
    )
    try:
        prev_pulse.analyze()
    except Exception:
        prev_pulse = None

    prev_commits = prev_pulse.total_commits if prev_pulse else 0
    prev_ins = prev_pulse.total_insertions if prev_pulse else 0
    prev_del = prev_pulse.total_deletions if prev_pulse else 0
    prev_active = prev_pulse.active_days if prev_pulse else 0
    prev_authors = len(prev_pulse.authors) if prev_pulse else 0

    current_label = f"Last {period_days}d"
    prev_label = f"Prev {period_days}d"

    def _delta(cur: int, prev: int) -> str:
        if prev == 0 and cur == 0:
            return "  —"
        if prev == 0:
            return "  +∞"
        change = ((cur - prev) / prev) * 100
        if change >= 0:
            return f"  {_green(f'+{change:.0%}')}"
        return f"  {_red(f'{change:.0%}')}"

    print(f" {'Metric':<18} {current_label:>12} {prev_label:>12} {'Change':>12}")
    print(f" {'─' * 18} {'─' * 12} {'─' * 12} {'─' * 12}")
    print(
        f" {'Commits':<18} {current_commits!s:>12} {prev_commits!s:>12} {_delta(current_commits, prev_commits)}"
    )
    print(
        f" {'Insertions':<18} {f'+{current_ins:,}':>12} {f'+{prev_ins:,}':>12} {_delta(current_ins, prev_ins)}"
    )
    print(
        f" {'Deletions':<18} {f'-{current_del:,}':>12} {f'-{prev_del:,}':>12} {_delta(current_del, prev_del)}"
    )
    print(
        f" {'Active days':<18} {current_active!s:>12} {prev_active!s:>12} {_delta(current_active, prev_active)}"
    )
    print(
        f" {'Authors':<18} {current_authors!s:>12} {prev_authors!s:>12} {_delta(current_authors, prev_authors)}"
    )

    # Visual comparison
    print()
    print(_bold(" ── Visual Comparison ──"))
    metrics = [
        ("Commits", current_commits, prev_commits),
        ("Insertions", current_ins, prev_ins),
        ("Deletions", current_del, prev_del),
    ]
    max_val = max(max(c, p) for _, c, p in metrics) if metrics else 1
    for name, cur, prev in metrics:
        cur_bar = "█" * int(cur / max(max_val, 1) * 25)
        prev_bar = "░" * int(prev / max(max_val, 1) * 25)
        print(f" {name:<12} {_green(cur_bar)} {_cyan(str(cur))}")
        print(f" {'':>12} {_red(prev_bar)} {prev!s}")
    print()


def handle_report(
    pulse: GitPulse,
    since: datetime,
    until: datetime,
    output: str = "text",
) -> None:
    """Generate a comprehensive text or markdown report."""
    from .display import _bold

    if output == "markdown":
        _report_markdown(pulse, since, until)
        return

    print()
    print(_bold(" ╔══════════════════════════════════════════╗"))
    print(_bold(" ║        📋 gitpulse report               ║"))
    print(_bold(" ╚══════════════════════════════════════════╝"))
    print()

    range_str = f"{since.strftime('%Y-%m-%d')} → {until.strftime('%Y-%m-%d')}"
    print(f" Period: {range_str}")
    if pulse.repo_count > 1:
        print(f" Repos: {pulse.repo_count}")
    print()

    # Overview
    print(_bold(" ── Overview ──"))
    net = pulse.total_insertions - pulse.total_deletions
    net_str = f"+{net:,}" if net >= 0 else f"{net:,}"
    print(f" Total commits:       {pulse.total_commits:,}")
    print(f" Lines added:         +{pulse.total_insertions:,}")
    print(f" Lines removed:       -{pulse.total_deletions:,}")
    print(f" Net lines:           {net_str}")
    print(f" Active days:         {pulse.active_days:,}")
    print(f" Longest streak:      {pulse.longest_streak} days")
    print(f" Current streak:      {pulse.current_streak} days")
    print(f" Unique authors:      {len(pulse.authors)}")
    print()

    # Health
    h = pulse.health
    print(_bold(" ── Health ──"))
    print(f" Activity score:      {h.activity_score}/100 (Grade: {h.health_grade})")
    print(f" Bus factor:          {h.bus_factor}")
    print(f" Churn ratio:         {h.churn_ratio:.1%}")
    print(f" Freshness:           {h.freshness_days} days since last commit")
    print(f" README:              {'✓' if h.has_readme else '✗'}")
    print(f" CONTRIBUTING:        {'✓' if h.has_contributing else '✗'}")
    print(f" LICENSE:             {'✓' if h.has_license else '✗'}")
    print(f" CI config:           {'✓' if h.has_ci else '✗'}")
    print(f" File count:          {h.file_count:,}")
    print()

    # Top authors
    if pulse.authors:
        print(_bold(" ── Top Authors ──"))
        sorted_authors = sorted(pulse.authors.values(), key=lambda a: a.commits, reverse=True)
        for a in sorted_authors[:10]:
            span = ""
            if a.first_commit and a.last_commit:
                span = f" ({a.first_commit.strftime('%Y-%m-%d')} → {a.last_commit.strftime('%Y-%m-%d')})"
            print(f" {a.name:<25} {a.commits:>5} commits, +{a.insertions:,}/-{a.deletions:,}{span}")
        print()

    # Top churned files
    if pulse.file_churn:
        print(_bold(" ── Most Churned Files ──"))
        sorted_churn = sorted(pulse.file_churn.values(), key=lambda f: f.total_churn, reverse=True)
        for fc in sorted_churn[:10]:
            print(
                f" {fc.path:<40} churn={fc.total_churn:,}  +{fc.insertions:,}/-{fc.deletions:,}  ({fc.commits} commits, {len(fc.authors)} authors)"
            )
        print()

    # Extension breakdown
    if pulse.extension_churn:
        print(_bold(" ── By Extension ──"))
        sorted_ext = sorted(
            pulse.extension_churn.values(), key=lambda e: e.total_churn, reverse=True
        )
        for ec in sorted_ext[:10]:
            print(
                f" .{ec.extension:<10} churn={ec.total_churn:,}  +{ec.insertions:,}/-{ec.deletions:,}  ({ec.files} files)"
            )
        print()

    # Monthly breakdown
    if pulse.monthly:
        print(_bold(" ── Monthly Breakdown ──"))
        sorted_months = sorted(pulse.monthly.values(), key=lambda m: (m.year, m.month))
        print(f" {'Month':<10} {'Commits':>8} {'Added':>10} {'Removed':>10} {'Days':>6}")
        print(f" {'─' * 10} {'─' * 8} {'─' * 10} {'─' * 10} {'─' * 6}")
        for m in sorted_months:
            print(
                f" {m.label:<10} {m.commits!s:>8} {f'+{m.insertions:,}':>10} {f'-{m.deletions:,}':>10} {m.active_days!s:>6}"
            )
        print()


def _report_markdown(pulse: GitPulse, since: datetime, until: datetime) -> None:
    """Generate a markdown report."""
    range_str = f"{since.strftime('%Y-%m-%d')} → {until.strftime('%Y-%m-%d')}"

    print("# 🫀 GitPulse Report")
    print()
    print(f"**Period:** {range_str}")
    if pulse.repo_count > 1:
        print(f"**Repos:** {pulse.repo_count}")
    print()

    # Overview
    net = pulse.total_insertions - pulse.total_deletions
    net_str = f"+{net:,}" if net >= 0 else f"{net:,}"
    print("## Overview")
    print()
    print("| Metric | Value |")
    print("|--------|-------|")
    print(f"| Total commits | {pulse.total_commits:,} |")
    print(f"| Lines added | +{pulse.total_insertions:,} |")
    print(f"| Lines removed | -{pulse.total_deletions:,} |")
    print(f"| Net lines | {net_str} |")
    print(f"| Active days | {pulse.active_days:,} |")
    print(f"| Longest streak | {pulse.longest_streak} days |")
    print(f"| Current streak | {pulse.current_streak} days |")
    print(f"| Unique authors | {len(pulse.authors)} |")
    print()

    # Health
    h = pulse.health
    print("## Health")
    print()
    print("| Metric | Value |")
    print("|--------|-------|")
    print(f"| Activity score | {h.activity_score}/100 ({h.health_grade}) |")
    print(f"| Bus factor | {h.bus_factor} |")
    print(f"| Churn ratio | {h.churn_ratio:.1%} |")
    print(f"| Freshness | {h.freshness_days} days |")
    print(f"| README | {'✓' if h.has_readme else '✗'} |")
    print(f"| LICENSE | {'✓' if h.has_license else '✗'} |")
    print(f"| CI | {'✓' if h.has_ci else '✗'} |")
    print()

    # Top authors
    if pulse.authors:
        print("## Top Authors")
        print()
        print("| Author | Commits | Added | Removed |")
        print("|--------|---------|-------|---------|")
        sorted_authors = sorted(pulse.authors.values(), key=lambda a: a.commits, reverse=True)
        for a in sorted_authors[:10]:
            print(f"| {a.name} | {a.commits} | +{a.insertions:,} | -{a.deletions:,} |")
        print()

    # Top churned files
    if pulse.file_churn:
        print("## Most Churned Files")
        print()
        print("| File | Churn | Added | Removed | Commits |")
        print("|------|-------|-------|---------|---------|")
        sorted_churn = sorted(pulse.file_churn.values(), key=lambda f: f.total_churn, reverse=True)
        for fc in sorted_churn[:10]:
            print(
                f"| `{fc.path}` | {fc.total_churn:,} | +{fc.insertions:,} | -{fc.deletions:,} | {fc.commits} |"
            )
        print()

    # Monthly breakdown
    if pulse.monthly:
        print("## Monthly Breakdown")
        print()
        print("| Month | Commits | Added | Removed | Active Days |")
        print("|-------|---------|-------|---------|-------------|")
        sorted_months = sorted(pulse.monthly.values(), key=lambda m: (m.year, m.month))
        for m in sorted_months:
            print(
                f"| {m.label} | {m.commits} | +{m.insertions:,} | -{m.deletions:,} | {m.active_days} |"
            )
        print()


def handle_health(
    pulse: GitPulse,
    since: datetime,
    until: datetime,
) -> None:
    """Show repository health assessment."""
    from .display import _bold, _green, _red, _yellow

    h = pulse.health

    print()
    print(_bold(" ╔══════════════════════════════════════════╗"))
    print(_bold(" ║        🏥 gitpulse health              ║"))
    print(_bold(" ╚══════════════════════════════════════════╝"))
    print()

    # Activity Score with visual gauge
    score = h.activity_score
    grade = h.health_grade
    gauge_len = 40
    filled = int(score / 100 * gauge_len)
    gauge = "█" * filled + "░" * (gauge_len - filled)

    grade_color = _green if grade in ("A", "B") else (_yellow if grade == "C" else _red)
    print(_bold(" ── Activity Score ──"))
    print(f" [{gauge}] {score}/100  Grade: {grade_color(grade)}")
    print()

    # Score breakdown
    if h.total_days > 0:
        frequency_score = min(h.active_days / max(h.total_days, 1), 1.0) * 40
        recency_score = max(0, 30 - h.freshness_days) / 30 * 30
        streak_score = min(h.longest_streak / 30, 1.0) * 15
        diversity_score = min(h.unique_authors / 5, 1.0) * 15
        print(
            f" Frequency:  {frequency_score:.0f}/40  (active {h.active_days} of {h.total_days} days)"
        )
        print(f" Recency:    {recency_score:.0f}/30  ({h.freshness_days} days since last commit)")
        print(f" Streak:     {streak_score:.0f}/15  (longest: {h.longest_streak} days)")
        print(f" Diversity:  {diversity_score:.0f}/15  ({h.unique_authors} authors)")
    print()

    # Bus Factor
    print(_bold(" ── Bus Factor ──"))
    bus_color = _green if h.bus_factor >= 3 else (_yellow if h.bus_factor == 2 else _red)
    print(f" Bus factor: {bus_color(str(h.bus_factor))}")
    if pulse.authors:
        sorted_authors = sorted(pulse.authors.values(), key=lambda a: a.commits, reverse=True)
        total = pulse.total_commits
        accumulated = 0
        shown = False
        for i, a in enumerate(sorted_authors):
            accumulated += a.commits
            pct = a.commits / total * 100 if total > 0 else 0
            marker = " ◄── 50% threshold" if not shown and accumulated >= total * 0.5 else ""
            if not shown and accumulated >= total * 0.5:
                shown = True
            print(f"  {i + 1}. {a.name:<25} {a.commits:>5} commits ({pct:.0%}){marker}")
    print()

    # Churn Analysis
    print(_bold(" ── Churn Analysis ──"))
    churn_color = _green if h.churn_ratio < 0.3 else (_yellow if h.churn_ratio < 0.5 else _red)
    print(f" Churn ratio: {churn_color(f'{h.churn_ratio:.1%}')}")
    total_lines = pulse.total_insertions + pulse.total_deletions
    if total_lines > 0:
        print(
            f" Stable lines: {pulse.total_insertions - pulse.total_deletions:,} of {total_lines:,} total touched"
        )
    print()

    # Repo metadata
    print(_bold(" ── Repository Metadata ──"))
    checks = [
        ("README", h.has_readme),
        ("CONTRIBUTING", h.has_contributing),
        ("LICENSE", h.has_license),
        ("CI config", h.has_ci),
    ]
    for name, present in checks:
        status = _green("✓ Present") if present else _red("✗ Missing")
        print(f" {name:<15} {status}")
    if h.file_count > 0:
        print(f" File count:      {h.file_count:,}")
        print(f" Max depth:       {h.directory_depth} levels")
    print()

    # Recommendations
    print(_bold(" ── Recommendations ──"))
    recs = []
    if not h.has_readme:
        recs.append("Add a README.md to document your project")
    if not h.has_license:
        recs.append("Add a LICENSE file to clarify usage terms")
    if not h.has_contributing:
        recs.append("Add CONTRIBUTING.md to guide new contributors")
    if not h.has_ci:
        recs.append("Set up CI/CD to automate testing")
    if h.bus_factor == 1:
        recs.append("Critical: Only 1 author owns 50%+ of commits — knowledge concentration risk")
    if h.churn_ratio > 0.5:
        recs.append("High churn ratio — consider stabilizing frequently rewritten files")
    if h.freshness_days > 90:
        recs.append(
            f"Repo has been inactive for {h.freshness_days} days — consider archiving or updating"
        )
    if not recs:
        recs.append("Repository looks healthy! Keep up the good work.")
    for rec in recs:
        print(f" • {rec}")
    print()


def handle_churn(
    pulse: GitPulse,
    since: datetime,
    until: datetime,
    sort_by: str = "total",
    limit: int = 20,
) -> None:
    """Show file and extension churn analysis."""
    from .display import _bold, _green, _red, _yellow

    print()
    print(_bold(" ╔══════════════════════════════════════════╗"))
    print(_bold(" ║        🔥 gitpulse churn               ║"))
    print(_bold(" ╚══════════════════════════════════════════╝"))
    print()

    # File churn
    if pulse.file_churn:
        sort_key = {
            "total": lambda f: f.total_churn,
            "insertions": lambda f: f.insertions,
            "deletions": lambda f: f.deletions,
            "commits": lambda f: f.commits,
            "authors": lambda f: len(f.authors),
        }.get(sort_by, lambda f: f.total_churn)

        sorted_files = sorted(pulse.file_churn.values(), key=sort_key, reverse=True)

        print(_bold(" ── Most Churned Files ──"))
        print()
        print(
            f" {'File':<40} {'Churn':>8} {'Added':>8} {'Removed':>8} {'Commits':>8} {'Authors':>8}"
        )
        print(f" {'─' * 40} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 8}")

        for fc in sorted_files[:limit]:
            path = fc.path[:38] if len(fc.path) > 38 else fc.path
            print(
                f" {path:<40} {_yellow(str(fc.total_churn)):>8} {_green(f'+{fc.insertions:,}'):>8}"
                f" {_red(f'-{fc.deletions:,}'):>8} {fc.commits!s:>8} {len(fc.authors)!s:>8}"
            )

        # Visual bar
        print()
        max_churn = max(f.total_churn for f in sorted_files[:limit]) if sorted_files[:limit] else 1
        for fc in sorted_files[:10]:
            bar_len = int(fc.total_churn / max(max_churn, 1) * 35)
            bar = "█" * bar_len
            path = fc.path[:30] if len(fc.path) > 30 else fc.path
            print(f" {path:<32} {_yellow(str(fc.total_churn)):>6} {bar}")
        print()

    # Extension churn
    if pulse.extension_churn:
        sorted_ext = sorted(
            pulse.extension_churn.values(), key=lambda e: e.total_churn, reverse=True
        )

        print(_bold(" ── Churn by Extension ──"))
        print()
        print(f" {'Extension':<12} {'Churn':>10} {'Added':>10} {'Removed':>10} {'Files':>8}")
        print(f" {'─' * 12} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 8}")

        for ec in sorted_ext[:15]:
            print(
                f" .{ec.extension:<11} {_yellow(str(ec.total_churn)):>10} {_green(f'+{ec.insertions:,}'):>10}"
                f" {_red(f'-{ec.deletions:,}'):>10} {ec.files!s:>8}"
            )
        print()

    # Hotspots: files edited by many authors
    if pulse.file_churn:
        multi_author = [f for f in pulse.file_churn.values() if len(f.authors) > 1]
        if multi_author:
            multi_author.sort(key=lambda f: len(f.authors), reverse=True)
            print(_bold(" ── Collaboration Hotspots ──"))
            print(" Files edited by multiple authors (potential coordination points):")
            print()
            for fc in multi_author[:10]:
                path = fc.path[:45] if len(fc.path) > 45 else fc.path
                print(f" {path:<47} {len(fc.authors)} authors, {fc.commits} edits")
            print()

    if not pulse.file_churn and not pulse.extension_churn:
        print(" No churn data found. Commit some changes and try again.")
        print()
