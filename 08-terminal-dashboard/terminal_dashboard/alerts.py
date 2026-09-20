from terminal_dashboard.models import Alert, AlertLevel, DashboardConfig, DashboardSnapshot


def evaluate_alerts(snapshot: DashboardSnapshot, config: DashboardConfig) -> list[Alert]:
    alerts: list[Alert] = []

    cpu_val = snapshot.cpu.usage_percent
    if cpu_val >= config.cpu_critical_threshold:
        alerts.append(
            Alert(
                name="CPU Usage",
                level=AlertLevel.CRITICAL,
                message=f"CPU usage is critical at {cpu_val:.1f}%",
                value=cpu_val,
                threshold=config.cpu_critical_threshold,
            )
        )
    elif cpu_val >= config.cpu_warning_threshold:
        alerts.append(
            Alert(
                name="CPU Usage",
                level=AlertLevel.WARNING,
                message=f"CPU usage is high at {cpu_val:.1f}%",
                value=cpu_val,
                threshold=config.cpu_warning_threshold,
            )
        )

    mem_val = snapshot.memory.usage_percent
    if mem_val >= config.memory_critical_threshold:
        alerts.append(
            Alert(
                name="Memory Usage",
                level=AlertLevel.CRITICAL,
                message=f"Memory usage is critical at {mem_val:.1f}%",
                value=mem_val,
                threshold=config.memory_critical_threshold,
            )
        )
    elif mem_val >= config.memory_warning_threshold:
        alerts.append(
            Alert(
                name="Memory Usage",
                level=AlertLevel.WARNING,
                message=f"Memory usage is high at {mem_val:.1f}%",
                value=mem_val,
                threshold=config.memory_warning_threshold,
            )
        )

    if snapshot.memory.swap_total_bytes > 0:
        swap_val = snapshot.memory.swap_usage_percent
        if swap_val >= config.swap_critical_threshold:
            alerts.append(
                Alert(
                    name="Swap Usage",
                    level=AlertLevel.CRITICAL,
                    message=f"Swap usage is critical at {swap_val:.1f}%",
                    value=swap_val,
                    threshold=config.swap_critical_threshold,
                )
            )
        elif swap_val >= config.swap_warning_threshold:
            alerts.append(
                Alert(
                    name="Swap Usage",
                    level=AlertLevel.WARNING,
                    message=f"Swap usage is high at {swap_val:.1f}%",
                    value=swap_val,
                    threshold=config.swap_warning_threshold,
                )
            )

    for part in snapshot.disk.partitions:
        if part.usage_percent >= config.disk_critical_threshold:
            alerts.append(
                Alert(
                    name=f"Disk {part.mountpoint}",
                    level=AlertLevel.CRITICAL,
                    message=f"Partition {part.mountpoint} is critical at {part.usage_percent:.1f}%",
                    value=part.usage_percent,
                    threshold=config.disk_critical_threshold,
                )
            )
        elif part.usage_percent >= config.disk_warning_threshold:
            alerts.append(
                Alert(
                    name=f"Disk {part.mountpoint}",
                    level=AlertLevel.WARNING,
                    message=f"Partition {part.mountpoint} is high at {part.usage_percent:.1f}%",
                    value=part.usage_percent,
                    threshold=config.disk_warning_threshold,
                )
            )

    if snapshot.battery and snapshot.battery.power_plugged is False:
        bat_val = snapshot.battery.percent
        if bat_val <= 5.0:
            alerts.append(
                Alert(
                    name="Battery",
                    level=AlertLevel.CRITICAL,
                    message=f"Battery critically low at {bat_val:.0f}%",
                    value=bat_val,
                    threshold=5.0,
                )
            )
        elif bat_val <= 15.0:
            alerts.append(
                Alert(
                    name="Battery",
                    level=AlertLevel.WARNING,
                    message=f"Battery low at {bat_val:.0f}%",
                    value=bat_val,
                    threshold=15.0,
                )
            )

    return alerts


def get_health_status(alerts: list[Alert]) -> tuple[int, str]:
    if any(a.level == AlertLevel.CRITICAL for a in alerts):
        return 2, "CRITICAL"
    if any(a.level == AlertLevel.WARNING for a in alerts):
        return 1, "WARNING"
    return 0, "HEALTHY"
