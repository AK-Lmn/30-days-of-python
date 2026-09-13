# Day 02 — Smart File Organizer

A robust, non-destructive CLI tool and Python library for automatically organizing messy directories (such as Downloads, Desktop, or raw datasets) by file type categories, extensions, creation/modification dates, file size tiers, or custom regex naming rules. Features dry-run simulations, collision resolution strategies, atomic undo/rollback history, duplicate file detection, and empty folder cleanup.

**Date:** Sep 13, 2026 (Submitted Sep 14, 2026)  
**Status:** ✅ Completed (Late)  

---

## Features

- **Multiple Sorting Strategies**:
  - `category` (default): Groups files into standard folders (`Images`, `Documents`, `Audio`, `Video`, `Archives`, `Code`, `Executables`, `Data`, `Other`).
  - `extension`: Groups files by file extension (`PDF`, `PNG`, `PY`, `ZIP`, etc.).
  - `date`: Groups files into chronological folders (`YYYY/YYYY-MM`).
  - `size`: Groups files into size tiers (`Tiny (<1MB)`, `Small (1-10MB)`, `Medium (10-100MB)`, `Large (100MB-1GB)`, `Huge (>1GB)`).
  - `custom`: User-defined regex and extension rules from `organizer.yaml`.
- **Safety First & Zero Data Loss**:
  - **Dry-Run Mode (`-n` / `--dry-run`)**: Preview all proposed operations in a formatted Rich table before moving any files.
  - **Collision Resolution**: Configurable via `--conflict [rename|skip|overwrite|hash]`. Defaults to safe auto-increment renaming (`file (1).ext`) to guarantee no existing file is overwritten.
  - **Atomic Rollback (`organizer undo`)**: Every move or copy operation is logged to a local SQLite journal, enabling 1-command rollback of any previous session.
- **Power Utilities**:
  - **Duplicate Detection (`organizer duplicates`)**: Fast two-stage detection (size filtering followed by chunked SHA-256 hashing) with options to list, move, or delete duplicates.
  - **Empty Folder Cleaner (`organizer clean-empty`)**: Prunes empty leftover directories (bottom-up traversal) with dry-run support.
  - **Config Generator (`organizer config init`)**: Scaffolds a starter `organizer.yaml` file for custom rules.
- **Rich Terminal UI**:
  - Color-coded badges for action types (`MOVE`, `COPY`, `SKIP`), categories, and formatted byte sizes.
  - Interactive prompts for potentially destructive operations.

---

## Installation & Setup

All dependencies and packaging are self-contained within this folder.

```powershell
# Navigate into the day's folder
cd 02-file-organizer

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

### 1. Organizing Files

```bash
# Preview what would be organized without touching any files
organizer organize ~/Downloads --dry-run

# Organize current directory using default categories
organizer organize .

# Organize recursively across subdirectories
organizer organize ~/Downloads -r

# Copy files instead of moving them
organizer organize ~/Downloads --copy

# Sort files by extension into dedicated extension folders
organizer organize ~/Downloads --by extension

# Sort files by modification date (Year/Month)
organizer organize ~/Downloads --by date

# Sort files by size tiers
organizer organize ~/Downloads --by size

# Append Year/Month subfolders within categories
organizer organize ~/Downloads --date-subfolders

# Specify a separate destination directory
organizer organize ~/Downloads --dest ~/CleanDownloads

# Set collision strategy (rename, skip, overwrite, hash)
organizer organize ~/Downloads --conflict skip
```

### 2. Undoing Past Operations

```bash
# Revert the most recent organization session
organizer undo

# Revert a specific session by ID
organizer undo 3
```

### 3. Viewing History

```bash
# View recent organization sessions
organizer history

# Limit history count
organizer history --limit 10
```

### 4. Detecting Duplicate Files

```bash
# Find duplicate files in a directory
organizer duplicates ~/Downloads

# Find duplicates and move them to a review folder
organizer duplicates ~/Downloads --move-to ~/Downloads/Duplicates

# Find duplicates and prompt to delete them
organizer duplicates ~/Downloads --delete
```

### 5. Cleaning Empty Directories

```bash
# Preview empty folders to delete
organizer clean-empty ~/Downloads --dry-run

# Remove empty folders
organizer clean-empty ~/Downloads
```

### 6. Custom Configuration

Generate a starter configuration file:

```bash
organizer config init
```

Inspect active categories and custom rules:

```bash
organizer config show
```

Sample `organizer.yaml`:

```yaml
categories:
  Images:
    - .jpg
    - .png
    - .webp
  Documents:
    - .pdf
    - .docx
    - .xlsx
  Code:
    - .py
    - .ts
    - .json

rules:
  - name: Invoices
    folder: Documents/Invoices
    pattern: "(?i)^inv.*\\.pdf$"
  - name: Screenshots
    folder: Images/Screenshots
    pattern: "(?i)^screenshot.*\\.(png|jpg)$"

ignored_patterns:
  - ".*"
  - "desktop.ini"
  - "thumbs.db"

ignored_directories:
  - ".git"
  - ".venv"
  - "node_modules"
```

---

## Running Tests

All unit and integration tests are self-contained:

```powershell
cd 02-file-organizer
.\.venv\Scripts\pytest -v
```

---

## Architecture

- `organizer/models.py`: Strongly-typed dataclasses and enums for files, actions, sessions, and rules.
- `organizer/config.py`: Configuration loading, default category definitions, and starter template generator.
- `organizer/rules.py`: File classification engine matching extensions, regex patterns, date structures, and size tiers.
- `organizer/duplicates.py`: Two-stage duplicate finder with size binning and chunked SHA-256 calculation.
- `organizer/history.py`: SQLite audit log tracking sessions and file movements for rollback operations.
- `organizer/core.py`: Directory scanner, collision resolver, organization execution, and rollback engine.
- `organizer/views.py`: Rich terminal presentation layer for tables, summaries, trees, and progress indicators.
- `organizer/cli.py`: Click-based CLI entry point exposing commands and options.
