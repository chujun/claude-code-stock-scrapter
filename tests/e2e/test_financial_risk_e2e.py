"""财务风险模块端到端测试

验证:
1. 模块可以正确导入
2. StockFinancialRisk 数据模型可以正常工作
3. THSClient 可以创建实例
4. FinancialRiskService 可以创建实例
"""

import asyncio
import sys
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestFinancialRiskModuleImports:
    """测试模块导入"""

    def test_import_stock_financial_risk_model(self):
        """验证可以正确导入 StockFinancialRisk 模型"""
        from models.stock_financial_risk import StockFinancialRisk
        assert StockFinancialRisk is not None

    def test_import_financial_risk_service(self):
        """验证可以正确导入 FinancialRiskService"""
        from services.financial_risk_service import FinancialRiskService
        assert FinancialRiskService is not None

    def test_import_ths_client(self):
        """验证可以正确导入 THSClient"""
        from data_source.ths_client import THSClient
        assert THSClient is not None

    def test_import_ths_risk_page_source(self):
        """验证可以正确导入 THSRiskPageSource"""
        from data_source.ths_client import THSRiskPageSource
        assert THSRiskPageSource is not None


class TestStockFinancialRiskModel:
    """测试 StockFinancialRisk 模型"""

    def test_create_valid_model(self):
        """测试创建有效的模型实例"""
        from models.stock_financial_risk import StockFinancialRisk

        risk = StockFinancialRisk(
            stock_code="600000",
            trade_date=date(2024, 1, 2),
            total_risk=10,
            no_risk=3,
            low_risk=4,
            medium_risk=2,
            high_risk=1
        )

        assert risk.stock_code == "600000"
        assert risk.trade_date == date(2024, 1, 2)
        assert risk.total_risk == 10
        assert risk.no_risk == 3
        assert risk.low_risk == 4
        assert risk.medium_risk == 2
        assert risk.high_risk == 1
        assert risk.data_source == "ths"

    def test_model_to_dict(self):
        """测试模型转换为字典"""
        from models.stock_financial_risk import StockFinancialRisk

        risk = StockFinancialRisk(
            stock_code="600000",
            trade_date=date(2024, 1, 2),
            total_risk=10,
            no_risk=3,
            low_risk=4,
            medium_risk=2,
            high_risk=1
        )

        data = risk.model_dump()
        assert isinstance(data, dict)
        assert data["stock_code"] == "600000"
        assert data["trade_date"] == date(2024, 1, 2)
        assert data["total_risk"] == 10

    def test_model_validation_sum_mismatch(self):
        """测试风险总数不匹配时验证失败"""
        from models.stock_financial_risk import StockFinancialRisk
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            StockFinancialRisk(
                stock_code="600000",
                trade_date=date(2024, 1, 2),
                total_risk=10,
                no_risk=3,
                low_risk=4,
                medium_risk=2,
                high_risk=0  # 总和是9，不是10
            )
        assert "Risk sum" in str(exc_info.value)

    def test_model_validation_negative_value(self):
        """测试负数值时验证失败"""
        from models.stock_financial_risk import StockFinancialRisk
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            StockFinancialRisk(
                stock_code="600000",
                trade_date=date(2024, 1, 2),
                total_risk=-1,
                no_risk=0,
                low_risk=0,
                medium_risk=0,
                high_risk=0
            )

    def test_model_with_zero_values(self):
        """测试所有值为0的情况"""
        from models.stock_financial_risk import StockFinancialRisk

        risk = StockFinancialRisk(
            stock_code="600000",
            trade_date=date(2024, 1, 2),
            total_risk=0,
            no_risk=0,
            low_risk=0,
            medium_risk=0,
            high_risk=0
        )
        assert risk.total_risk == 0


