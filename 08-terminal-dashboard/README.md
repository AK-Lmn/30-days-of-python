# Day 08 — Terminal Dashboard

A live, high-performance terminal system telemetry dashboard and process explorer built with Python, Rich, and psutil. Features real-time resource gauges (CPU, memory, swap, storage, network, and battery), live Unicode history trend sparklines, proactive threshold alert monitoring, individual subsystem inspection commands, and multi-format reports (JSON, Markdown, styled dark-mode HTML).

**Date:** Sep 19, 2026  
**Status:** ✅ Completed  

---

## Features

- **Live System Telemetry & Hardware Gauges**:
  - **Host & Platform**: Hostname, OS distribution, release, kernel/version, architecture, Python runtime version, system boot time, and human-readable uptime.
  - **CPU Performance**: Overall CPU load percentage, per-core meter breakdown across all physical and logical cores, clock frequency, and OS load averages.
  - **Memory & Swap**: Physical RAM breakdown (total, used, available, free, usage %) and Swap/Pagefile usage meters.
  - **Storage & Partitions**: Auto-detects mounted disk partitions, filesystems, total/used/free space, disk usage progress bars, and real-time read/write I/O byte rates.
  - **Network Monitoring**: Active network adapters, status (UP/DOWN), IPv4 addresses, MAC addresses, active connection counts, and real-time upload/download throughput.
  - **Battery & Power Detection**: Battery charge percentage, AC plugged-in indicator, and remaining time estimation on laptops.

- **Process Explorer**:
  - Comprehensive process table listing PID, Process Name, User, CPU %, Memory %, RSS memory bytes, Thread count, and Status.
  - Multi-key sorting: sort processes by CPU usage (`--sort cpu`), Memory consumption (`--sort mem`), Process Name (`--sort name`), or PID (`--sort pid`).
  - Search and filter processes by keyword match (`--search <pattern>`).
  - Configurable top-N limits.

- **Real-Time Visualizations**:
  - High-resolution Unicode sparklines (` ▂▃▄▅▆▇█`) for historical trend visualization (CPU utilization, RAM utilization, network download/upload traffic).
  - Adaptive color-coded progress bars and percentage meters: Green (<75%), Yellow (75-90%), Red (>=90%).

- **Proactive Threshold Alerting & Health Engine**:
  - Configurable warning and critical thresholds for CPU, RAM, Swap, Disk, and Battery.
  - Live alert banner displaying active warnings and critical alerts or a green healthy badge.
  - Automated health check CLI command (`termdash check`) returning standard UNIX exit codes (0 = Healthy, 1 = Warning, 2 = Critical) for CI/CD pipelines and monitoring daemons.

- **Multi-Format Snapshot Reports & Exports**:
  - Export system snapshots instantly to **JSON**, **Markdown**, and self-contained styled **HTML** reports with embedded CSS dark-mode dashboard styling.

- **Comprehensive Modular CLI**:
  - `termdash` / `termdash live`: Full-screen live terminal dashboard with configurable refresh interval.
  - `termdash snapshot`: One-shot telemetry snapshot print (ideal for piping or cron logging).
  - `termdash cpu`: Detailed CPU telemetry inspection.
  - `termdash mem`: Detailed memory and swap telemetry inspection.
  - `termdash disk`: Detailed storage partitions and I/O rates inspection.
  - `termdash net`: Detailed network adapters and traffic inspection.
  - `termdash proc`: Process explorer with sorting, filtering, and limit flags.
  - `termdash check`: Exit code health check command.
  - `termdash export`: Export current snapshot to JSON, Markdown, or HTML files.
  - `termdash config-show` / `termdash config-init`: Configuration management.

---

## Architecture

