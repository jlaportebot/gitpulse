# 🫀 gitpulse

**Beautiful Git activity dashboard in your terminal.**

A fast, offline CLI tool that analyzes your local git repositories and renders a GitHub-style contribution heatmap, commit stats, author breakdowns, and streak tracking — all from the terminal.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- 📊 **Contribution heatmap** — GitHub-style year view, right in your terminal
- 📈 **Activity stats** — total commits, insertions/deletions, active days, net lines
- 🔥 **Streak tracking** — current and longest commit streaks
- 👤 **Author breakdown** — see who contributes what (bar chart visualization)
- 📁 **Multi-repo scanning** — point at a directory and aggregate stats across all repos
- 🎯 **Author filtering** — filter stats by author name or email
- 📋 **JSON output** — machine-readable output for scripting and integrations
- ⚡ **Zero dependencies** — pure Python, uses only `git` CLI under the hood
- 🔒 **Fully offline** — no API calls, no network, your data stays local

## Installation

```bash
pip install gitpulse
```

Or install from source:

```bash
git clone https://github.com/jlaportebot/gitpulse.git
cd gitpulse
pip install -e .
```

## Usage

### Dashboard (default)

```bash
# Show dashboard for the current repo
gitpulse

# Show dashboard for a specific repo
gitpulse /path/to/repo

# Aggregate stats across all repos in a directory
gitpulse --repos ~/projects
```

### Contribution Heatmap

```bash
# GitHub-style heatmap for the last year
gitpulse --heatmap

# Heatmap for the last 90 days
gitpulse --heatmap --since 90d
```

### Date Ranges

```bash
# Custom date range
gitpulse --since 2024-01-01 --until 2024-12-31

# Last 30 days
gitpulse --since 30d
```

### Author Filter

```bash
# Only your commits
gitpulse --author "Your Name"
```

### JSON Output

```bash
# Machine-readable output for scripts and CI
gitpulse --json
gitpulse --json --repos ~/projects
```

## Examples

### Dashboard output

```
  ╔══════════════════════════════════════════╗
  ║          🫀  gitpulse dashboard          ║
  ╚══════════════════════════════════════════╝

  Period:   2024-05-26 → 2025-05-26

  ── Overview ──
  Total commits:    847
  Lines added:      +23,456
  Lines removed:    -12,123
  Net lines:        +11,333
  Active days:      156
  Longest streak:   23 days
  Current streak:   5 days

  ── Top Authors ──
  You <you@example.com>                   847 ██████████████████████████████

  ── Recent Commits ──
  a1b2c3d 2025-05-25 14:30 Fix edge case in heatmap renderer
  e4f5g6h 2025-05-24 09:15 Add multi-repo scanning support
  ...
```

### Heatmap output

```
  Contribution Heatmap

      Jun  Jul  Aug  Sep  Oct  Nov  Dec  Jan  Feb  Mar  Apr  May
  Mon ░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒
  Wed ░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒
  Fri ░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒▓█░▒░▒
  Sun ░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒░▒

    Less ░▒▓█ More
    847 commits in the last year · 156 active days
```

## How It Works

gitpulse runs `git log` with `--numstat` to collect commit metadata and line-level diff stats, then aggregates everything in memory. No API keys, no network access, no external databases — just your local git data.

## Requirements

- Python 3.10+
- Git (installed and in PATH)

## License

MIT © Jonathan Laporte
