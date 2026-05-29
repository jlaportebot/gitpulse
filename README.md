# 🫀 gitpulse

Beautiful Git activity dashboard and analytics in your terminal.

## Installation

```bash
pip install gitpulse
```

## Quick Start

```bash
# Quick summary of current repo
gitpulse summary

# Full dashboard view
gitpulse dashboard

# Contribution heatmap
gitpulse heatmap

# Detailed author breakdown
gitpulse authors

# Commit activity over time
gitpulse timeline

# Hourly and day-of-week patterns
gitpulse activity

# Compare periods
gitpulse compare --period 30

# Full report (text or markdown)
gitpulse report --output markdown

# Repository health assessment
gitpulse health

# File churn analysis
gitpulse churn
```

## Commands

| Command | Description |
|---------|-------------|
| `summary` | Quick activity overview (default if no command given) |
| `dashboard` | Full interactive dashboard with stats, authors, and recent commits |
| `heatmap` | GitHub-style contribution heatmap (last 52 weeks) |
| `authors` | Detailed author rankings with sorting by commits, lines, activity |
| `timeline` | Commit activity over time — monthly or weekly granularity |
| `activity` | Hour-of-day and day-of-week commit pattern analysis |
| `compare` | Compare current period vs previous period of equal length |
| `report` | Comprehensive analysis report in text or markdown |
| `health` | Repository health assessment with recommendations |
| `churn` | File and extension churn analysis with collaboration hotspots |

## Options

All commands support:

| Option | Description |
|--------|-------------|
| `path` | Path to a git repo or directory (default: `.`) |
| `--since` | Start date (`YYYY-MM-DD` or `Nd` for N days ago) |
| `--until` | End date (`YYYY-MM-DD`, default: today) |
| `--author` | Filter commits by author name or email |
| `--repos` | Scan directory for multiple git repos |
| `--json` | Output results as JSON |

Command-specific options:

- `authors --sort-by {commits,insertions,deletions,net,active_days,recent}` — Sort authors by metric
- `authors --limit N` — Max authors to show
- `timeline --granularity {month,week}` — Time bucket size
- `compare --period N` — Period length in days for comparison
- `report --output {text,markdown}` — Report output format
- `churn --sort-by {total,insertions,deletions,commits,authors}` — Sort files by metric
- `churn --limit N` — Max files to show

## Examples

```bash
# Analyze a specific repo for the last 90 days
gitpulse summary /path/to/repo --since 90d

# Show author rankings sorted by lines added
gitpulse authors --sort-by insertions --limit 10

# Weekly commit timeline
gitpulse timeline --granularity week

# Compare last 60 days vs previous 60 days
gitpulse compare --period 60

# Generate markdown report
gitpulse report --output markdown > report.md

# Repository health check
gitpulse health

# Most churned files
gitpulse churn --sort-by total --limit 15

# Scan all repos in a directory
gitpulse summary ~/projects --repos

# JSON output for scripting
gitpulse summary --json | jq '.health'
```

## Health Score

The `health` command calculates an activity score (0-100) based on:

| Component | Weight | Description |
|-----------|--------|-------------|
| Frequency | 40 | Active days / total days ratio |
| Recency | 30 | Days since last commit (decays over 30 days) |
| Streak | 15 | Longest consecutive-day streak (capped at 30) |
| Diversity | 15 | Number of unique authors (capped at 5) |

Grades: A (80+), B (60+), C (40+), D (20+), F (<20)

The health check also evaluates:
- **Bus factor** — minimum authors needed to cover 50% of commits
- **Churn ratio** — fraction of lines that are deletions (indicates rewriting)
- **Metadata** — README, LICENSE, CONTRIBUTING, CI config presence
- **Recommendations** — actionable suggestions based on detected issues

## Churn Analysis

The `churn` command identifies:

- **Most churned files** — files with the highest insertions+deletions, indicating instability or hot development areas
- **Churn by extension** — which file types see the most change activity
- **Collaboration hotspots** — files edited by multiple authors, indicating coordination needs or potential conflict zones

## Development

```bash
pip install -e ".[dev]"
pytest gitpulse/tests.py -v
```

## License

MIT
