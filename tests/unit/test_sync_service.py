# tests/unit/test_sync_service.py
"""StockSyncService单元测试"""

import pytest
from datetime import date
from unittest.mock import Mock, AsyncMock
import sys
sys.path.insert(0, '/root/ai/claudecode/first/stock-scraper')

from services.sync_service import StockSyncService, SyncStrategy
from services.quality_service import QualityService
from services.report_service import ReportService
from data_source.akshare_client import AkshareClient
from storage.clickhouse_repo import ClickHouseRepository
from models.stock_daily import StockDaily


class TestStockSyncService:
    """StockSyncService测试"""

    def test_initialization(self):
        """测试初始化"""
        data_source = Mock(spec=AkshareClient)
        storage = Mock(spec=ClickHouseRepository)
        quality_service = Mock(spec=QualityService)
        report_service = Mock(spec=ReportService)

        service = StockSyncService(
            data_source=data_source,
            storage=storage,
            quality_service=quality_service,
            report_service=report_service
        )

        assert service.data_source is not None
        assert service.storage is not None
        assert service.quality_service is not None

    @pytest.mark.asyncio
    async def test_sync_single_stock(self):
        """测试同步单只股票"""
        data_source = Mock(spec=AkshareClient)
        storage = Mock(spec=ClickHouseRepository)
        quality_service = Mock(spec=QualityService)
        report_service = Mock(spec=ReportService)

        # Mock data_source response
        mock_records = [
            StockDaily(
                stock_code='600000',
                trade_date=date(2024, 1, 2),
                open=10.0,
                high=10.8,
                low=9.9,
                close=10.5,
                volume=1000000,
                data_source='test',
                adjust_type='qfq',
                is_adjusted=True
            )
        ]
        data_source.get_daily = AsyncMock(return_value=mock_records)
        storage.insert = AsyncMock(return_value=1)
        quality_service.batch_validate = AsyncMock(return_value={
            'total': 1, 'passed': 1, 'failed': 0, 'quality_flags': ['good']
        })

        service = StockSyncService(
            data_source=data_source,
            storage=storage,
            quality_service=quality_service,
            report_service=report_service
        )

        result = await service.sync_single_stock('600000')

        assert result is not None
        assert result['stock_code'] == '600000'

    @pytest.mark.asyncio
    async def test_sync_single_stock_no_data(self):
        """测试同步无数据的股票"""
        data_source = Mock(spec=AkshareClient)
        storage = Mock(spec=ClickHouseRepository)
        quality_service = Mock(spec=QualityService)
        report_service = Mock(spec=ReportService)

        data_source.get_daily = AsyncMock(return_value=[])
        storage.insert = AsyncMock(return_value=0)

        service = StockSyncService(
            data_source=data_source,
            storage=storage,
            quality_service=quality_service,
            report_service=report_service
        )

        result = await service.sync_single_stock('600000')

        assert result['success_count'] == 0

    def test_get_sync_status(self):
        """测试获取同步状态"""
        data_source = Mock(spec=AkshareClient)
        storage = Mock(spec=ClickHouseRepository)
        quality_service = Mock(spec=QualityService)
        report_service = Mock(spec=ReportService)

        service = StockSyncService(
            data_source=data_source,
            storage=storage,
            quality_service=quality_service,
            report_service=report_service
        )

        # 设置同步状态
        service.mark_sync_start('600000')
        status = service.get_sync_status('600000')

        assert status is not None
        assert status['stock_code'] == '600000'
        assert status['status'] == 'running'


