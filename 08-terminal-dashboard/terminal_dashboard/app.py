from collections import deque
import time

from rich.console import Console
from rich.live import Live

from terminal_dashboard.alerts import evaluate_alerts
from terminal_dashboard.collector import MetricsCollector
from terminal_dashboard.models import DashboardConfig
from terminal_dashboard.views import compose_dashboard_layout


class DashboardApp:
    def __init__(self, config: DashboardConfig | None = None) -> None:
        self.config = config or DashboardConfig()
        self.collector = MetricsCollector()
        self.console = Console()
        self.cpu_history: deque[float] = deque(maxlen=self.config.history_points)
        self.mem_history: deque[float] = deque(maxlen=self.config.history_points)
        self.net_recv_history: deque[float] = deque(maxlen=self.config.history_points)
        self.net_sent_history: deque[float] = deque(maxlen=self.config.history_points)

    def step(self) -> any:
        snapshot = self.collector.collect_snapshot(
            process_limit=self.config.process_limit,
            sort_by=self.config.process_sort_by,
        )
        snapshot.alerts = evaluate_alerts(snapshot, self.config)

        self.cpu_history.append(snapshot.cpu.usage_percent)
        self.mem_history.append(snapshot.memory.usage_percent)
        if snapshot.network.io:
            self.net_recv_history.append(snapshot.network.io.bytes_recv_per_sec)
            self.net_sent_history.append(snapshot.network.io.bytes_sent_per_sec)
        else:
            self.net_recv_history.append(0.0)
            self.net_sent_history.append(0.0)

        return compose_dashboard_layout(
            snapshot=snapshot,
            cpu_history=self.cpu_history,
            mem_history=self.mem_history,
            net_recv_history=self.net_recv_history,
            net_sent_history=self.net_sent_history,
            refresh_interval=self.config.refresh_interval,
            sort_by=self.config.process_sort_by,
        )

    def run(self, max_iterations: int | None = None) -> None:
        iteration = 0
        try:
            with Live(self.step(), console=self.console, screen=True, refresh_per_second=4) as live:
                while True:
                    iteration += 1
                    if max_iterations is not None and iteration >= max_iterations:
                        break
                    time.sleep(self.config.refresh_interval)
                    live.update(self.step())
        except KeyboardInterrupt:
            pass
        finally:
            self.console.print("\n[bold cyan]Terminal Dashboard closed.[/bold cyan]")
