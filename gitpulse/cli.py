"""Command-line interface for gitpulse — subcommand-based CLI."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from .commands import (
    handle_activity,
    handle_authors,
    handle_churn,
    handle_compare,
    handle_health,
    handle_report,
    handle_summary,
    handle_timeline,
)
from .core import GitPulse
from .display import render_dashboard
from .heatmap import render_heatmap


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gitpulse",
        description="Beautiful Git activity dashboard and analytics in your terminal.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__import__('gitpulse').__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
    )

    # Common arguments shared across subcommands
    def _add_common_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "path",
            nargs="?",
            default=".",
            help="Path to a git repository or directory (default: .)",
        )
        sp.add_argument(
            "--since",
            type=str,
            default=None,
            help="Start date (YYYY-MM-DD or Nd for N days ago)",
        )
        sp.add_argument(
            "--until",
            type=str,
            default=None,
            help="End date (YYYY-MM-DD, default: today)",
        )
        sp.add_argument(
            "--author",
            type=str,
            default=None,
            help="Filter commits by author name or email",
        )
        sp.add_argument(
            "--repos",
            action="store_true",
            help="Scan directory for multiple git repos",
        )
        sp.add_argument(
            "--json",
            action="store_true",
            dest="output_json",
            help="Output results as JSON",
        )

    # summary
    p_summary = subparsers.add_parser(
        "summary",
        help="Quick repository activity summary",
    )
    _add_common_args(p_summary)

    # authors
    p_authors = subparsers.add_parser(
        "authors",
        help="Detailed author breakdown and rankings",
    )
    _add_common_args(p_authors)
    p_authors.add_argument(
        "--sort-by",
        choices=["commits", "insertions", "deletions", "net", "active_days", "recent"],
        default="commits",
        help="Sort authors by metric (default: commits)",
    )
    p_authors.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max authors to show (default: 20)",
    )

    # timeline
    p_timeline = subparsers.add_parser(
        "timeline",
        help="Commit activity over time (monthly or weekly)",
    )
    _add_common_args(p_timeline)
    p_timeline.add_argument(
        "--granularity",
        choices=["month", "week"],
        default="month",
        help="Time bucket size (default: month)",
    )

    # activity
    p_activity = subparsers.add_parser(
        "activity",
        help="Hourly and day-of-week commit patterns",
    )
    _add_common_args(p_activity)

    # compare
    p_compare = subparsers.add_parser(
        "compare",
        help="Compare current period vs previous period",
    )
    _add_common_args(p_compare)
    p_compare.add_argument(
        "--period",
        type=int,
        default=30,
        help="Period length in days for comparison (default: 30)",
    )

    # report
    p_report = subparsers.add_parser(
        "report",
        help="Generate comprehensive analysis report",
    )
    _add_common_args(p_report)
    p_report.add_argument(
        "--output",
        choices=["text", "markdown"],
        default="text",
        help="Report output format (default: text)",
    )

    # health
    p_health = subparsers.add_parser(
        "health",
        help="Repository health assessment with recommendations",
    )
    _add_common_args(p_health)

    # churn
    p_churn = subparsers.add_parser(
        "churn",
        help="File and extension churn analysis",
    )
    _add_common_args(p_churn)
    p_churn.add_argument(
        "--sort-by",
        choices=["total", "insertions", "deletions", "commits", "authors"],
        default="total",
        help="Sort files by metric (default: total)",
    )
    p_churn.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max files to show (default: 20)",
    )

    # heatmap (legacy compatibility)
    p_heatmap = subparsers.add_parser(
        "heatmap",
        help="GitHub-style contribution heatmap (last 52 weeks)",
    )
    _add_common_args(p_heatmap)

    # dashboard (legacy compatibility — default command)
    p_dashboard = subparsers.add_parser(
        "dashboard",
        help="Full interactive dashboard view",
    )
    _add_common_args(p_dashboard)

    # Determine if a subcommand was provided; if not, default to 'summary'
    COMMANDS = {
        "summary",
        "authors",
        "timeline",
        "activity",
        "compare",
        "report",
        "health",
        "churn",
        "heatmap",
        "dashboard",
    }
    effective_argv = list(argv) if argv else []
    has_subcommand = bool(effective_argv) and effective_argv[0] in COMMANDS
    if not has_subcommand:
        effective_argv = ["summary"] + effective_argv

    args = parser.parse_args(effective_argv)

    target = Path(args.path).resolve()

    if not target.exists():
        print(f"Error: path '{target}' does not exist.", file=sys.stderr)
        return 1

    # Parse date ranges
    until = datetime.now()
    since = until - timedelta(days=365)
    if args.since:
        since = _parse_date(args.since, default=until - timedelta(days=365))
    if args.until:
        until = _parse_date(args.until, default=until)

    try:
        pulse = GitPulse(
            path=target,
            since=since,
            until=until,
            author=args.author,
            scan_repos=args.repos,
        )
        pulse.analyze()
    except Exception as e:
        print(f"Error analyzing repository: {e}", file=sys.stderr)
        return 1

    if args.output_json:
        pulse.to_json(sys.stdout)
        return 0

    # Dispatch to subcommand handler
    cmd = args.command or "summary"
    if cmd == "summary":
        handle_summary(pulse, since, until)
    elif cmd == "authors":
        handle_authors(pulse, since, until, sort_by=args.sort_by, limit=args.limit)
    elif cmd == "timeline":
        handle_timeline(pulse, since, until, granularity=args.granularity)
    elif cmd == "activity":
        handle_activity(pulse, since, until)
    elif cmd == "compare":
        handle_compare(pulse, since, until, period_days=args.period)
    elif cmd == "report":
        handle_report(pulse, since, until, output=args.output)
    elif cmd == "health":
        handle_health(pulse, since, until)
    elif cmd == "churn":
        handle_churn(pulse, since, until, sort_by=args.sort_by, limit=args.limit)
    elif cmd == "heatmap":
        render_heatmap(pulse, since, until)
    elif cmd == "dashboard":
        render_dashboard(pulse, since, until)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 1

    return 0


def _parse_date(value: str, default: datetime) -> datetime:
    """Parse a date string like '2024-01-15' or '30d'."""
    if value.endswith("d"):
        try:
            days = int(value[:-1])
            return datetime.now() - timedelta(days=days)
        except ValueError:
            pass
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        print(
            f"Error: cannot parse date '{value}'. Use YYYY-MM-DD or Nd format.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
