from datetime import datetime, timezone
import os
import platform
import socket
import time
from typing import Any

import psutil

from terminal_dashboard.models import (
    BatteryMetrics,
    CpuMetrics,
    DashboardSnapshot,
    DiskIoMetrics,
    DiskMetrics,
    DiskPartitionMetrics,
    NetworkInterfaceMetrics,
    NetworkIoMetrics,
    NetworkMetrics,
    MemoryMetrics,
    ProcessInfo,
    SystemInfo,
)


def format_duration(seconds: float) -> str:
    total_seconds = int(seconds)
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


class MetricsCollector:
    def __init__(self) -> None:
        self._last_disk_io: Any | None = None
        self._last_disk_time: float | None = None
        self._last_net_io: Any | None = None
        self._last_net_time: float | None = None
        self._initialize_baselines()

    def _initialize_baselines(self) -> None:
        try:
            psutil.cpu_percent(interval=None)
            psutil.cpu_percent(interval=None, percpu=True)
            self._last_disk_io = psutil.disk_io_counters()
            self._last_disk_time = time.time()
            self._last_net_io = psutil.net_io_counters()
            self._last_net_time = time.time()
        except Exception:
            pass

    def collect_system_info(self) -> SystemInfo:
        boot_timestamp = psutil.boot_time()
        boot_dt = datetime.fromtimestamp(boot_timestamp)
        uptime = time.time() - boot_timestamp
        hostname = platform.node() or socket.gethostname()

        return SystemInfo(
            hostname=hostname,
            os_name=platform.system(),
            os_release=platform.release(),
            os_version=platform.version(),
            architecture=platform.machine(),
            python_version=platform.python_version(),
            boot_time=boot_dt.strftime("%Y-%m-%d %H:%M:%S"),
            uptime_seconds=uptime,
            uptime_formatted=format_duration(uptime),
        )

    def collect_cpu(self) -> CpuMetrics:
        overall_usage = psutil.cpu_percent(interval=None)
        per_core = psutil.cpu_percent(interval=None, percpu=True)
        physical = psutil.cpu_count(logical=False) or 1
        logical = psutil.cpu_count(logical=True) or 1

        freq = psutil.cpu_freq()
        cur_freq = freq.current if freq else None
        min_freq = freq.min if freq else None
        max_freq = freq.max if freq else None

        load_avg = None
        if hasattr(os, "getloadavg"):
            try:
                load_avg = list(os.getloadavg())
            except OSError:
                load_avg = None

        return CpuMetrics(
            usage_percent=overall_usage,
            physical_cores=physical,
            logical_cores=logical,
            frequency_current_mhz=cur_freq,
            frequency_min_mhz=min_freq,
            frequency_max_mhz=max_freq,
            per_core_percent=per_core,
            load_averages=load_avg,
        )

    def collect_memory(self) -> MemoryMetrics:
        vmem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return MemoryMetrics(
            total_bytes=vmem.total,
            used_bytes=vmem.used,
            available_bytes=vmem.available,
            free_bytes=vmem.free,
            usage_percent=vmem.percent,
            swap_total_bytes=swap.total,
            swap_used_bytes=swap.used,
            swap_free_bytes=swap.free,
            swap_usage_percent=swap.percent,
        )

    def collect_disk(self) -> DiskMetrics:
        partitions: list[DiskPartitionMetrics] = []
        try:
            raw_partitions = psutil.disk_partitions(all=False)
        except Exception:
            raw_partitions = []

        seen_mounts: set[str] = set()
        for p in raw_partitions:
            if p.mountpoint in seen_mounts:
                continue
            seen_mounts.add(p.mountpoint)
            try:
                usage = psutil.disk_usage(p.mountpoint)
                partitions.append(
                    DiskPartitionMetrics(
                        device=p.device,
                        mountpoint=p.mountpoint,
                        fstype=p.fstype,
                        total_bytes=usage.total,
                        used_bytes=usage.used,
                        free_bytes=usage.free,
                        usage_percent=usage.percent,
                    )
                )
            except (PermissionError, OSError):
                continue

        now = time.time()
        disk_io: DiskIoMetrics | None = None
        try:
            current_io = psutil.disk_io_counters()
            if current_io and self._last_disk_io and self._last_disk_time:
                time_diff = max(now - self._last_disk_time, 0.001)
                read_bytes_rate = max(0.0, (current_io.read_bytes - self._last_disk_io.read_bytes) / time_diff)
                write_bytes_rate = max(0.0, (current_io.write_bytes - self._last_disk_io.write_bytes) / time_diff)
                read_count_rate = max(0.0, (current_io.read_count - self._last_disk_io.read_count) / time_diff)
                write_count_rate = max(0.0, (current_io.write_count - self._last_disk_io.write_count) / time_diff)
                disk_io = DiskIoMetrics(
                    read_bytes_per_sec=read_bytes_rate,
                    write_bytes_per_sec=write_bytes_rate,
                    read_count_per_sec=read_count_rate,
                    write_count_per_sec=write_count_rate,
                    total_read_bytes=current_io.read_bytes,
                    total_write_bytes=current_io.write_bytes,
                )
            elif current_io:
                disk_io = DiskIoMetrics(
                    read_bytes_per_sec=0.0,
                    write_bytes_per_sec=0.0,
                    read_count_per_sec=0.0,
                    write_count_per_sec=0.0,
                    total_read_bytes=current_io.read_bytes,
                    total_write_bytes=current_io.write_bytes,
                )
            self._last_disk_io = current_io
            self._last_disk_time = now
        except Exception:
            disk_io = None

        return DiskMetrics(partitions=partitions, io=disk_io)

    def collect_network(self) -> NetworkMetrics:
        interfaces: list[NetworkInterfaceMetrics] = []
        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            for iface_name, addr_list in addrs.items():
                is_up = stats[iface_name].isup if iface_name in stats else True
                ipv4 = None
                netmask = None
                mac = None
                for a in addr_list:
                    if getattr(socket, "AF_INET", None) and a.family == socket.AF_INET:
                        ipv4 = a.address
                        netmask = a.netmask
                    elif hasattr(psutil, "AF_LINK") and a.family == psutil.AF_LINK:
                        mac = a.address
                    elif getattr(socket, "AF_LINK", None) and a.family == socket.AF_LINK:
                        mac = a.address

                if ipv4 or is_up:
                    interfaces.append(
                        NetworkInterfaceMetrics(
                            name=iface_name,
                            is_up=is_up,
                            ip_address=ipv4,
                            netmask=netmask,
                            mac_address=mac,
                        )
                    )
        except Exception:
            pass

        now = time.time()
        net_io: NetworkIoMetrics | None = None
        try:
            current_net = psutil.net_io_counters()
            if current_net and self._last_net_io and self._last_net_time:
                time_diff = max(now - self._last_net_time, 0.001)
                sent_bytes_rate = max(0.0, (current_net.bytes_sent - self._last_net_io.bytes_sent) / time_diff)
                recv_bytes_rate = max(0.0, (current_net.bytes_recv - self._last_net_io.bytes_recv) / time_diff)
                sent_pkt_rate = max(0.0, (current_net.packets_sent - self._last_net_io.packets_sent) / time_diff)
                recv_pkt_rate = max(0.0, (current_net.packets_recv - self._last_net_io.packets_recv) / time_diff)
                net_io = NetworkIoMetrics(
                    bytes_sent_per_sec=sent_bytes_rate,
                    bytes_recv_per_sec=recv_bytes_rate,
                    packets_sent_per_sec=sent_pkt_rate,
                    packets_recv_per_sec=recv_pkt_rate,
                    total_bytes_sent=current_net.bytes_sent,
                    total_bytes_recv=current_net.bytes_recv,
                )
            elif current_net:
                net_io = NetworkIoMetrics(
                    bytes_sent_per_sec=0.0,
                    bytes_recv_per_sec=0.0,
                    packets_sent_per_sec=0.0,
                    packets_recv_per_sec=0.0,
                    total_bytes_sent=current_net.bytes_sent,
                    total_bytes_recv=current_net.bytes_recv,
                )
            self._last_net_io = current_net
            self._last_net_time = now
        except Exception:
            net_io = None

        connection_count = 0
        try:
            connections = psutil.net_connections(kind="inet")
            connection_count = len(connections)
        except Exception:
            connection_count = 0

        return NetworkMetrics(
            interfaces=interfaces,
            io=net_io,
            connection_count=connection_count,
        )

    def collect_battery(self) -> BatteryMetrics | None:
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return None
            secs_left = battery.secsleft if battery.secsleft > 0 else None
            return BatteryMetrics(
                percent=battery.percent,
                power_plugged=battery.power_plugged,
                seconds_left=secs_left,
            )
        except Exception:
            return None

    def collect_processes(self, limit: int = 15, sort_by: str = "cpu") -> list[ProcessInfo]:
        procs: list[ProcessInfo] = []
        attrs = [
            "pid",
            "name",
            "username",
            "status",
            "cpu_percent",
            "memory_percent",
            "memory_info",
            "num_threads",
            "create_time",
        ]

        for p in psutil.process_iter(attrs=attrs):
            try:
                info = p.info
                mem_info = info.get("memory_info")
                mem_bytes = mem_info.rss if mem_info else 0
                create_timestamp = info.get("create_time") or 0
                create_dt = datetime.fromtimestamp(create_timestamp) if create_timestamp else None
                create_str = create_dt.strftime("%H:%M:%S") if create_dt else "N/A"

                procs.append(
                    ProcessInfo(
                        pid=info.get("pid") or 0,
                        name=info.get("name") or "unknown",
                        username=info.get("username") or "N/A",
                        status=str(info.get("status") or "running"),
                        cpu_percent=float(info.get("cpu_percent") or 0.0),
                        memory_percent=float(info.get("memory_percent") or 0.0),
                        memory_bytes=mem_bytes,
                        threads=int(info.get("num_threads") or 1),
                        create_time=create_str,
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if sort_by == "cpu":
            procs.sort(key=lambda p: p.cpu_percent, reverse=True)
        elif sort_by == "mem" or sort_by == "memory":
            procs.sort(key=lambda p: p.memory_percent, reverse=True)
        elif sort_by == "name":
            procs.sort(key=lambda p: p.name.lower())
        elif sort_by == "pid":
            procs.sort(key=lambda p: p.pid)

        return procs[:limit]

    def collect_snapshot(self, process_limit: int = 15, sort_by: str = "cpu") -> DashboardSnapshot:
        system = self.collect_system_info()
        cpu = self.collect_cpu()
        memory = self.collect_memory()
        disk = self.collect_disk()
        network = self.collect_network()
        battery = self.collect_battery()
        processes = self.collect_processes(limit=process_limit, sort_by=sort_by)

        now_str = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")

        return DashboardSnapshot(
            timestamp=now_str,
            system=system,
            cpu=cpu,
            memory=memory,
            disk=disk,
            network=network,
            battery=battery,
            processes=processes,
            alerts=[],
        )
