from unittest.mock import MagicMock, patch

from terminal_dashboard.collector import MetricsCollector, format_duration


def test_format_duration():
    assert format_duration(45) == "45s"
    assert format_duration(125) == "2m 5s"
    assert format_duration(3665) == "1h 1m 5s"
    assert format_duration(90065) == "1d 1h 1m 5s"


def test_collect_system_info():
    collector = MetricsCollector()
    info = collector.collect_system_info()
    assert info.hostname != ""
    assert info.os_name != ""
    assert info.architecture != ""
    assert info.python_version != ""
    assert info.uptime_seconds >= 0


def test_collect_cpu():
    collector = MetricsCollector()
    cpu = collector.collect_cpu()
    assert 0.0 <= cpu.usage_percent <= 100.0
    assert cpu.logical_cores >= 1
    assert cpu.physical_cores >= 1
    assert len(cpu.per_core_percent) >= 1


def test_collect_memory():
    collector = MetricsCollector()
    mem = collector.collect_memory()
    assert mem.total_bytes > 0
    assert mem.used_bytes > 0
    assert 0.0 <= mem.usage_percent <= 100.0


def test_collect_disk():
    collector = MetricsCollector()
    disk = collector.collect_disk()
    assert isinstance(disk.partitions, list)
    if disk.partitions:
        assert disk.partitions[0].total_bytes > 0


def test_collect_network():
    collector = MetricsCollector()
    net = collector.collect_network()
    assert isinstance(net.interfaces, list)
    assert net.connection_count >= 0


def test_collect_processes():
    collector = MetricsCollector()
    procs = collector.collect_processes(limit=5, sort_by="cpu")
    assert isinstance(procs, list)
    assert len(procs) <= 5
    if procs:
        assert procs[0].pid >= 0


def test_collect_snapshot():
    collector = MetricsCollector()
    snap = collector.collect_snapshot(process_limit=3, sort_by="mem")
    assert snap.timestamp != ""
    assert snap.system.hostname != ""
    assert snap.cpu.logical_cores >= 1
    assert snap.memory.total_bytes > 0


@patch("psutil.sensors_battery")
def test_collect_battery_present(mock_battery):
    mock_battery.return_value = MagicMock(percent=88.0, power_plugged=True, secsleft=-1)
    collector = MetricsCollector()
    bat = collector.collect_battery()
    assert bat is not None
    assert bat.percent == 88.0
    assert bat.power_plugged is True


@patch("psutil.sensors_battery")
def test_collect_battery_absent(mock_battery):
    mock_battery.return_value = None
    collector = MetricsCollector()
    bat = collector.collect_battery()
    assert bat is None