```text
08-terminal-dashboard/
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── README.md
├── exports/
│   ├── snapshot.json
│   ├── snapshot.md
│   └── snapshot.html
├── terminal_dashboard/
│   ├── __init__.py           # Package exports and version
│   ├── models.py             # Strongly-typed telemetry models & data schemas
│   ├── collector.py          # psutil & platform system metrics collector
│   ├── sparkline.py          # Unicode sparklines & byte/rate formatters
│   ├── alerts.py             # Threshold monitoring & health evaluation
│   ├── config.py             # Settings loader and JSON configuration manager
│   ├── views.py              # Rich terminal components, tables, and layouts
│   ├── exporter.py           # JSON, Markdown, and HTML report generators
│   ├── app.py                # Live terminal dashboard loop with sliding history
│   └── cli.py                # Click CLI interface with modular subcommands
└── tests/
    ├── __init__.py
    ├── test_models.py        # Model serialization and schema verification
    ├── test_collector.py     # System telemetry collection tests
    ├── test_sparkline.py     # Sparkline rendering and scaling tests
    ├── test_alerts.py        # Alert threshold triggers and level categorization
    ├── test_config.py        # Config loading, parsing, and persistence tests
    ├── test_exporter.py      # JSON, Markdown, and HTML export tests
    ├── test_views.py         # Rich panel and layout composition tests
    └── test_cli.py           # CLI commands, subcommands, and flags tests
```

---

## Installation & Setup

1. Navigate to the project directory:
   ```bash
   cd 08-terminal-dashboard
   ```

2. Create and activate the virtual environment:
   ```bash
   uv venv .venv
   .\.venv\Scripts\activate      # Windows
   # source .venv/bin/activate    # Linux / macOS
   ```

3. Install dependencies in editable development mode:
   ```bash
   uv pip install -e ".[dev]"
   ```

---

## CLI Usage Guide

### 1. Live Interactive Dashboard
Launch the full-screen live dashboard:
```bash
termdash
```
Customize refresh interval, sorting, and process count:
```bash
termdash live --interval 0.5 --sort mem --limit 20
```

### 2. One-Shot Snapshot
Print an instant telemetry snapshot directly to terminal output:
```bash
termdash snapshot
```

### 3. Subsystem Inspection
Inspect specific hardware and system subsystems:
```bash
termdash cpu
termdash mem
termdash disk
termdash net
```

### 4. Process Explorer
Inspect and sort top running processes:
```bash
# Sort by CPU usage
termdash proc --sort cpu --limit 10

# Sort by memory usage
termdash proc --sort mem --limit 15

# Search processes by name
termdash proc --search python
```

### 5. Automated Health Check
Run health checks for automation and monitoring scripts:
```bash
termdash check
echo $LASTEXITCODE   # 0: Healthy, 1: Warning, 2: Critical
```

### 6. Export Reports
Export current system snapshot to structured formats:
```bash
termdash export --format json --output exports/snapshot.json
termdash export --format markdown --output exports/snapshot.md
termdash export --format html --output exports/snapshot.html
```

### 7. Configuration Management
Inspect or initialize custom thresholds and settings:
```bash
termdash config-show
termdash config-init --path ~/.termdash.json
```

---

## Configuration Schema

You can customize thresholds and behaviors via `~/.termdash.json` or by specifying `--config path/to/config.json`:

```json
{
  "refresh_interval": 1.0,
  "history_points": 30,
  "process_limit": 15,
  "process_sort_by": "cpu",
  "cpu_warning_threshold": 75.0,
  "cpu_critical_threshold": 90.0,
  "memory_warning_threshold": 80.0,
  "memory_critical_threshold": 95.0,
  "swap_warning_threshold": 60.0,
  "swap_critical_threshold": 85.0,
  "disk_warning_threshold": 80.0,
  "disk_critical_threshold": 90.0
}
```

---

## Testing

Run the comprehensive 50-test test suite:
```bash
pytest -v
```

All 50 unit and integration tests validate metric collection, models, sparkline scaling, alert thresholds, multi-format export, view rendering, and CLI command execution.
