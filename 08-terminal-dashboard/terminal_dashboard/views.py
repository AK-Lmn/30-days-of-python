from collections import deque
from typing import Sequence

from rich.align import Align
from rich.box import ROUNDED, SIMPLE
from rich.console import Group, RenderableType
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from terminal_dashboard.models import (
    Alert,
    AlertLevel,
    BatteryMetrics,
    CpuMetrics,
    DashboardSnapshot,
    DiskMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessInfo,
    SystemInfo,
)
from terminal_dashboard.sparkline import format_bytes, format_rate, render_bar, render_sparkline


def get_usage_color(percent: float) -> str:
    if percent >= 90.0:
        return "bold red"
    if percent >= 75.0:
        return "bold yellow"
    return "bold green"


def render_header(system: SystemInfo, battery: BatteryMetrics | None) -> Panel:
    title_text = Text()
    title_text.append("⚡ ", style="bold yellow")
    title_text.append("TERMINAL DASHBOARD", style="bold cyan")
    title_text.append("  |  Host: ", style="dim")
    title_text.append(system.hostname, style="bold white")
    title_text.append("  |  OS: ", style="dim")
    title_text.append(f"{system.os_name} {system.os_release} ({system.architecture})", style="white")
    title_text.append("  |  Uptime: ", style="dim")
    title_text.append(system.uptime_formatted, style="bold green")

    if battery:
        title_text.append("  |  Battery: ", style="dim")
        bat_color = "bold red" if battery.percent <= 15 else ("bold yellow" if battery.percent <= 30 else "bold green")
        plug_icon = "🔌 " if battery.power_plugged else "🔋 "
        title_text.append(f"{plug_icon}{battery.percent:.0f}%", style=bat_color)

    return Panel(title_text, box=ROUNDED, style="cyan", padding=(0, 1))


def render_alerts_banner(alerts: list[Alert]) -> Panel | None:
    if not alerts:
        healthy_text = Text("● System Healthy — All metrics within normal operating bounds", style="bold green")
        return Panel(healthy_text, box=ROUNDED, style="green", padding=(0, 1))

    has_crit = any(a.level == AlertLevel.CRITICAL for a in alerts)
    box_style = "bold red" if has_crit else "bold yellow"
    alert_text = Text()
    for idx, a in enumerate(alerts):
        if idx > 0:
            alert_text.append("  •  ", style="dim white")
        lvl_color = "bold red" if a.level == AlertLevel.CRITICAL else "bold yellow"
        alert_text.append(f"[{a.level.value}] ", style=lvl_color)
        alert_text.append(f"{a.name}: {a.message}", style="white")

    return Panel(alert_text, title="Active Alerts", box=ROUNDED, style=box_style, padding=(0, 1))


def render_cpu_panel(cpu: CpuMetrics, history: Sequence[float] | None = None) -> Panel:
    color = get_usage_color(cpu.usage_percent)
    bar = render_bar(cpu.usage_percent, width=16)

    table = Table(box=None, expand=True, show_header=False, padding=(0, 1))
    table.add_column("Key", style="cyan", justify="left", ratio=1)
    table.add_column("Value", justify="right", ratio=2)

    table.add_row(
        "Overall Usage",
        f"[{color}]{cpu.usage_percent:5.1f}% [/{color}][dim]{bar}[/dim]",
    )

    if history:
        spark = render_sparkline(history, min_val=0.0, max_val=100.0)
        table.add_row("History Trend", f"[cyan]{spark}[/cyan]")

    table.add_row(
        "Cores",
        f"{cpu.physical_cores} Physical / {cpu.logical_cores} Logical",
    )

    if cpu.frequency_current_mhz:
        table.add_row("Frequency", f"{cpu.frequency_current_mhz:.0f} MHz")

    if cpu.load_averages:
        loads = " ".join(f"{l:.2f}" for l in cpu.load_averages)
        table.add_row("Load Avg", loads)

    core_table = Table(box=None, expand=True, show_header=False, padding=(0, 1))
    for i in range(0, len(cpu.per_core_percent), 2):
        c1 = cpu.per_core_percent[i]
        col1 = get_usage_color(c1)
        b1 = render_bar(c1, width=8)
        left = f"C{i:02d} [{col1}]{c1:4.1f}%[/{col1}] [dim]{b1}[/dim]"

        if i + 1 < len(cpu.per_core_percent):
            c2 = cpu.per_core_percent[i + 1]
            col2 = get_usage_color(c2)
            b2 = render_bar(c2, width=8)
            right = f"C{i+1:02d} [{col2}]{c2:4.1f}%[/{col2}] [dim]{b2}[/dim]"
        else:
            right = ""
        core_table.add_row(left, right)

    content = Group(table, core_table)
    return Panel(content, title="CPU Telemetry", box=ROUNDED, style="bright_blue", border_style="bright_blue")


