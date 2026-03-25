# data_source/rate_limiter.py
"""请求限流器"""

import asyncio
import time
from enum import Enum


class SyncMode(Enum):
    """同步模式枚举"""
    FULL = "full"           # 全量同步 - 使用 full_sync_interval
    INCREMENTAL = "incremental"  # 增量同步 - 使用 incremental_sync_interval


class RateLimiter:
    """请求限流器

    控制请求频率，避免API限流
    支持根据同步模式调整请求间隔
    """

    def __init__(
        self,
        base_interval: float = 1.0,
        full_sync_interval: float = 1.0,
        incremental_sync_interval: float = 0.8
    ):
        """初始化限流器

        Args:
            base_interval: 基础请求间隔（秒），默认1.0秒
            full_sync_interval: 全量同步间隔（秒），默认1.0秒
            incremental_sync_interval: 增量同步间隔（秒），默认0.8秒
        """
        self.base_interval = base_interval
        self.full_sync_interval = full_sync_interval
        self.incremental_sync_interval = incremental_sync_interval
        self.last_request_time: float = 0.0
        self._current_interval: float = base_interval

    async def wait(self, sync_mode: SyncMode = None) -> None:
        """等待以满足请求间隔要求

        如果距离上次请求时间小于间隔时间，则等待

        Args:
            sync_mode: 同步模式，决定使用的间隔
        """
        # 根据同步模式选择间隔
        if sync_mode == SyncMode.FULL:
            self._current_interval = self.full_sync_interval
        elif sync_mode == SyncMode.INCREMENTAL:
            self._current_interval = self.incremental_sync_interval
        else:
            self._current_interval = self.base_interval

        current_time = time.time()
        elapsed = current_time - self.last_request_time

        if elapsed < self._current_interval:
            wait_time = self._current_interval - elapsed
            await asyncio.sleep(wait_time)

        self.last_request_time = time.time()

    def reset(self) -> None:
        """重置限流器"""
        self.last_request_time = 0.0

    def set_interval(self, interval: float) -> None:
        """设置基础请求间隔

        Args:
            interval: 请求间隔（秒）
        """
        self.base_interval = interval
        self._current_interval = interval

    @property
    def current_interval(self) -> float:
        """获取当前使用的间隔"""
        return self._current_interval