class TestStockSyncServiceIntegration:
    """StockSyncService集成测试"""

    @pytest.mark.asyncio
    async def test_sync_stock_daily_alias(self):
        """测试sync_stock_daily方法别名"""
        data_source = Mock(spec=AkshareClient)
        storage = Mock(spec=ClickHouseRepository)
        quality_service = Mock(spec=QualityService)
        report_service = Mock(spec=ReportService)

        mock_records = [
            StockDaily(
                stock_code='600000',
                trade_date=date(2024, 1, 2),
                open=10.0,
                high=10.8,
                low=9.9,
                close=10.5,
                volume=1000000,
                data_source='test',
                adjust_type='qfq',
                is_adjusted=True
            )
        ]
        data_source.get_daily = AsyncMock(return_value=mock_records)
        storage.insert = AsyncMock(return_value=1)
        quality_service.batch_validate = AsyncMock(return_value={
            'total': 1, 'passed': 1, 'failed': 0, 'quality_flags': ['good']
        })

        service = StockSyncService(
            data_source=data_source,
            storage=storage,
            quality_service=quality_service,
            report_service=report_service
        )

        # 使用 sync_stock_daily 别名
        result = await service.sync_stock_daily(
            '600000',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )

        assert result is not None
        assert result['stock_code'] == '600000'
        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_batch_sync_multiple_stocks(self):
        """测试批量同步多只股票"""
        data_source = Mock(spec=AkshareClient)
        storage = Mock(spec=ClickHouseRepository)
        quality_service = Mock(spec=QualityService)
        report_service = Mock(spec=ReportService)

        mock_records = [
            StockDaily(
                stock_code='600000',
                trade_date=date(2024, 1, 2),
                open=10.0,
                high=10.8,
                low=9.9,
                close=10.5,
                volume=1000000,
                data_source='test',
                adjust_type='qfq',
                is_adjusted=True
            )
        ]
        data_source.get_daily = AsyncMock(return_value=mock_records)
        storage.insert = AsyncMock(return_value=1)
        quality_service.batch_validate = AsyncMock(return_value={
            'total': 1, 'passed': 1, 'failed': 0, 'quality_flags': ['good']
        })

        service = StockSyncService(
            data_source=data_source,
            storage=storage,
            quality_service=quality_service,
            report_service=report_service
        )

        result = await service.batch_sync(['600000', '600001'])

        assert result['total'] == 2
        assert result['success_count'] == 2
        assert result['failed_count'] == 0

    @pytest.mark.asyncio
    async def test_sync_with_quality_validation(self):
        """测试同步包含质量校验"""
        data_source = Mock(spec=AkshareClient)
        storage = Mock(spec=ClickHouseRepository)
        quality_service = Mock(spec=QualityService)
        report_service = Mock(spec=ReportService)

        # 模拟一些数据通过校验，一些不通过
        mock_records = [
            StockDaily(
                stock_code='600000',
                trade_date=date(2024, 1, 2),
                open=10.0,
                high=10.8,
                low=9.9,
                close=10.5,
                volume=1000000,
                data_source='test',
                adjust_type='qfq',
                is_adjusted=True
            ),
            StockDaily(
                stock_code='600000',
                trade_date=date(2024, 1, 3),
                open=10.0,
                high=10.8,
                low=9.9,
                close=10.5,
                volume=1000000,
                change_pct=15.0,  # 超限，会被标记为error
                data_source='test',
                adjust_type='qfq',
                is_adjusted=True
            )
        ]
        data_source.get_daily = AsyncMock(return_value=mock_records)
        storage.insert = AsyncMock(return_value=1)
        quality_service.batch_validate = AsyncMock(return_value={
            'total': 2,
            'passed': 1,
            'failed': 1,
            'quality_flags': ['good', 'error']
        })

        service = StockSyncService(
            data_source=data_source,
            storage=storage,
            quality_service=quality_service,
            report_service=report_service
        )

        result = await service.sync_single_stock('600000')

        assert result['total_records'] == 2
        assert result['success_count'] == 1
        assert result['failed_count'] == 1

    @pytest.mark.asyncio
    async def test_sync_status_tracking(self):
        """测试同步状态跟踪"""
        data_source = Mock(spec=AkshareClient)
        storage = Mock(spec=ClickHouseRepository)
        quality_service = Mock(spec=QualityService)
        report_service = Mock(spec=ReportService)

        data_source.get_daily = AsyncMock(return_value=[])
        storage.insert = AsyncMock(return_value=0)

        service = StockSyncService(
            data_source=data_source,
            storage=storage,
            quality_service=quality_service,
            report_service=report_service
        )

        # 标记开始
        service.mark_sync_start('600000')
        status = service.get_sync_status('600000')
        assert status['status'] == 'running'

        # 执行同步
        await service.sync_single_stock('600000')

        # 检查状态已更新
        status = service.get_sync_status('600000')
        assert status['status'] == 'success'

    @pytest.mark.asyncio
    async def test_sync_with_skip_strategy_all_exist(self):
        """测试SKIP策略-所有日期已存在时跳过"""
        data_source = Mock(spec=AkshareClient)
        storage = Mock(spec=ClickHouseRepository)
        quality_service = Mock(spec=QualityService)
        report_service = Mock(spec=ReportService)

        # 模拟已有全部数据 (1/1 到 1/5)
        existing_dates = {date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5)}
        storage.get_existing_dates = AsyncMock(return_value=existing_dates)
        data_source.get_daily = AsyncMock(return_value=[])

        service = StockSyncService(
            data_source=data_source,
            storage=storage,
            quality_service=quality_service,
            report_service=report_service
        )

        result = await service.sync_single_stock(
            '600000',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 5),
            strategy=SyncStrategy.SKIP
        )

        assert result['status'] == 'success'
        assert result['success_count'] == 0
        assert result['skipped_count'] == 5  # 5天全部跳过

    @pytest.mark.asyncio
    async def test_sync_with_skip_strategy_partial_exist(self):
        """测试SKIP策略-部分日期已存在"""
        data_source = Mock(spec=AkshareClient)
        storage = Mock(spec=ClickHouseRepository)
        quality_service = Mock(spec=QualityService)
        report_service = Mock(spec=ReportService)

        # 已有最新日期
        existing_dates = {date(2024, 1, 3), date(2024, 1, 4)}
        storage.get_existing_dates = AsyncMock(return_value=existing_dates)

        mock_records = [
            StockDaily(
                stock_code='600000',
                trade_date=date(2024, 1, 5),
                open=10.0,
                high=10.8,
                low=9.9,
                close=10.5,
                volume=1000000,
                data_source='test',
                adjust_type='qfq',
                is_adjusted=True
            )
        ]
        data_source.get_daily = AsyncMock(return_value=mock_records)
        storage.insert = AsyncMock(return_value=1)
        quality_service.batch_validate = AsyncMock(return_value={
            'total': 1, 'passed': 1, 'failed': 0, 'quality_flags': ['good']
        })

        service = StockSyncService(
            data_source=data_source,
            storage=storage,
            quality_service=quality_service,
            report_service=report_service
        )

        result = await service.sync_single_stock(
            '600000',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 5),
            strategy=SyncStrategy.SKIP
        )

        assert result['status'] == 'success'
        assert result['strategy'] == 'skip'

    @pytest.mark.asyncio
    async def test_sync_with_incremental_strategy(self):
        """测试INCREMENTAL策略-只同步新增日期"""
        data_source = Mock(spec=AkshareClient)
        storage = Mock(spec=ClickHouseRepository)
        quality_service = Mock(spec=QualityService)
        report_service = Mock(spec=ReportService)

        # 已有1月3日
        existing_dates = {date(2024, 1, 3)}
        storage.get_existing_dates = AsyncMock(return_value=existing_dates)

        # API返回了3天数据
        mock_records = [
            StockDaily(
                stock_code='600000',
                trade_date=date(2024, 1, 2),
                open=10.0,
                high=10.8,
                low=9.9,
                close=10.5,
                volume=1000000,
                data_source='test',
                adjust_type='qfq',
                is_adjusted=True
            ),
            StockDaily(
                stock_code='600000',
                trade_date=date(2024, 1, 3),
                open=10.0,
                high=10.8,
                low=9.9,
                close=10.5,
                volume=1000000,
                data_source='test',
                adjust_type='qfq',
                is_adjusted=True
            ),
            StockDaily(
                stock_code='600000',
                trade_date=date(2024, 1, 4),
                open=10.0,
                high=10.8,
                low=9.9,
                close=10.5,
                volume=1000000,
                data_source='test',
                adjust_type='qfq',
                is_adjusted=True
            ),
        ]
        data_source.get_daily = AsyncMock(return_value=mock_records)
        storage.insert = AsyncMock(return_value=2)  # 只插入2条新增
        quality_service.batch_validate = AsyncMock(return_value={
            'total': 2, 'passed': 2, 'failed': 0, 'quality_flags': ['good', 'good']
        })

        service = StockSyncService(
            data_source=data_source,
            storage=storage,
            quality_service=quality_service,
            report_service=report_service
        )

        result = await service.sync_single_stock(
            '600000',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 5),
            strategy=SyncStrategy.INCREMENTAL
        )

        assert result['status'] == 'success'
        assert result['strategy'] == 'incremental'
        assert result['total_records'] == 2  # 过滤掉了已存在的1月3日

    @pytest.mark.asyncio
    async def test_sync_strategy_enum_values(self):
        """测试SyncStrategy枚举值"""
        assert SyncStrategy.SKIP.value == 'skip'
        assert SyncStrategy.OVERWRITE.value == 'overwrite'
        assert SyncStrategy.INCREMENTAL.value == 'incremental'

    @pytest.mark.asyncio
    async def test_sync_with_skip_strategy_no_start_date(self):
        """测试SKIP策略-无开始日期时从最新日期后继续"""
        data_source = Mock(spec=AkshareClient)
        storage = Mock(spec=ClickHouseRepository)
        quality_service = Mock(spec=QualityService)
        report_service = Mock(spec=ReportService)

        # 已有最新日期到1月3日
        existing_dates = {date(2024, 1, 3)}
        storage.get_existing_dates = AsyncMock(return_value=existing_dates)

        # API返回1月4日的新数据
        mock_records = [
            StockDaily(
                stock_code='600000',
                trade_date=date(2024, 1, 4),
                open=10.0,
                high=10.8,
                low=9.9,
                close=10.5,
                volume=1000000,
                data_source='test',
                adjust_type='qfq',
                is_adjusted=True
            )
        ]
        data_source.get_daily = AsyncMock(return_value=mock_records)
        storage.insert = AsyncMock(return_value=1)
        quality_service.batch_validate = AsyncMock(return_value={
            'total': 1, 'passed': 1, 'failed': 0, 'quality_flags': ['good']
        })

        service = StockSyncService(
            data_source=data_source,
            storage=storage,
            quality_service=quality_service,
            report_service=report_service
        )

        # 不指定start_date，end_date=1月5日
        result = await service.sync_single_stock(
            '600000',
            end_date=date(2024, 1, 5),
            strategy=SyncStrategy.SKIP
        )

        assert result['status'] == 'success'
        # 验证从1月4日开始获取（最新已存在是1月3日）
        call_args = data_source.get_daily.call_args
        assert call_args[1]['start_date'] == date(2024, 1, 4)

    @pytest.mark.asyncio
    async def test_sync_stock_info(self):
        """测试同步股票基本信息"""
        from models.stock_info import StockInfo

        data_source = Mock(spec=AkshareClient)
        storage = Mock(spec=ClickHouseRepository)
        quality_service = Mock(spec=QualityService)
        report_service = Mock(spec=ReportService)

        storage.insert = AsyncMock(return_value=2)

        service = StockSyncService(
            data_source=data_source,
            storage=storage,
            quality_service=quality_service,
            report_service=report_service
        )

        stocks = [
            StockInfo(stock_code='600000', stock_name='浦发银行', market='SSE'),
            StockInfo(stock_code='600001', stock_name='邯郸钢铁', market='SSE'),
        ]

        result = await service.sync_stock_info(stocks)

        assert result['status'] == 'success'
        assert result['success_count'] == 2

    @pytest.mark.asyncio
    async def test_sync_stock_info_empty(self):
        """测试同步空股票列表"""
        data_source = Mock(spec=AkshareClient)
        storage = Mock(spec=ClickHouseRepository)
        quality_service = Mock(spec=QualityService)
        report_service = Mock(spec=ReportService)

        service = StockSyncService(
            data_source=data_source,
            storage=storage,
            quality_service=quality_service,
            report_service=report_service
        )

        result = await service.sync_stock_info([])

        assert result['status'] == 'success'
        assert result['total'] == 0