def render_memory_panel(memory: MemoryMetrics, history: Sequence[float] | None = None) -> Panel:
    ram_color = get_usage_color(memory.usage_percent)
    ram_bar = render_bar(memory.usage_percent, width=16)

    swap_color = get_usage_color(memory.swap_usage_percent)
    swap_bar = render_bar(memory.swap_usage_percent, width=16)

    table = Table(box=None, expand=True, show_header=False, padding=(0, 1))
    table.add_column("Key", style="magenta", justify="left", ratio=1)
    table.add_column("Value", justify="right", ratio=2)

    table.add_row(
        "RAM Usage",
        f"[{ram_color}]{memory.usage_percent:5.1f}% [/{ram_color}][dim]{ram_bar}[/dim]",
    )

    if history:
        spark = render_sparkline(history, min_val=0.0, max_val=100.0)
        table.add_row("RAM Trend", f"[magenta]{spark}[/magenta]")

    table.add_row("Used / Total", f"{format_bytes(memory.used_bytes)} / {format_bytes(memory.total_bytes)}")
    table.add_row("Available", f"[green]{format_bytes(memory.available_bytes)}[/green]")
    table.add_row("Free", f"{format_bytes(memory.free_bytes)}")

    if memory.swap_total_bytes > 0:
        table.add_row(
            "Swap Usage",
            f"[{swap_color}]{memory.swap_usage_percent:5.1f}% [/{swap_color}][dim]{swap_bar}[/dim]",
        )
        table.add_row("Swap Used", f"{format_bytes(memory.swap_used_bytes)} / {format_bytes(memory.swap_total_bytes)}")

    return Panel(table, title="Memory & Swap", box=ROUNDED, style="magenta", border_style="magenta")


def render_disk_panel(disk: DiskMetrics) -> Panel:
    table = Table(box=SIMPLE, expand=True, padding=(0, 1))
    table.add_column("Mount", style="yellow")
    table.add_column("Type", style="dim")
    table.add_column("Used / Total", justify="right")
    table.add_column("Bar", justify="center")
    table.add_column("Usage", justify="right")

    for p in disk.partitions:
        col = get_usage_color(p.usage_percent)
        b = render_bar(p.usage_percent, width=10)
        table.add_row(
            p.mountpoint,
            p.fstype,
            f"{format_bytes(p.used_bytes)} / {format_bytes(p.total_bytes)}",
            f"[dim]{b}[/dim]",
            f"[{col}]{p.usage_percent:4.1f}%[/{col}]",
        )

    elements = [table]
    if disk.io:
        io_table = Table(box=None, expand=True, show_header=False, padding=(0, 1))
        io_table.add_row(
            "Disk I/O Rates",
            f"Read: [bold cyan]{format_rate(disk.io.read_bytes_per_sec)}[/bold cyan]  |  Write: [bold yellow]{format_rate(disk.io.write_bytes_per_sec)}[/bold yellow]",
        )
        elements.append(io_table)

    return Panel(Group(*elements), title="Storage & Disks", box=ROUNDED, style="yellow", border_style="yellow")


