"""
定时器调度模块
管理壁纸自动切换的定时任务
"""
import threading
from typing import Callable, Optional


class WallpaperScheduler:
    """壁纸切换定时器，支持启动 / 停止 / 重置"""

    def __init__(self, callback: Callable[[], None], interval_minutes: int = 1440):
        """
        Args:
            callback: 定时触发时执行的回调函数
            interval_minutes: 切换间隔（分钟）
        """
        self._callback = callback
        self._interval_seconds = interval_minutes * 60
        self._timer: Optional[threading.Timer] = None
        self._running = False

    @property
    def interval_minutes(self) -> int:
        return self._interval_seconds // 60

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """启动定时器"""
        if self._running:
            return
        self._running = True
        self._schedule_next()

    def stop(self) -> None:
        """停止定时器"""
        self._running = False
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def reset(self, new_interval_minutes: Optional[int] = None) -> None:
        """
        重置定时器（切换间隔后调用，或在手动切换后重新计时）

        Args:
            new_interval_minutes: 新的间隔（分钟），不传则保持原间隔
        """
        if new_interval_minutes is not None:
            self._interval_seconds = new_interval_minutes * 60
        if self._running:
            if self._timer is not None:
                self._timer.cancel()
            self._schedule_next()

    def _schedule_next(self) -> None:
        """安排下一次触发"""
        if not self._running:
            return
        self._timer = threading.Timer(self._interval_seconds, self._on_tick)
        self._timer.daemon = True
        self._timer.start()

    def _on_tick(self) -> None:
        """定时器触发时执行"""
        if not self._running:
            return
        try:
            self._callback()
        finally:
            # 无论回调是否成功，都安排下一次触发
            self._schedule_next()
