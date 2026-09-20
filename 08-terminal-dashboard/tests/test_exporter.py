import json
from pathlib import Path
import pytest

from terminal_dashboard.collector import MetricsCollector
from terminal_dashboard.exporter import export_snapshot, export_to_html, export_to_json, export_to_markdown


def test_export_to_json():
    collector = MetricsCollector()
    snap = collector.collect_snapshot(process_limit=3)
    out = export_to_json(snap)
    data = json.loads(out)
    assert "timestamp" in data
    assert "system" in data
    assert "cpu" in data


def test_export_to_markdown():
    collector = MetricsCollector()
    snap = collector.collect_snapshot(process_limit=3)
    md = export_to_markdown(snap)
    assert "# System Dashboard Report" in md
    assert "## System Overview" in md
    assert "## CPU" in md
    assert "## Memory & Swap" in md
    assert "## Storage Partitions" in md


def test_export_to_html():
    collector = MetricsCollector()
    snap = collector.collect_snapshot(process_limit=3)
    html = export_to_html(snap)
    assert "<!DOCTYPE html>" in html
    assert "Terminal Dashboard" in html
    assert snap.system.hostname in html


def test_export_snapshot_file(tmp_path: Path):
    collector = MetricsCollector()
    snap = collector.collect_snapshot(process_limit=2)

    json_file = tmp_path / "report.json"
    export_snapshot(snap, format_type="json", output_path=json_file)
    assert json_file.exists()
    assert len(json_file.read_text(encoding="utf-8")) > 50

    md_file = tmp_path / "report.md"
    export_snapshot(snap, format_type="markdown", output_path=md_file)
    assert md_file.exists()
    assert len(md_file.read_text(encoding="utf-8")) > 50

    html_file = tmp_path / "report.html"
    export_snapshot(snap, format_type="html", output_path=html_file)
    assert html_file.exists()
    assert "<!DOCTYPE html>" in html_file.read_text(encoding="utf-8")


def test_export_snapshot_invalid_format():
    collector = MetricsCollector()
    snap = collector.collect_snapshot(process_limit=2)
    with pytest.raises(ValueError):
        export_snapshot(snap, format_type="unsupported_format")
