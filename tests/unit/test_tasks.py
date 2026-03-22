# tests/unit/test_tasks.py
"""Tasks模块单元测试"""

import pytest
import tempfile
import os
import asyncio
from datetime import date, datetime
from unittest.mock import Mock, AsyncMock, patch
import sys
sys.path.insert(0, '/root/ai/claudecode/first/stock-scraper')

from tasks.base import BaseTask, TaskLock, TaskStatus
from tasks.full_sync_task import FullSyncTask
from tasks.daily_sync_task import DailySyncTask
from tasks.verification_task import VerificationTask


class TestTaskLock:
    """TaskLock测试"""

    def test_lock_acquire_release(self):
        """测试锁的获取和释放"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            lock_file = f.name

        try:
            lock = TaskLock(lock_file)
            assert lock.acquire() == True, '首次获取锁应成功'

            # 测试重复获取（应失败）
            assert lock.acquire() == False, '重复获取锁应失败'

            # 释放锁
            lock.release()
            assert lock.release() == False, '释放未持有的锁应返回False'

            # 再次获取（应成功）
            assert lock.acquire() == True, '释放后获取锁应成功'

            # 清理
            lock.release()
        finally:
            if os.path.exists(lock_file):
                os.unlink(lock_file)

    def test_lock_context_manager(self):
        """测试锁的上下文管理器"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            lock_file = f.name

        try:
            lock = TaskLock(lock_file)

            # 使用上下文管理器
            with lock:
                assert lock.acquire() == False, '上下文管理器内重复获取应失败'

            # 退出后应自动释放
            assert lock.acquire() == True, '退出上下文后获取锁应成功'
            lock.release()
        finally:
            if os.path.exists(lock_file):
                os.unlink(lock_file)


class TestTaskStatus:
    """TaskStatus测试"""

    def test_task_status_values(self):
        """测试任务状态枚举值"""
        assert TaskStatus.PENDING == 'pending'
        assert TaskStatus.RUNNING == 'running'
        assert TaskStatus.SUCCESS == 'success'
        assert TaskStatus.FAILED == 'failed'


class TestBaseTask:
    """BaseTask测试"""

    def test_base_task_is_abstract(self):
        """测试BaseTask是抽象类"""
        from abc import ABC
        assert issubclass(BaseTask, ABC)

    def test_base_task_has_abstract_method(self):
        """测试BaseTask有execute抽象方法"""
        assert hasattr(BaseTask, 'execute')

    def test_base_task_init(self):
        """测试BaseTask初始化"""
        # BaseTask是抽象类，需要创建子类实例来测试
        class ConcreteTask(BaseTask):
            async def execute(self):
                return {}

        task = ConcreteTask(task_name='test_task', sync_service=Mock(), storage=Mock())
        assert task.task_name == 'test_task'
        assert task.sync_service is not None
        assert task.storage is not None

    def test_base_task_lock_file_path(self):
        """测试锁文件路径"""
        # BaseTask是抽象类，需要创建子类实例来测试
        class ConcreteTask(BaseTask):
            async def execute(self):
                return {}

        task = ConcreteTask(task_name='test_task', sync_service=Mock(), storage=Mock())
        expected_path = f'/tmp/test_task.lock'
        assert task.lock_file == expected_path


class TestFullSyncTask:
    """FullSyncTask测试"""

    def test_full_sync_task_initialization(self):
        """测试FullSyncTask初始化"""
        mock_sync_service = Mock()
        mock_storage = Mock()

        task = FullSyncTask(
            sync_service=mock_sync_service,
            storage=mock_storage
        )

        assert task.task_name == 'full_sync'
        assert task.sync_service == mock_sync_service
        assert task.storage == mock_storage

    @pytest.mark.asyncio
    async def test_full_sync_execute(self):
        """测试FullSyncTask执行"""
        mock_sync_service = AsyncMock()
        mock_sync_service.batch_sync = AsyncMock(return_value={
            'total': 2,
            'success_count': 2,
            'failed_count': 0,
            'results': []
        })
        mock_storage = AsyncMock()
        mock_storage.query = AsyncMock(return_value=[
            {'stock_code': '600000'},
            {'stock_code': '600001'}
        ])

        task = FullSyncTask(
            sync_service=mock_sync_service,
            storage=mock_storage
        )

        # 直接设置stock_list以避免依赖_get_all_stocks
        task.stock_list = ['600000', '600001']

        result = await task.execute()

        assert result['total'] == 2
        assert result['success_count'] == 2


