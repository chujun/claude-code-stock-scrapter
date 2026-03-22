# tasks/base.py
"""任务调度基类"""

import os
import fcntl
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional

from storage.base import BaseRepository
from services.sync_service import StockSyncService


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'


class TaskLock:
    """文件锁实现

    使用fcntl实现进程级别的锁机制，防止并发执行
    """

    def __init__(self, lock_file: str):
        """初始化锁

        Args:
            lock_file: 锁文件路径
        """
        self.lock_file = lock_file
        self._fd: Optional[int] = None

    def acquire(self) -> bool:
        """尝试获取锁

        Returns:
            bool: 获取成功返回True，失败返回False
        """
        if self._fd is not None:
            return False

        try:
            # 确保目录存在
            lock_dir = os.path.dirname(self.lock_file)
            if lock_dir and not os.path.exists(lock_dir):
                os.makedirs(lock_dir, exist_ok=True)

            # 打开文件（不存在则创建）
            self._fd = os.open(self.lock_file, os.O_CREAT | os.O_RDWR)

            # 非阻塞获取排他锁
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            except (IOError, OSError):
                # 锁已被持有
                os.close(self._fd)
                self._fd = None
                return False
        except (IOError, OSError):
            return False

    def release(self) -> bool:
        """释放锁

        Returns:
            bool: 释放成功返回True，锁未持有返回False
        """
        if self._fd is None:
            return False

        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None
            return True
        except (IOError, OSError):
            if self._fd is not None:
                try:
                    os.close(self._fd)
                except OSError:
                    pass
                self._fd = None
            return False

    def __enter__(self):
        """上下文管理器入口"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.release()
        return False

    def __del__(self):
        """析构时确保锁被释放"""
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                os.close(self._fd)
            except (IOError, OSError):
                pass
            self._fd = None


class BaseTask(ABC):
    """任务基类

    所有同步任务都应继承此类并实现execute方法
    """

    def __init__(
        self,
        task_name: str,
        sync_service: StockSyncService,
        storage: BaseRepository
    ):
        """初始化任务

        Args:
            task_name: 任务名称
            sync_service: 同步服务
            storage: 存储库
        """
        self.task_name = task_name
        self.sync_service = sync_service
        self.storage = storage
        self._lock_file = f'/tmp/{task_name}.lock'

    @property
    def lock_file(self) -> str:
        """获取锁文件路径"""
        return self._lock_file

    @property
    def lock(self) -> TaskLock:
        """获取任务锁"""
        return TaskLock(self._lock_file)

    @abstractmethod
    async def execute(self) -> Dict[str, Any]:
        """执行任务

        Returns:
            Dict: 任务执行结果
        """
        pass

    async def update_status(
        self,
        stock_code: str,
        status: str,
        sync_type: str = 'full',
        error_msg: Optional[str] = None
    ) -> None:
        """更新同步状态到数据库

        Args:
            stock_code: 股票代码
            status: 状态
            sync_type: 同步类型
            error_msg: 错误信息
        """
        from models.sync_status import SyncStatus
        from datetime import datetime

        status_record = SyncStatus(
            stock_code=stock_code,
            sync_type=sync_type,
            status=status,
            started_at=datetime.now(),
            finished_at=datetime.now() if status in ('success', 'failed') else None,
            error_message=error_msg
        )

        try:
            await self.storage.insert('sync_status', [status_record.model_dump()])
        except Exception:
            # 状态更新失败不影响主流程
            pass
