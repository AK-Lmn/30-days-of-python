import asyncio
from pathlib import Path
import threading
import time
from typing import Callable, List, Optional

import httpx

from website_monitor.checker import check_target, async_check_target
from website_monitor.db import (
    record_check,
    list_targets,
    get_active_incident,
    open_incident,
    resolve_incident,
    get_consecutive_failures,
)
from website_monitor.models import CheckResult, MonitorTarget
from website_monitor.notifier import NotificationManager


class MonitorEngine:
    def __init__(
        self,
        db_path: Optional[Path] = None,
        notifier: Optional[NotificationManager] = None,
    ):
        self.db_path = db_path
        self.notifier = notifier or NotificationManager()
        self.is_running = False
        self._stop_event = threading.Event()

    def check_target_sync(
        self,
        target: MonitorTarget,
        client: Optional[httpx.Client] = None,
        callback: Optional[Callable[[MonitorTarget, CheckResult], None]] = None,
    ) -> CheckResult:
        result = check_target(target, client=client)
        if target.id is not None:
            record_check(result, db_path=self.db_path)

            if not result.is_up:
                active_inc = get_active_incident(target.id, db_path=self.db_path)
                if not active_inc:
                    current_fails = max(
                        self.notifier.failure_counts.get(target.id, 0) + 1,
                        get_consecutive_failures(target.id, db_path=self.db_path),
                    )
                    if current_fails >= self.notifier.consecutive_failures_threshold:
                        reason = result.error_message or "Health check failed"
                        open_incident(
                            target.id,
                            reason=reason,
                            started_at=result.checked_at,
                            db_path=self.db_path,
                        )
            else:
                active_inc = get_active_incident(target.id, db_path=self.db_path)
                if active_inc and active_inc.id is not None:
                    resolve_incident(
                        active_inc.id,
                        ended_at=result.checked_at,
                        db_path=self.db_path,
                    )

            self.notifier.handle_check(result, target, client=client)

        if callback:
            callback(target, result)

        return result

    async def _async_check_worker(
        self,
        target: MonitorTarget,
        client: httpx.AsyncClient,
        callback: Optional[Callable[[MonitorTarget, CheckResult], None]] = None,
    ) -> CheckResult:
        result = await async_check_target(target, client=client)
        if target.id is not None:
            record_check(result, db_path=self.db_path)

            if not result.is_up:
                active_inc = get_active_incident(target.id, db_path=self.db_path)
                if not active_inc:
                    current_fails = max(
                        self.notifier.failure_counts.get(target.id, 0) + 1,
                        get_consecutive_failures(target.id, db_path=self.db_path),
                    )
                    if current_fails >= self.notifier.consecutive_failures_threshold:
                        reason = result.error_message or "Health check failed"
                        open_incident(
                            target.id,
                            reason=reason,
                            started_at=result.checked_at,
                            db_path=self.db_path,
                        )
            else:
                active_inc = get_active_incident(target.id, db_path=self.db_path)
                if active_inc and active_inc.id is not None:
                    resolve_incident(
                        active_inc.id,
                        ended_at=result.checked_at,
                        db_path=self.db_path,
                    )

            self.notifier.handle_check(result, target)

        if callback:
            callback(target, result)

        return result

    async def check_all_async(
        self,
        tag: Optional[str] = None,
        callback: Optional[Callable[[MonitorTarget, CheckResult], None]] = None,
    ) -> List[CheckResult]:
        targets = list_targets(active_only=True, tag=tag, db_path=self.db_path)
        if not targets:
            return []

        async with httpx.AsyncClient() as client:
            tasks = [self._async_check_worker(t, client, callback) for t in targets]
            return await asyncio.gather(*tasks)

    def check_all(
        self,
        tag: Optional[str] = None,
        callback: Optional[Callable[[MonitorTarget, CheckResult], None]] = None,
    ) -> List[CheckResult]:
        targets = list_targets(active_only=True, tag=tag, db_path=self.db_path)
        results = []
        with httpx.Client() as client:
            for t in targets:
                res = self.check_target_sync(t, client=client, callback=callback)
                results.append(res)
        return results

    def start_loop(
        self,
        interval_seconds: int = 60,
        tag: Optional[str] = None,
        callback: Optional[Callable[[MonitorTarget, CheckResult], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> None:
        self.is_running = True
        actual_stop = stop_event or self._stop_event
        actual_stop.clear()

        while not actual_stop.is_set():
            self.check_all(tag=tag, callback=callback)
            for _ in range(max(1, interval_seconds)):
                if actual_stop.is_set():
                    break
                time.sleep(1)
        self.is_running = False

    def stop_loop(self) -> None:
        self._stop_event.set()
        self.is_running = False
