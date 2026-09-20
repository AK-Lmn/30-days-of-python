from terminal_dashboard.models import (
    Alert,
    AlertLevel,
    BatteryMetrics,
    CpuMetrics,
    DashboardConfig,
    DashboardSnapshot,
    DiskIoMetrics,
    DiskMetrics,
    DiskPartitionMetrics,
    MemoryMetrics,
    NetworkInterfaceMetrics,
    NetworkIoMetrics,
    NetworkMetrics,
    ProcessInfo,
    SystemInfo,
)


def test_alert_serialization():
    alert = Alert(
        name="CPU Usage",
        level=AlertLevel.WARNING,
        message="CPU is high",
        value=78.5,
        threshold=75.0,
    )
    data = alert.to_dict()
    assert data["name"] == "CPU Usage"
    assert data["level"] == "WARNING"
    assert data["value"] == 78.5
    assert data["threshold"] == 75.0


def test_dashboard_snapshot_serialization():
    sys_info = SystemInfo(
        hostname="testhost",
        os_name="Linux",
        os_release="6.1.0",
        os_version="SMP PREEMPT",
        architecture="x86_64",
        python_version="3.12.0",
        boot_time="2026-09-20 10:00:00",
        uptime_seconds=3600.0,
        uptime_formatted="1h 0m 0s",
    )
    cpu = CpuMetrics(
        usage_percent=45.5,
        physical_cores=4,
        logical_cores=8,
        frequency_current_mhz=3200.0,
        frequency_min_mhz=1600.0,
        frequency_max_mhz=4000.0,
        per_core_percent=[40.0, 50.0],
        load_averages=[1.5, 1.2, 0.9],
    )
    mem = MemoryMetrics(
        total_bytes=16000000000,
        used_bytes=8000000000,
        available_bytes=8000000000,
        free_bytes=4000000000,
        usage_percent=50.0,
        swap_total_bytes=4000000000,
        swap_used_bytes=1000000000,
        swap_free_bytes=3000000000,
        swap_usage_percent=25.0,
    )
    disk = DiskMetrics(
        partitions=[
            DiskPartitionMetrics(
                device="/dev/sda1",
                mountpoint="/",
                fstype="ext4",
                total_bytes=500000000000,
                used_bytes=250000000000,
                free_bytes=250000000000,
                usage_percent=50.0,
            )
        ],
        io=DiskIoMetrics(
            read_bytes_per_sec=1024.0,
            write_bytes_per_sec=2048.0,
            read_count_per_sec=10.0,
            write_count_per_sec=20.0,
            total_read_bytes=100000,
            total_write_bytes=200000,
        ),
    )
    net = NetworkMetrics(
        interfaces=[
            NetworkInterfaceMetrics(
                name="eth0",
                is_up=True,
                ip_address="192.168.1.100",
                netmask="255.255.255.0",
                mac_address="00:11:22:33:44:55",
            )
        ],
        io=NetworkIoMetrics(
            bytes_sent_per_sec=5000.0,
            bytes_recv_per_sec=10000.0,
            packets_sent_per_sec=50.0,
            packets_recv_per_sec=100.0,
            total_bytes_sent=500000,
            total_bytes_recv=1000000,
        ),
        connection_count=15,
    )
    battery = BatteryMetrics(
        percent=85.0,
        power_plugged=True,
        seconds_left=None,
    )
    proc = ProcessInfo(
        pid=1234,
        name="python",
        username="user",
        status="running",
        cpu_percent=12.5,
        memory_percent=4.2,
        memory_bytes=500000000,
        threads=4,
        create_time="10:05:00",
    )
    snapshot = DashboardSnapshot(
        timestamp="2026-09-20 11:00:00",
        system=sys_info,
        cpu=cpu,
        memory=mem,
        disk=disk,
        network=net,
        battery=battery,
        processes=[proc],
        alerts=[],
    )

    data = snapshot.to_dict()
    assert data["timestamp"] == "2026-09-20 11:00:00"
    assert data["system"]["hostname"] == "testhost"
    assert data["cpu"]["usage_percent"] == 45.5
    assert data["memory"]["usage_percent"] == 50.0
    assert len(data["disk"]["partitions"]) == 1
    assert data["network"]["connection_count"] == 15
    assert data["battery"]["percent"] == 85.0
    assert len(data["processes"]) == 1
    assert data["processes"][0]["pid"] == 1234


def test_dashboard_config_defaults():
    cfg = DashboardConfig()
    assert cfg.refresh_interval == 1.0
    assert cfg.history_points == 30
    assert cfg.cpu_warning_threshold == 75.0
    assert cfg.cpu_critical_threshold == 90.0
    data = cfg.to_dict()
    assert data["refresh_interval"] == 1.0
