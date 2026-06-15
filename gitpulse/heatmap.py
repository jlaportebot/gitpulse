"""Contribution heatmap renderer — GitHub-style year view in the terminal."""

from __future__ import annotations

from datetime import datetime, timedelta

from .core import GitPulse

# Block characters for heatmap intensity levels
BLOCKS = ["░", "▒", "▓", "█"]
DAY_LABELS = ["Mon", "   ", "Wed", "   ", "Fri", "   ", "Sun"]


def render_heatmap(pulse: GitPulse, since: datetime, until: datetime) -> None:
    """Render a GitHub-style contribution heatmap for the last 52 weeks."""
    # Build a 53-week x 7-day grid
    weeks = 53
    grid: list[list[int]] = [[0] * 7 for _ in range(weeks)]

    # Figure out the starting Monday
    today = until.date()
    today_weekday = today.weekday()  # Mon=0
    last_sunday = today + timedelta(days=(6 - today_weekday))
    grid_start = last_sunday - timedelta(weeks=weeks - 1)
    # grid_start should be a Monday
    grid_start = grid_start - timedelta(days=grid_start.weekday())

    for day_key, activity in pulse.daily.items():
        day_date = datetime.strptime(day_key, "%Y-%m-%d").date()
        if day_date < grid_start or day_date > last_sunday:
            continue
        delta = day_date - grid_start
        week_idx = delta.days // 7
        day_idx = day_date.weekday()  # Mon=0
        if 0 <= week_idx < weeks and 0 <= day_idx < 7:
            grid[week_idx][day_idx] = activity.commits

    # Find max for scaling
    max_commits = max(max(col) for col in grid) if any(any(c for c in col) for col in grid) else 1
    if max_commits == 0:
        max_commits = 1

    # Month labels
    months = _month_labels(grid_start, weeks)

    # Render
    print()
    print("  \033[1mContribution Heatmap\033[0m")
    print()

    # Month header
    header = "    "  # space for day labels
    for w in range(weeks):
        if months[w]:
            header += months[w]
            # Pad to align (each week is 2 chars wide)
        else:
            header += "  "
    print(header[: weeks * 2 + 4])

    # Day rows
    for day in range(7):
        label = DAY_LABELS[day]
        row = f"{label} "
        for w in range(weeks):
            count = grid[w][day]
            level = _level(count, max_commits)
            color = _color(level)
            row += f"{color}{BLOCKS[level]}\033[0m"
        print(row)

    # Legend
    print()
    less_color = _color(0)
    low_color = _color(1)
    med_color = _color(2)
    high_color = _color(3)
    blocks = BLOCKS
    print(
        f"    Less {less_color}{blocks[0]}\\033[0m"
        f"{low_color}{blocks[1]}\\033[0m"
        f"{med_color}{blocks[2]}\\033[0m"
        f"{high_color}{blocks[3]}\\033[0m More"
    )

    # Stats line
    print(f"    {pulse.total_commits} commits in the last year · {pulse.active_days} active days")


def _level(count: int, max_val: int) -> int:
    """Map a count to a 0-3 intensity level."""
    if count == 0:
        return 0
    ratio = count / max_val
    if ratio <= 0.25:
        return 1
    if ratio <= 0.50:
        return 2
    return 3


def _color(level: int) -> str:
    """Return ANSI color code for a heatmap level."""
    colors = [
        "\033[38;5;236m",  # empty / dark gray
        "\033[38;5;28m",  # low / green
        "\033[38;5;34m",  # medium / bright green
        "\033[38;5;46m",  # high / neon green
    ]
    return colors[level]


def _month_labels(start, weeks: int) -> list[str]:
    """Return month abbreviation labels aligned to weeks."""
    labels = [""] * weeks
    prev_month = -1
    for w in range(weeks):
        week_date = start + timedelta(weeks=w)
        month = week_date.month
        if month != prev_month:
            labels[w] = week_date.strftime("%b")[:3]
            prev_month = month
        else:
            labels[w] = "   "
    return labels
