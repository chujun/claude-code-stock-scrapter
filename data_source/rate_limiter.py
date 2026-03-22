# data_source/rate_limiter.py
"""请求限流器"""

import asyncio
import time


class RateLimiter:
    """请求限流器

    控制请求频率，避免API限流
    """

    def __init__(self, base_interval: float = 1.0):
        """初始化限流器

        Args:
            base_interval: 基础请求间隔（秒）
        """
        self.base_interval = base_interval
        self.last_request_time: float = 0.0

    async def wait(self) -> None:
        """等待以满足请求间隔要求

        如果距离上次请求时间小于间隔时间，则等待
        """
        current_time = time.time()
        elapsed = current_time - self.last_request_time

        if elapsed < self.base_interval:
            wait_time = self.base_interval - elapsed
            await asyncio.sleep(wait_time)

        self.last_request_time = time.time()

    def reset(self) -> None:
        """重置限流器"""
        self.last_request_time = 0.0

    def set_interval(self, interval: float) -> None:
        """设置请求间隔

        Args:
            interval: 请求间隔（秒）
        """
        self.base_interval = interval
