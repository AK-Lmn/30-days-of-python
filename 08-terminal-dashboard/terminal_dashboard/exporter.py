import html
import json
from pathlib import Path

from terminal_dashboard.models import DashboardSnapshot
from terminal_dashboard.sparkline import format_bytes, format_rate


def export_to_json(snapshot: DashboardSnapshot) -> str:
    return json.dumps(snapshot.to_dict(), indent=2)


def export_to_markdown(snapshot: DashboardSnapshot) -> str:
    lines = [
        f"# System Dashboard Report — {snapshot.timestamp}",
        "",
        "## System Overview",
        "",
        f"- **Hostname:** {snapshot.system.hostname}",
        f"- **OS:** {snapshot.system.os_name} {snapshot.system.os_release} ({snapshot.system.architecture})",
        f"- **Kernel / OS Version:** {snapshot.system.os_version}",
        f"- **Python Version:** {snapshot.system.python_version}",
        f"- **Boot Time:** {snapshot.system.boot_time}",
        f"- **Uptime:** {snapshot.system.uptime_formatted}",
        "",
        "## CPU",
        "",
        f"- **Overall Usage:** {snapshot.cpu.usage_percent:.1f}%",
        f"- **Cores:** {snapshot.cpu.physical_cores} Physical / {snapshot.cpu.logical_cores} Logical",
    ]

    if snapshot.cpu.frequency_current_mhz:
        lines.append(f"- **Frequency:** {snapshot.cpu.frequency_current_mhz:.0f} MHz")

    if snapshot.cpu.load_averages:
        loads_str = ", ".join(f"{l:.2f}" for l in snapshot.cpu.load_averages)
        lines.append(f"- **Load Averages:** {loads_str}")

    lines.extend([
        "",
        "## Memory & Swap",
        "",
        f"- **RAM Usage:** {snapshot.memory.usage_percent:.1f}% ({format_bytes(snapshot.memory.used_bytes)} / {format_bytes(snapshot.memory.total_bytes)})",
        f"- **RAM Available:** {format_bytes(snapshot.memory.available_bytes)}",
        f"- **Swap Usage:** {snapshot.memory.swap_usage_percent:.1f}% ({format_bytes(snapshot.memory.swap_used_bytes)} / {format_bytes(snapshot.memory.swap_total_bytes)})",
        "",
        "## Storage Partitions",
        "",
        "| Mountpoint | Device | Filesystem | Used | Total | Usage % |",
        "|---|---|---|---|---|---|",
    ])

    for part in snapshot.disk.partitions:
        lines.append(
            f"| `{part.mountpoint}` | {part.device} | {part.fstype} | {format_bytes(part.used_bytes)} | {format_bytes(part.total_bytes)} | {part.usage_percent:.1f}% |"
        )

    if snapshot.disk.io:
        lines.extend([
            "",
            "### Disk I/O",
            f"- **Read Rate:** {format_rate(snapshot.disk.io.read_bytes_per_sec)}",
            f"- **Write Rate:** {format_rate(snapshot.disk.io.write_bytes_per_sec)}",
            f"- **Total Read:** {format_bytes(snapshot.disk.io.total_read_bytes)}",
            f"- **Total Written:** {format_bytes(snapshot.disk.io.total_write_bytes)}",
        ])

    lines.extend([
        "",
        "## Network",
        "",
        f"- **Active Connections:** {snapshot.network.connection_count}",
    ])

    if snapshot.network.io:
        lines.extend([
            f"- **Upload Rate:** {format_rate(snapshot.network.io.bytes_sent_per_sec)}",
            f"- **Download Rate:** {format_rate(snapshot.network.io.bytes_recv_per_sec)}",
            f"- **Total Sent:** {format_bytes(snapshot.network.io.total_bytes_sent)}",
            f"- **Total Received:** {format_bytes(snapshot.network.io.total_bytes_recv)}",
        ])

    lines.extend([
        "",
        "| Interface | Status | IP Address | MAC Address |",
        "|---|---|---|---|",
    ])
    for iface in snapshot.network.interfaces:
        status_badge = "UP" if iface.is_up else "DOWN"
        lines.append(
            f"| {iface.name} | {status_badge} | {iface.ip_address or 'N/A'} | {iface.mac_address or 'N/A'} |"
        )

    if snapshot.battery:
        plugged_str = "Plugged In" if snapshot.battery.power_plugged else "On Battery"
        lines.extend([
            "",
            "## Battery",
            f"- **Charge:** {snapshot.battery.percent:.0f}%",
            f"- **Power State:** {plugged_str}",
        ])

    lines.extend([
        "",
        "## Top Processes",
        "",
        "| PID | Name | User | CPU % | Mem % | Memory RSS | Threads | Status |",
        "|---|---|---|---|---|---|---|---|",
    ])
    for proc in snapshot.processes:
        lines.append(
            f"| {proc.pid} | {proc.name} | {proc.username} | {proc.cpu_percent:.1f}% | {proc.memory_percent:.1f}% | {format_bytes(proc.memory_bytes)} | {proc.threads} | {proc.status} |"
        )

    if snapshot.alerts:
        lines.extend([
            "",
            "## Active Alerts",
            "",
            "| Level | Target | Message | Value | Threshold |",
            "|---|---|---|---|---|",
        ])
        for alert in snapshot.alerts:
            lines.append(
                f"| {alert.level.value} | {alert.name} | {alert.message} | {alert.value:.1f} | {alert.threshold:.1f} |"
            )

    lines.append("")
    return "\n".join(lines)