class TestTHSClient:
    """测试 THSClient - 使用 mock 因为 THSClient 是抽象类"""

    def test_create_ths_client_instance(self):
        """测试 THSClient 实例属性"""
        from data_source.ths_client import THSClient
        from data_source.base import BaseDataSource
        from unittest.mock import MagicMock

        # THSClient 是抽象类，需要通过 mock 来测试其属性
        # 创建一个非抽象的代理类来测试初始化逻辑
        class ConcreteTHSClient(THSClient):
            async def get_stock_list(self):
                return []
            async def get_daily(self, stock_code, start_date, end_date, adjust_type="qfq"):
                return []
            async def get_index(self, index_code, start_date, end_date):
                return []
            async def health_check(self):
                return True
            async def get_split(self, stock_code, start_date=None, end_date=None):
                return []
            def get_financial_indicator(self, stock_code):
                return {}
            async def get_financial_indicator_async(self, stock_code):
                return {}
            async def get_trading_dates(self, start_date, end_date):
                return set()

        client = ConcreteTHSClient(
            headless=True,
            timeout=30000,
            slow_mo=100,
            browser_type="chromium",
            rate_limit_interval=2.0
        )

        assert client is not None
        assert client.headless is True
        assert client.timeout == 30000
        assert client.slow_mo == 100
        assert client.browser_type == "chromium"
        assert client._browser is None  # 浏览器尚未启动

    def test_ths_client_default_values(self):
        """测试 THSClient 默认值"""
        from data_source.ths_client import THSClient

        class ConcreteTHSClient(THSClient):
            async def get_stock_list(self):
                return []
            async def get_daily(self, stock_code, start_date, end_date, adjust_type="qfq"):
                return []
            async def get_index(self, index_code, start_date, end_date):
                return []
            async def health_check(self):
                return True
            async def get_split(self, stock_code, start_date=None, end_date=None):
                return []
            def get_financial_indicator(self, stock_code):
                return {}
            async def get_financial_indicator_async(self, stock_code):
                return {}
            async def get_trading_dates(self, start_date, end_date):
                return set()

        client = ConcreteTHSClient()

        assert client.headless is True
        assert client.timeout == 30000
        assert client.slow_mo == 100
        assert client.browser_type == "chromium"
        assert client._browser is None

    @pytest.mark.asyncio
    async def test_ths_client_close_without_browser(self):
        """测试关闭未启动浏览器的客户端"""
        from data_source.ths_client import THSClient

        class ConcreteTHSClient(THSClient):
            async def get_stock_list(self):
                return []
            async def get_daily(self, stock_code, start_date, end_date, adjust_type="qfq"):
                return []
            async def get_index(self, index_code, start_date, end_date):
                return []
            async def health_check(self):
                return True
            async def get_split(self, stock_code, start_date=None, end_date=None):
                return []
            def get_financial_indicator(self, stock_code):
                return {}
            async def get_financial_indicator_async(self, stock_code):
                return {}
            async def get_trading_dates(self, start_date, end_date):
                return set()

        client = ConcreteTHSClient()
        # 关闭未启动的浏览器不应该报错
        await client.close()
        assert client._browser is None


class TestFinancialRiskService:
    """测试 FinancialRiskService"""

    def test_create_financial_risk_service(self):
        """测试创建 FinancialRiskService 实例"""
        from services.financial_risk_service import FinancialRiskService

        mock_repo = MagicMock()
        mock_client = MagicMock()

        service = FinancialRiskService(
            repo=mock_repo,
            playwright_client=mock_client
        )

        assert service is not None
        assert service.repo is mock_repo
        assert service.client is mock_client

    @pytest.mark.asyncio
    async def test_sync_stock_with_mock(self):
        """测试使用模拟客户端同步股票"""
        from services.financial_risk_service import FinancialRiskService
        from models.stock_financial_risk import StockFinancialRisk

        mock_repo = AsyncMock()
        mock_repo.upsert = AsyncMock(return_value=1)

        mock_client = AsyncMock()
        mock_client.get_financial_risk = AsyncMock(return_value=[
            StockFinancialRisk(
                stock_code="600000",
                trade_date=date(2024, 1, 2),
                total_risk=10,
                no_risk=3,
                low_risk=4,
                medium_risk=2,
                high_risk=1
            )
        ])

        service = FinancialRiskService(
            repo=mock_repo,
            playwright_client=mock_client
        )

        result = await service.sync_stock("600000")

        assert result["stock_code"] == "600000"
        assert result["status"] == "success"
        assert result["records_synced"] == 1
        mock_client.get_financial_risk.assert_called_once_with("600000")

    @pytest.mark.asyncio
    async def test_close_service(self):
        """测试关闭服务"""
        from services.financial_risk_service import FinancialRiskService

        mock_repo = MagicMock()
        mock_client = AsyncMock()

        service = FinancialRiskService(
            repo=mock_repo,
            playwright_client=mock_client
        )

        await service.close()
        mock_client.close.assert_called_once()


class TestIntegration:
    """集成测试"""

    def test_full_module_import_chain(self):
        """测试完整模块导入链"""
        from models.stock_financial_risk import StockFinancialRisk
        from services.financial_risk_service import FinancialRiskService
        from data_source.ths_client import THSClient, THSRiskPageSource

        # 验证所有类都可以实例化
        risk = StockFinancialRisk(
            stock_code="000001",
            trade_date=date(2024, 1, 1),
            total_risk=5,
            no_risk=1,
            low_risk=2,
            medium_risk=1,
            high_risk=1
        )
        assert risk.stock_code == "000001"

        # THSClient 是抽象类，验证 THSRiskPageSource 常量
        assert THSRiskPageSource.RISK_URL_TEMPLATE is not None
        assert "stockpage.10jqka.com.cn" in THSRiskPageSource.RISK_URL_TEMPLATE

    def test_ths_risk_page_source_constants(self):
        """测试 THSRiskPageSource 常量定义"""
        from data_source.ths_client import THSRiskPageSource

        # 验证 URL 模板
        assert "stockpage.10jqka.com.cn" in THSRiskPageSource.RISK_URL_TEMPLATE
        assert "{stock_code}" in THSRiskPageSource.RISK_URL_TEMPLATE

        # 验证选择器常量
        assert THSRiskPageSource.TOTAL_RISK_SELECTOR is not None
        assert THSRiskPageSource.NO_RISK_SELECTOR is not None
        assert THSRiskPageSource.LOW_RISK_SELECTOR is not None
        assert THSRiskPageSource.MEDIUM_RISK_SELECTOR is not None
        assert THSRiskPageSource.HIGH_RISK_SELECTOR is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])