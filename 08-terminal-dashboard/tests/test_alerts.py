from terminal_dashboard.alerts import evaluate_alerts, get_health_status
from terminal_dashboard.models import (
    Alert,
    AlertLevel,
    BatteryMetrics,
    CpuMetrics,
    DashboardConfig,
    DashboardSnapshot,
    DiskMetrics,
    DiskPartitionMetrics,
    MemoryMetrics,
    NetworkMetrics,
    SystemInfo,
)


def create_sample_snapshot(
    cpu_usage: float = 10.0,
    mem_usage: float = 20.0,
    swap_usage: float = 10.0,
    disk_usage: float = 30.0,
    battery_percent: float = 80.0,
    battery_plugged: bool = True,
) -> DashboardSnapshot:
    sys_info = SystemInfo(
        hostname="testhost",
        os_name="Linux",
        os_release="6.1.0",
        os_version="1",
        architecture="x86_64",
        python_version="3.12.0",
        boot_time="2026-09-20 10:00:00",
        uptime_seconds=3600.0,
        uptime_formatted="1h",
    )
    cpu = CpuMetrics(
        usage_percent=cpu_usage,
        physical_cores=4,
        logical_cores=8,
        frequency_current_mhz=3200.0,
        frequency_min_mhz=None,
        frequency_max_mhz=None,
        per_core_percent=[cpu_usage] * 8,
        load_averages=None,
    )
    mem = MemoryMetrics(
        total_bytes=1000,
        used_bytes=int(mem_usage * 10),
        available_bytes=1000 - int(mem_usage * 10),
        free_bytes=100,
        usage_percent=mem_usage,
        swap_total_bytes=1000,
        swap_used_bytes=int(swap_usage * 10),
        swap_free_bytes=1000 - int(swap_usage * 10),
        swap_usage_percent=swap_usage,
    )
    disk = DiskMetrics(
        partitions=[
            DiskPartitionMetrics(
                device="/dev/sda1",
                mountpoint="/",
                fstype="ext4",
                total_bytes=1000,
                used_bytes=int(disk_usage * 10),
                free_bytes=1000 - int(disk_usage * 10),
                usage_percent=disk_usage,
            )
        ],
        io=None,
    )
    net = NetworkMetrics(interfaces=[], io=None, connection_count=0)
    battery = BatteryMetrics(
        percent=battery_percent,
        power_plugged=battery_plugged,
        seconds_left=None,
    )
    return DashboardSnapshot(
        timestamp="2026-09-20 12:00:00",
        system=sys_info,
        cpu=cpu,
        memory=mem,
        disk=disk,
        network=net,
        battery=battery,
        processes=[],
        alerts=[],
    )


def test_evaluate_alerts_healthy():
    cfg = DashboardConfig()
    snap = create_sample_snapshot()
    alerts = evaluate_alerts(snap, cfg)
    assert len(alerts) == 0
    code, status = get_health_status(alerts)
    assert code == 0
    assert status == "HEALTHY"


def test_evaluate_alerts_cpu_warning():
    cfg = DashboardConfig(cpu_warning_threshold=70.0, cpu_critical_threshold=90.0)
    snap = create_sample_snapshot(cpu_usage=75.0)
    alerts = evaluate_alerts(snap, cfg)
    assert len(alerts) == 1
    assert alerts[0].name == "CPU Usage"
    assert alerts[0].level == AlertLevel.WARNING
    code, status = get_health_status(alerts)
    assert code == 1
    assert status == "WARNING"


def test_evaluate_alerts_cpu_critical():
    cfg = DashboardConfig(cpu_warning_threshold=70.0, cpu_critical_threshold=90.0)
    snap = create_sample_snapshot(cpu_usage=95.0)
    alerts = evaluate_alerts(snap, cfg)
    assert len(alerts) == 1
    assert alerts[0].name == "CPU Usage"
    assert alerts[0].level == AlertLevel.CRITICAL
    code, status = get_health_status(alerts)
    assert code == 2
    assert status == "CRITICAL"


def test_evaluate_alerts_multiple():
    cfg = DashboardConfig(
        cpu_warning_threshold=70.0,
        memory_warning_threshold=70.0,
        disk_warning_threshold=70.0,
    )
    snap = create_sample_snapshot(cpu_usage=80.0, mem_usage=85.0, disk_usage=90.0)
    alerts = evaluate_alerts(snap, cfg)
    assert len(alerts) == 3


def test_evaluate_battery_alert():
    cfg = DashboardConfig()
    snap = create_sample_snapshot(battery_percent=10.0, battery_plugged=False)
    alerts = evaluate_alerts(snap, cfg)
    assert len(alerts) == 1
    assert alerts[0].name == "Battery"
    assert alerts[0].level == AlertLevel.WARNING
