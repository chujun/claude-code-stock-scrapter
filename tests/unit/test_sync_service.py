# tests/unit/test_sync_service.py
"""StockSyncService单元测试"""

import pytest
from datetime import date
from unittest.mock import Mock, AsyncMock
import sys
sys.path.insert(0, '/root/ai/claudecode/first/stock-scraper')

from services.sync_service import StockSyncService
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
