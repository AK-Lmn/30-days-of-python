from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class AlertLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    name: str
    level: AlertLevel
    message: str
    value: float
    threshold: float

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["level"] = self.level.value
        return data


@dataclass
class SystemInfo:
    hostname: str
    os_name: str
    os_release: str
    os_version: str
    architecture: str
    python_version: str
    boot_time: str
    uptime_seconds: float
    uptime_formatted: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CpuMetrics:
    usage_percent: float
    physical_cores: int
    logical_cores: int
    frequency_current_mhz: float | None
    frequency_min_mhz: float | None
    frequency_max_mhz: float | None
    per_core_percent: list[float]
    load_averages: list[float] | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryMetrics:
    total_bytes: int
    used_bytes: int
    available_bytes: int
    free_bytes: int
    usage_percent: float
    swap_total_bytes: int
    swap_used_bytes: int
    swap_free_bytes: int
    swap_usage_percent: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DiskPartitionMetrics:
    device: str
    mountpoint: str
    fstype: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    usage_percent: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DiskIoMetrics:
    read_bytes_per_sec: float
    write_bytes_per_sec: float
    read_count_per_sec: float
    write_count_per_sec: float
    total_read_bytes: int
    total_write_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DiskMetrics:
    partitions: list[DiskPartitionMetrics]
    io: DiskIoMetrics | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "partitions": [p.to_dict() for p in self.partitions],
            "io": self.io.to_dict() if self.io else None,
        }


@dataclass
class NetworkInterfaceMetrics:
    name: str
    is_up: bool
    ip_address: str | None
    netmask: str | None
    mac_address: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NetworkIoMetrics:
    bytes_sent_per_sec: float
    bytes_recv_per_sec: float
    packets_sent_per_sec: float
    packets_recv_per_sec: float
    total_bytes_sent: int
    total_bytes_recv: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NetworkMetrics:
    interfaces: list[NetworkInterfaceMetrics]
    io: NetworkIoMetrics | None
    connection_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "interfaces": [i.to_dict() for i in self.interfaces],
            "io": self.io.to_dict() if self.io else None,
            "connection_count": self.connection_count,
        }


@dataclass
class BatteryMetrics:
    percent: float
    power_plugged: bool | None
    seconds_left: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProcessInfo:
    pid: int
    name: str
    username: str
    status: str
    cpu_percent: float
    memory_percent: float
    memory_bytes: int
    threads: int
    create_time: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DashboardSnapshot:
    timestamp: str
    system: SystemInfo
    cpu: CpuMetrics
    memory: MemoryMetrics
    disk: DiskMetrics
    network: NetworkMetrics
    battery: BatteryMetrics | None
    processes: list[ProcessInfo]
    alerts: list[Alert]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "system": self.system.to_dict(),
            "cpu": self.cpu.to_dict(),
            "memory": self.memory.to_dict(),
            "disk": self.disk.to_dict(),
            "network": self.network.to_dict(),
            "battery": self.battery.to_dict() if self.battery else None,
            "processes": [p.to_dict() for p in self.processes],
            "alerts": [a.to_dict() for a in self.alerts],
        }


@dataclass
class DashboardConfig:
    refresh_interval: float = 1.0
    history_points: int = 30
    process_limit: int = 15
    process_sort_by: str = "cpu"
    cpu_warning_threshold: float = 75.0
    cpu_critical_threshold: float = 90.0
    memory_warning_threshold: float = 80.0
    memory_critical_threshold: float = 95.0
    swap_warning_threshold: float = 60.0
    swap_critical_threshold: float = 85.0
    disk_warning_threshold: float = 80.0
    disk_critical_threshold: float = 90.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
