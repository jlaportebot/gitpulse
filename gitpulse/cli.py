"""Command-line interface for gitpulse."""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from .core import GitPulse
from .heatmap import render_heatmap
from .display import render_dashboard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gitpulse",
        description="Beautiful Git activity dashboard in your terminal.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to a git repository or directory containing repos (default: .)",
    )
    parser.add_argument(
        "--heatmap",
        action="store_true",
        help="Show contribution heatmap (last 52 weeks)",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Start date (YYYY-MM-DD or Nd for N days ago)",
    )
    parser.add_argument(
        "--until",
        type=str,
        default=None,
        help="End date (YYYY-MM-DD, default: today)",
    )
    parser.add_argument(
        "--author",
        type=str,
        default=None,
        help="Filter commits by author name or email",
    )
    parser.add_argument(
        "--repos",
        action="store_true",
        help="Scan directory for multiple git repos and show aggregate stats",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__import__('gitpulse').__version__}",
    )

    args = parser.parse_args(argv)
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

    if args.heatmap:
        render_heatmap(pulse, since, until)
        return 0

    render_dashboard(pulse, since, until)
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
