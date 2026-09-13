# Day 03 — GitHub Analyzer

A high-performance CLI tool and Python library for analyzing GitHub users, organizations, and repositories. Computes metrics on language distribution, repository portfolios, star/fork aggregations, commit activity, contributor rankings, and repository health scores, complete with side-by-side comparisons and export capabilities (Markdown and JSON).

**Date:** Sep 14, 2026  
**Status:** ✅ Completed  

---

## Features

- **User & Organization Analytics (`gh-analyzer user <username>`)**:
  - Profile card displaying name, bio, organization, location, website, and account join date.
  - Portfolio metrics: total public repos, source vs forked repository count, followers, total stars earned, and total forks accumulated.
  - Aggregated language distribution across all public repositories with percentage breakdown and visual bar chart.
  - Top starred and most active repositories.
- **Repository Deep Dive (`gh-analyzer repo <owner/repo>`)**:
  - Repository overview: default branch, license, size, stars, forks, watchers, open issues.
  - Byte-accurate language composition breakdown.
  - Commit velocity analytics: sampled commit volume, weekday activity patterns, and top commit authors.
  - Top contributors leaderboard with contribution tallies.
  - Repository Health Score (0-100) evaluating description, license, README, topics, and issue tracking.
- **Side-by-Side Comparison (`gh-analyzer compare <target1> <target2>`)**:
  - Compare two repositories (stars, forks, open issues, health score, size, language, contributors).
  - Compare two users (followers, public repos, source repos, total stars earned, total forks earned, top language).
  - Automatic winner highlighting for key metrics.
- **Rate Limit & Performance Optimization**:
  - `gh-analyzer rate-limit`: Displays current GitHub API quota, remaining requests, reset timestamp, and usage bar.
  - Automatic SQLite response caching with TTL (default 1 hour) to preserve API rate limits and deliver instantaneous repeated queries.
  - `gh-analyzer cache clear` & `gh-analyzer cache status` management commands.
  - Optional personal access token support via `--token` or `GITHUB_TOKEN` environment variable for 5,000 requests/hr.
- **Exporting Engine**:
  - Export comprehensive reports directly to formatted Markdown (`--export md`) or raw structured JSON (`--export json`).
- **Modern Pure-Python Desktop GUI (`gh-analyzer gui`)**:
  - Built with CustomTkinter (100% Python, dark mode theme).
  - Tabview with dedicated panels for User Analysis, Repository Deep Dive, Side-by-Side Comparisons, and API Rate Limit/Cache Management.
  - Smooth asynchronous data loading with progress bars and native file dialog report exports.
- **Rich Terminal UI**:
  - Cross-platform formatted tables, panels, and distribution bars.

---

## Installation & Setup

All dependencies and packaging are self-contained within this folder.

```powershell
# Navigate into the day's folder
cd 03-github-analyzer

# Create virtual environment (if not already created)
python -m venv .venv

# Activate virtual environment
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

# Install requirements and package in editable mode
pip install -r requirements.txt
pip install -e .
```

---

## CLI Command Reference

### 1. Analyzing a User or Organization

```bash
# Analyze a GitHub user
gh-analyzer user octocat

# Include forked repositories in metrics
gh-analyzer user octocat --include-forks

# Export user report to Markdown
gh-analyzer user octocat --export md --output octocat_report.md

# Export user report to JSON
gh-analyzer user octocat --export json --output octocat_report.json
```

### 2. Analyzing a Repository

```bash
# Analyze repository metrics, languages, commits, and health
gh-analyzer repo octocat/Spoon-Knife

# Export repository audit to Markdown
gh-analyzer repo octocat/Spoon-Knife --export md --output spoon_knife_audit.md
```

### 3. Comparing Repositories or Users

```bash
# Compare two repositories side-by-side
gh-analyzer compare octocat/Hello-World octocat/Spoon-Knife

# Compare two GitHub users side-by-side
gh-analyzer compare torvalds antirez --type user
```

### 4. Rate Limits & Cache Management

```bash
# Check GitHub API rate limit quota
gh-analyzer rate-limit

# Use personal access token for 5,000 requests/hr
gh-analyzer --token YOUR_GITHUB_TOKEN user octocat

# Clear local cache
gh-analyzer cache clear

# Prune expired entries
gh-analyzer cache status
```

### 5. Launching the Desktop GUI

You can launch the modern CustomTkinter desktop interface using either command:

```powershell
# Via the main CLI
gh-analyzer gui

# Or via the dedicated GUI script
gh-analyzer-gui
```

---

## Running Tests

Run the test suite with pytest:

```powershell
.\.venv\Scripts\pytest -v
```

All 32 test cases cover cache management, API client error handling, rate limiting, analytics computations, comparisons, markdown/json exports, and CLI commands.

---

## Project Structure

```text
03-github-analyzer/
├── .gitignore
├── README.md
├── pyproject.toml
├── requirements.txt
├── github_analyzer/
│   ├── __init__.py
│   ├── analyzer.py       # Metrics aggregation, health calculation, comparisons
│   ├── cache.py          # SQLite response caching with TTL
│   ├── client.py         # HTTP client with auth, rate-limiting, error handling
│   ├── exporter.py       # JSON and Markdown report generation
│   ├── models.py         # Dataclasses for users, repos, metrics, languages
│   └── views.py          # Rich terminal rendering components
└── tests/
    ├── __init__.py
    ├── test_analyzer.py  # Analytics, calculations, comparisons tests
    ├── test_cache.py     # SQLite cache persistence and expiration tests
    ├── test_cli.py       # Click CLI command execution tests
    ├── test_client.py    # GitHubClient and mock response tests
    └── test_exporter.py  # JSON and Markdown export tests
```
