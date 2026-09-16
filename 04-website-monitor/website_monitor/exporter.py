import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
from typing import List

from website_monitor.models import TargetStats, Incident


def export_to_json(stats: List[TargetStats], incidents: List[Incident]) -> str:
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_targets": len(stats),
            "up_targets": sum(1 for s in stats if s.last_is_up is True),
            "down_targets": sum(1 for s in stats if s.last_is_up is False),
            "active_incidents": sum(1 for i in incidents if not i.resolved),
        },
        "targets": [s.to_dict() for s in stats],
        "incidents": [i.to_dict() for i in incidents],
    }
    return json.dumps(data, indent=2)


def export_to_csv(stats: List[TargetStats]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Target ID",
        "Target Name",
        "URL",
        "Status",
        "Uptime %",
        "Total Checks",
        "Up Checks",
        "Down Checks",
        "Avg Latency (ms)",
        "Min Latency (ms)",
        "p95 Latency (ms)",
        "Max Latency (ms)",
        "Active Incident",
        "SSL Days Left",
        "Last Checked At",
    ])
    for s in stats:
        status_str = "UP" if s.last_is_up is True else ("DOWN" if s.last_is_up is False else "UNKNOWN")
        writer.writerow([
            s.target_id,
            s.target_name,
            s.target_url,
            status_str,
            f"{s.uptime_percentage:.2f}%",
            s.total_checks,
            s.up_checks,
            s.down_checks,
            f"{s.avg_latency_ms:.2f}",
            f"{s.min_latency_ms:.2f}",
            f"{s.p95_latency_ms:.2f}",
            f"{s.max_latency_ms:.2f}",
            "YES" if s.active_incident else "NO",
            s.ssl_days_left if s.ssl_days_left is not None else "N/A",
            s.last_checked_at or "N/A",
        ])
    return output.getvalue()


def export_to_markdown(stats: List[TargetStats], incidents: List[Incident]) -> str:
    lines = []
    lines.append("# Website Health & SLA Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")
    lines.append("## Target Summary")
    lines.append("")
    lines.append("| Target | Status | Uptime % | Avg Latency | p95 Latency | SSL Days | Outage |")
    lines.append("|---|---|---|---|---|---|---|")
    for s in stats:
        status_icon = "🟢 UP" if s.last_is_up is True else ("🔴 DOWN" if s.last_is_up is False else "⚪ UNKNOWN")
        ssl_str = f"{s.ssl_days_left}d" if s.ssl_days_left is not None else "—"
        incident_str = "⚠️ Active" if s.active_incident else "None"
        lines.append(
            f"| [{s.target_name}]({s.target_url}) | {status_icon} | {s.uptime_percentage:.2f}% | "
            f"{s.avg_latency_ms:.1f} ms | {s.p95_latency_ms:.1f} ms | {ssl_str} | {incident_str} |"
        )
    lines.append("")
    lines.append("## Recent Incidents")
    lines.append("")
    if not incidents:
        lines.append("No incidents recorded.")
    else:
        lines.append("| Target | Started | Duration | Status | Root Cause |")
        lines.append("|---|---|---|---|---|")
        for inc in incidents:
            dur_str = f"{int(inc.duration_seconds)}s" if inc.duration_seconds is not None else "Ongoing"
            res_str = "Resolved" if inc.resolved else "🚨 UNRESOLVED"
            lines.append(
                f"| {inc.target_name or inc.target_id} | {inc.started_at} | {dur_str} | {res_str} | {inc.reason} |"
            )
    lines.append("")
    return "\n".join(lines)


def save_export(content: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
