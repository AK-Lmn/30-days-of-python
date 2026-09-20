from terminal_dashboard.collector import MetricsCollector
from terminal_dashboard.models import Alert, AlertLevel
from terminal_dashboard.views import (
    compose_dashboard_layout,
    get_usage_color,
    render_alerts_banner,
    render_cpu_panel,
    render_disk_panel,
    render_footer,
    render_header,
    render_memory_panel,
    render_network_panel,
    render_process_panel,
)


def test_get_usage_color():
    assert get_usage_color(50.0) == "bold green"
    assert get_usage_color(76.0) == "bold yellow"
    assert get_usage_color(92.0) == "bold red"


def test_render_views():
    collector = MetricsCollector()
    snap = collector.collect_snapshot(process_limit=3)

    header = render_header(snap.system, snap.battery)
    assert header is not None

    healthy_banner = render_alerts_banner([])
    assert healthy_banner is not None

    alert = Alert("CPU", AlertLevel.CRITICAL, "Over 90%", 95.0, 90.0)
    crit_banner = render_alerts_banner([alert])
    assert crit_banner is not None

    cpu_panel = render_cpu_panel(snap.cpu, history=[10.0, 20.0, 30.0])
    assert cpu_panel is not None

    mem_panel = render_memory_panel(snap.memory, history=[40.0, 42.0])
    assert mem_panel is not None

    disk_panel = render_disk_panel(snap.disk)
    assert disk_panel is not None

    net_panel = render_network_panel(snap.network, [100.0, 200.0], [50.0, 75.0])
    assert net_panel is not None

    proc_panel = render_process_panel(snap.processes, sort_by="cpu")
    assert proc_panel is not None

    footer = render_footer(1.0)
    assert footer is not None


def test_compose_dashboard_layout():
    collector = MetricsCollector()
    snap = collector.collect_snapshot(process_limit=3)
    layout = compose_dashboard_layout(
        snapshot=snap,
        cpu_history=[10.0, 15.0],
        mem_history=[40.0, 42.0],
        net_recv_history=[1000.0],
        net_sent_history=[500.0],
        refresh_interval=1.0,
        sort_by="cpu",
    )
    assert layout is not None
    assert layout["header"] is not None
    assert layout["cpu"] is not None
    assert layout["processes"] is not None