class TestDailySyncTask:
    """DailySyncTask测试"""

    def test_daily_sync_task_initialization(self):
        """测试DailySyncTask初始化"""
        mock_sync_service = Mock()
        mock_storage = Mock()

        task = DailySyncTask(
            sync_service=mock_sync_service,
            storage=mock_storage
        )

        assert task.task_name == 'daily_sync'
        assert task.sync_service == mock_sync_service
        assert task.storage == mock_storage

    @pytest.mark.asyncio
    async def test_daily_sync_execute(self):
        """测试DailySyncTask执行"""
        mock_sync_service = AsyncMock()
        mock_sync_service.batch_sync = AsyncMock(return_value={
            'total': 5,
            'success_count': 5,
            'failed_count': 0,
            'results': []
        })
        mock_storage = AsyncMock()
        mock_storage.query = AsyncMock(return_value=[
            {'stock_code': '600000'},
            {'stock_code': '600001'},
            {'stock_code': '600002'},
            {'stock_code': '600003'},
            {'stock_code': '600004'}
        ])

        task = DailySyncTask(
            sync_service=mock_sync_service,
            storage=mock_storage
        )

        # 直接设置stock_list以避免依赖_get_active_stocks
        task.stock_list = ['600000', '600001', '600002', '600003', '600004']

        result = await task.execute()

        assert result['total'] == 5
        assert result['success_count'] == 5


class TestVerificationTask:
    """VerificationTask测试"""

    def test_verification_task_initialization(self):
        """测试VerificationTask初始化"""
        mock_sync_service = Mock()
        mock_storage = Mock()

        task = VerificationTask(
            sync_service=mock_sync_service,
            storage=mock_storage
        )

        assert task.task_name == 'verification'
        assert task.sync_service == mock_sync_service
        assert task.storage == mock_storage

    def test_verification_task_date_validation(self):
        """测试VerificationTask日期验证"""
        mock_sync_service = Mock()
        mock_storage = Mock()

        # start_date > end_date 应该抛出异常
        with pytest.raises(ValueError, match="start_date must be <= end_date"):
            VerificationTask(
                sync_service=mock_sync_service,
                storage=mock_storage,
                start_date=date(2024, 12, 31),
                end_date=date(2024, 1, 1)
            )

    @pytest.mark.asyncio
    async def test_verification_task_execute_no_stocks(self):
        """测试VerificationTask无股票时执行"""
        mock_sync_service = AsyncMock()
        mock_storage = AsyncMock()
        mock_storage.query = AsyncMock(return_value=[])

        task = VerificationTask(
            sync_service=mock_sync_service,
            storage=mock_storage
        )

        task.stock_list = []

        result = await task.execute()

        assert result['total'] == 0
        assert result['verified'] == 0

    @pytest.mark.asyncio
    async def test_verification_task_with_stock_list(self):
        """测试VerificationTask使用股票列表"""
        mock_sync_service = AsyncMock()
        mock_storage = AsyncMock()
        mock_storage.query = AsyncMock(return_value=[
            {'stock_code': '600000', 'trade_date': '2024-01-02', 'open': 10.0,
             'high': 10.5, 'low': 9.8, 'close': 10.2, 'volume': 1000000}
        ])

        task = VerificationTask(
            sync_service=mock_sync_service,
            storage=mock_storage
        )

        task.stock_list = ['600000']

        result = await task.execute()

        assert result['total'] == 1
