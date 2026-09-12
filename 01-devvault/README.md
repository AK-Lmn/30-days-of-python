# Day 01 — DevVault CLI

A developer-focused CLI tool for saving, organizing, searching, and managing code snippets, shell commands, notes, and useful URLs with SQLite FTS5 full-text search, Rich formatting, and clipboard integration.

**Date:** Sep 12, 2026  
**Status:** ✅ Completed  

---

## Features

- **4 Core Item Types**:
  - `snippet`: Multi-line code snippets with syntax highlighting (`python`, `bash`, `javascript`, `sql`, etc.).
  - `command`: Common shell commands and one-liners with safe execution (`devvault run <id>`).
  - `note`: Quick notes, architectural decisions, and markdown documentation.
  - `url`: Bookmarked documentation, APIs, and tools, launchable in your browser (`devvault open <id>`).
- **Instant Full-Text Search (FTS5)**: Fast ranked searching across titles, contents, and descriptions.
- **Rich Terminal UI**: Styled badges, syntax-highlighted code panels, formatted result tables, and statistics cards.
- **Multiple Input Modes**: Inline flags, interactive prompts, `$EDITOR` for multi-line notes/code, and piped `stdin`.
- **Developer Workflows**:
  - Direct clipboard copying (`devvault copy <id>` or `--copy`).
  - Safe command execution with confirmation prompt (`devvault run <id> -y`).
  - Browser launcher for URLs (`devvault open <id>`).
  - Export and import to/from JSON or Markdown (`devvault export`, `devvault import`).
- **Flexible Storage**: Stored at `~/.devvault/vault.db` by default; custom path configurable with `--db` or `DEVVAULT_DB` environment variable.

---

## Installation & Setup

All dependencies and packaging are self-contained within this folder.

```powershell
# Navigate into the day's folder
cd 01-devvault

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

### 1. Adding Entries

```bash
# Add with type flag and inline content
devvault add -t "FastAPI Server" -T snippet -c "from fastapi import FastAPI\napp = FastAPI()" -l python

# Pipe content from stdin
cat script.py | devvault add -t "Script Backup" -T snippet -l python --stdin

# Launch $EDITOR for multi-line drafting
devvault add -t "System Architecture" -T note -e

# Interactive wizard (prompts for title, content, type, etc.)
devvault add
```

#### Dedicated Shorthands

```bash
# Code snippets
devvault snippet add "Reverse String" -c "s[::-1]" -l python

# Shell commands
devvault cmd add "Docker Prune" "docker system prune -a --volumes -f" -d "Clean all containers and volumes"

# Notes
devvault note add "Database Design" "Always use SQLite FTS5 for fast text search"

# Bookmarks / URLs
devvault url add "Python Docs" "https://docs.python.org/3/"
```

### 2. Listing & Inspecting

```bash
# List all entries (most recent first)
devvault list

# Filter by type
devvault list -t snippet
devvault list -t command

# View full details with syntax highlighting
devvault show 1

# View details and copy content directly to clipboard
devvault show 1 --copy
```

### 3. Full-Text Search (FTS5)

```bash
# Search across titles, content, and descriptions
devvault search "docker"

# Filter search results by type
devvault search "python" -t snippet
```

### 4. Developer Actions

```bash
# Copy snippet or command to clipboard
devvault copy 1

# Execute a saved command in your shell (with confirmation prompt)
devvault run 2

# Execute without prompt
devvault run 2 --yes

# Open URL bookmark in default web browser
devvault open 3
```

### 5. Editing & Deleting

```bash
# Edit metadata or content
devvault edit 1 -t "New Title" -d "Updated description"

# Edit content in your preferred text editor
devvault edit 1 -e

# Delete an entry
devvault delete 1
devvault delete 1 --yes
```

### 6. Statistics & Backup

```bash
# View vault statistics
devvault stats

# Export entries to JSON or Markdown
devvault export -f json -o vault_backup.json
devvault export -f markdown -o vault_notes.md

# Import entries from JSON backup
devvault import vault_backup.json
```

---

## Running Tests

Automated test suite using `pytest`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

Suite covers:
- SQLite table initialization & triggers
- FTS5 full-text search indexing and fallbacks
- CRUD operations for all item types
- CLI options, flags, stdin piping, and Click commands
- Export to JSON/Markdown and import verification