def export_to_html(snapshot: DashboardSnapshot) -> str:
    title = f"Terminal Dashboard — {html.escape(snapshot.system.hostname)}"

    proc_rows = []
    for p in snapshot.processes:
        proc_rows.append(
            f"<tr><td>{p.pid}</td><td><b>{html.escape(p.name)}</b></td><td>{html.escape(p.username)}</td>"
            f"<td>{p.cpu_percent:.1f}%</td><td>{p.memory_percent:.1f}%</td>"
            f"<td>{format_bytes(p.memory_bytes)}</td><td>{p.threads}</td>"
            f"<td><span class='badge'>{p.status}</span></td></tr>"
        )

    disk_rows = []
    for d in snapshot.disk.partitions:
        disk_rows.append(
            f"<tr><td><code>{html.escape(d.mountpoint)}</code></td><td>{html.escape(d.fstype)}</td>"
            f"<td>{format_bytes(d.used_bytes)} / {format_bytes(d.total_bytes)}</td>"
            f"<td><div class='bar-track'><div class='bar-fill' style='width: {min(d.usage_percent, 100.0):.1f}%;'></div></div></td>"
            f"<td>{d.usage_percent:.1f}%</td></tr>"
        )

    net_rows = []
    for n in snapshot.network.interfaces:
        status_cls = "badge-ok" if n.is_up else "badge-warn"
        net_rows.append(
            f"<tr><td><b>{html.escape(n.name)}</b></td>"
            f"<td><span class='badge {status_cls}'>{'UP' if n.is_up else 'DOWN'}</span></td>"
            f"<td>{html.escape(n.ip_address or 'N/A')}</td>"
            f"<td>{html.escape(n.mac_address or 'N/A')}</td></tr>"
        )

    alert_blocks = []
    for a in snapshot.alerts:
        cls = "alert-crit" if a.level.value == "CRITICAL" else "alert-warn"
        alert_blocks.append(
            f"<div class='alert-card {cls}'><b>[{a.level.value}] {html.escape(a.name)}:</b> {html.escape(a.message)}</div>"
        )
    alerts_html = "".join(alert_blocks) if alert_blocks else "<p class='dim'>No active warnings or critical alerts.</p>"

    lines = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{title}</title>",
        "<style>",
        "  :root {",
        "    --bg: #0f172a;",
        "    --surface: #1e293b;",
        "    --surface-hover: #334155;",
        "    --border: #334155;",
        "    --text: #f8fafc;",
        "    --text-dim: #94a3b8;",
        "    --accent: #38bdf8;",
        "    --green: #4ade80;",
        "    --yellow: #facc15;",
        "    --red: #f87171;",
        "  }",
        "  body {",
        "    margin: 0;",
        "    padding: 24px;",
        '    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;',
        "    background: var(--bg);",
        "    color: var(--text);",
        "  }",
        "  header {",
        "    border-bottom: 1px solid var(--border);",
        "    padding-bottom: 16px;",
        "    margin-bottom: 24px;",
        "  }",
        "  h1 { margin: 0 0 8px; font-size: 24px; color: var(--accent); }",
        "  .meta { color: var(--text-dim); font-size: 14px; }",
        "  .grid {",
        "    display: grid;",
        "    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));",
        "    gap: 16px;",
        "    margin-bottom: 24px;",
        "  }",
        "  .card {",
        "    background: var(--surface);",
        "    border: 1px solid var(--border);",
        "    border-radius: 8px;",
        "    padding: 16px;",
        "  }",
        "  .card h2 { margin-top: 0; font-size: 16px; color: var(--accent); }",
        "  .metric-large { font-size: 32px; font-weight: 700; margin: 8px 0; }",
        "  .bar-track { background: #0f172a; border-radius: 4px; height: 10px; overflow: hidden; margin: 8px 0; }",
        "  .bar-fill { background: var(--accent); height: 100%; }",
        "  table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }",
        "  th, td { padding: 8px 10px; border-bottom: 1px solid var(--border); }",
        "  th { color: var(--text-dim); font-weight: 600; }",
        "  tr:hover { background: var(--surface-hover); }",
        "  .badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 11px; background: #334155; }",
        "  .badge-ok { background: rgba(74, 222, 128, 0.2); color: var(--green); }",
        "  .badge-warn { background: rgba(250, 204, 21, 0.2); color: var(--yellow); }",
        "  .alert-card { padding: 10px 14px; border-radius: 6px; margin-bottom: 8px; font-size: 13px; }",
        "  .alert-warn { background: rgba(250, 204, 21, 0.15); border-left: 4px solid var(--yellow); }",
        "  .alert-crit { background: rgba(248, 113, 113, 0.15); border-left: 4px solid var(--red); }",
        "  .dim { color: var(--text-dim); }",
        "</style>",
        "</head>",
        "<body>",
        "  <header>",
        f"    <h1>Terminal Dashboard — {html.escape(snapshot.system.hostname)}</h1>",
        '    <div class="meta">',
        f"      OS: {html.escape(snapshot.system.os_name)} {html.escape(snapshot.system.os_release)} ({html.escape(snapshot.system.architecture)}) |",
        f"      Uptime: {html.escape(snapshot.system.uptime_formatted)} |",
        f"      Snapshot: {snapshot.timestamp}",
        "    </div>",
        "  </header>",
        "",
        '  <div class="card" style="margin-bottom: 24px;">',
        "    <h2>System Alerts</h2>",
        f"    {alerts_html}",
        "  </div>",
        "",
        '  <div class="grid">',
        '    <div class="card">',
        "      <h2>CPU Usage</h2>",
        f'      <div class="metric-large">{snapshot.cpu.usage_percent:.1f}%</div>',
        f'      <div class="bar-track"><div class="bar-fill" style="width: {min(snapshot.cpu.usage_percent, 100.0):.1f}%;"></div></div>',
        f'      <div class="meta">Cores: {snapshot.cpu.physical_cores}P / {snapshot.cpu.logical_cores}L</div>',
        "    </div>",
        "",
        '    <div class="card">',
        "      <h2>Memory (RAM)</h2>",
        f'      <div class="metric-large">{snapshot.memory.usage_percent:.1f}%</div>',
        f'      <div class="bar-track"><div class="bar-fill" style="width: {min(snapshot.memory.usage_percent, 100.0):.1f}%;"></div></div>',
        f'      <div class="meta">{format_bytes(snapshot.memory.used_bytes)} / {format_bytes(snapshot.memory.total_bytes)}</div>',
        "    </div>",
        "",
        '    <div class="card">',
        "      <h2>Swap Memory</h2>",
        f'      <div class="metric-large">{snapshot.memory.swap_usage_percent:.1f}%</div>',
        f'      <div class="bar-track"><div class="bar-fill" style="width: {min(snapshot.memory.swap_usage_percent, 100.0):.1f}%;"></div></div>',
        f'      <div class="meta">{format_bytes(snapshot.memory.swap_used_bytes)} / {format_bytes(snapshot.memory.swap_total_bytes)}</div>',
        "    </div>",
        "  </div>",
        "",
        '  <div class="card" style="margin-bottom: 24px;">',
        "    <h2>Storage Partitions</h2>",
        "    <table>",
        "      <thead><tr><th>Mount</th><th>Type</th><th>Used / Total</th><th>Progress</th><th>Usage %</th></tr></thead>",
        f"      <tbody>{''.join(disk_rows)}</tbody>",
        "    </table>",
        "  </div>",
        "",
        '  <div class="card" style="margin-bottom: 24px;">',
        "    <h2>Network Interfaces</h2>",
        "    <table>",
        "      <thead><tr><th>Interface</th><th>Status</th><th>IP Address</th><th>MAC Address</th></tr></thead>",
        f"      <tbody>{''.join(net_rows)}</tbody>",
        "    </table>",
        "  </div>",
        "",
        '  <div class="card" style="margin-bottom: 24px;">',
        "    <h2>Top Processes</h2>",
        "    <table>",
        "      <thead><tr><th>PID</th><th>Name</th><th>User</th><th>CPU %</th><th>Mem %</th><th>RSS</th><th>Threads</th><th>Status</th></tr></thead>",
        f"      <tbody>{''.join(proc_rows)}</tbody>",
        "    </table>",
        "  </div>",
        "</body>",
        "</html>",
    ]
    return "\n".join(lines)


def export_snapshot(
    snapshot: DashboardSnapshot,
    format_type: str,
    output_path: Path | str | None = None,
) -> str:
    fmt = format_type.strip().lower()
    if fmt == "json":
        content = export_to_json(snapshot)
    elif fmt in ("md", "markdown"):
        content = export_to_markdown(snapshot)
    elif fmt == "html":
        content = export_to_html(snapshot)
    else:
        raise ValueError(f"Unsupported format: {format_type}. Choose json, markdown, or html.")

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(content)

    return content
