import json
from pathlib import Path
from website_monitor.exporter import export_to_json, export_to_csv, export_to_markdown, save_export
from website_monitor.models import TargetStats, Incident


def make_dummy_data():
    stats = [
        TargetStats(
            target_id=1,
            target_name="Production API",
            target_url="https://api.prod.com",
            total_checks=100,
            up_checks=99,
            down_checks=1,
            uptime_percentage=99.0,
            avg_latency_ms=45.2,
            min_latency_ms=20.0,
            p95_latency_ms=80.0,
            max_latency_ms=120.0,
            active_incident=False,
            last_status_code=200,
            last_latency_ms=42.1,
            last_checked_at="2026-09-16T12:00:00Z",
            last_is_up=True,
            ssl_days_left=85,
        )
    ]
    incidents = [
        Incident(
            id=1,
            target_id=1,
            target_name="Production API",
            target_url="https://api.prod.com",
            reason="Gateway Timeout",
            started_at="2026-09-16T11:00:00Z",
            ended_at="2026-09-16T11:02:00Z",
            duration_seconds=120.0,
            resolved=True,
        )
    ]
    return stats, incidents


def test_export_to_json():
    stats, incidents = make_dummy_data()
    raw = export_to_json(stats, incidents)
    parsed = json.loads(raw)
    assert parsed["summary"]["total_targets"] == 1
    assert parsed["summary"]["up_targets"] == 1
    assert len(parsed["targets"]) == 1
    assert len(parsed["incidents"]) == 1


def test_export_to_csv():
    stats, _ = make_dummy_data()
    csv_text = export_to_csv(stats)
    lines = csv_text.strip().splitlines()
    assert len(lines) == 2
    assert "Target Name" in lines[0]
    assert "Production API" in lines[1]
    assert "99.00%" in lines[1]


def test_export_to_markdown():
    stats, incidents = make_dummy_data()
    md = export_to_markdown(stats, incidents)
    assert "# Website Health & SLA Report" in md
    assert "Production API" in md
    assert "99.00%" in md
    assert "Gateway Timeout" in md


def test_save_export(tmp_path: Path):
    out_file = tmp_path / "reports" / "report.md"
    save_export("# Hello World", out_file)
    assert out_file.exists()
    assert out_file.read_text(encoding="utf-8") == "# Hello World"