def render_network_panel(
    network: NetworkMetrics,
    recv_history: Sequence[float] | None = None,
    sent_history: Sequence[float] | None = None,
) -> Panel:
    table = Table(box=SIMPLE, expand=True, padding=(0, 1))
    table.add_column("Interface", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("IP Address")
    table.add_column("MAC Address", style="dim")

    for iface in network.interfaces[:4]:
        status_style = "bold green" if iface.is_up else "bold red"
        status_text = "UP" if iface.is_up else "DOWN"
        table.add_row(
            iface.name,
            f"[{status_style}]{status_text}[/{status_style}]",
            iface.ip_address or "N/A",
            iface.mac_address or "N/A",
        )

    elements = [table]
    if network.io:
        io_table = Table(box=None, expand=True, show_header=False, padding=(0, 1))
        io_table.add_row(
            "Network Throughput",
            f"↓ In: [bold green]{format_rate(network.io.bytes_recv_per_sec)}[/bold green]  |  ↑ Out: [bold blue]{format_rate(network.io.bytes_sent_per_sec)}[/bold blue]  |  Conns: [bold white]{network.connection_count}[/bold white]",
        )
        if recv_history and sent_history:
            r_spark = render_sparkline(recv_history)
            s_spark = render_sparkline(sent_history)
            io_table.add_row("Traffic Trend", f"↓ [green]{r_spark}[/green]  ↑ [blue]{s_spark}[/blue]")
        elements.append(io_table)

    return Panel(Group(*elements), title="Network Telemetry", box=ROUNDED, style="cyan", border_style="cyan")


def render_process_panel(processes: list[ProcessInfo], sort_by: str = "cpu") -> Panel:
    table = Table(box=SIMPLE, expand=True, padding=(0, 1))
    table.add_column("PID", style="cyan", justify="right")
    table.add_column("Name", style="bold white")
    table.add_column("User", style="dim")
    table.add_column("CPU %", justify="right")
    table.add_column("MEM %", justify="right")
    table.add_column("RSS Memory", justify="right")
    table.add_column("Threads", justify="right")
    table.add_column("Status", justify="center")

    for p in processes:
        cpu_style = get_usage_color(p.cpu_percent)
        mem_style = get_usage_color(p.memory_percent)
        table.add_row(
            str(p.pid),
            p.name,
            p.username,
            f"[{cpu_style}]{p.cpu_percent:5.1f}%[/{cpu_style}]",
            f"[{mem_style}]{p.memory_percent:5.1f}%[/{mem_style}]",
            format_bytes(p.memory_bytes),
            str(p.threads),
            p.status,
        )

    sort_label = f"Top Processes (Sorted by {sort_by.upper()})"
    return Panel(table, title=sort_label, box=ROUNDED, style="white", border_style="white")


def render_footer(refresh_interval: float) -> Panel:
    footer_text = Text()
    footer_text.append("  [Ctrl+C] ", style="bold red")
    footer_text.append("Exit  |  ", style="dim")
    footer_text.append(f"Refresh Rate: {refresh_interval:.1f}s  |  ", style="dim")
    footer_text.append("Live Telemetry Active", style="bold green")
    return Panel(Align.center(footer_text), box=ROUNDED, style="dim white", padding=(0, 1))


def compose_dashboard_layout(
    snapshot: DashboardSnapshot,
    cpu_history: Sequence[float] | None = None,
    mem_history: Sequence[float] | None = None,
    net_recv_history: Sequence[float] | None = None,
    net_sent_history: Sequence[float] | None = None,
    refresh_interval: float = 1.0,
    sort_by: str = "cpu",
) -> Layout:
    root = Layout(name="root")
    root.split_column(
        Layout(name="header", size=3),
        Layout(name="alerts", size=3),
        Layout(name="upper", ratio=3),
        Layout(name="lower", ratio=4),
        Layout(name="footer", size=3),
    )

    root["upper"].split_row(
        Layout(name="cpu", ratio=1),
        Layout(name="memory", ratio=1),
    )

    root["lower"].split_row(
        Layout(name="storage_net", ratio=1),
        Layout(name="processes", ratio=1),
    )

    root["storage_net"].split_column(
        Layout(name="disk", ratio=1),
        Layout(name="network", ratio=1),
    )

    root["header"].update(render_header(snapshot.system, snapshot.battery))
    root["alerts"].update(render_alerts_banner(snapshot.alerts))
    root["cpu"].update(render_cpu_panel(snapshot.cpu, cpu_history))
    root["memory"].update(render_memory_panel(snapshot.memory, mem_history))
    root["disk"].update(render_disk_panel(snapshot.disk))
    root["network"].update(render_network_panel(snapshot.network, net_recv_history, net_sent_history))
    root["processes"].update(render_process_panel(snapshot.processes, sort_by))
    root["footer"].update(render_footer(refresh_interval))

    return root
