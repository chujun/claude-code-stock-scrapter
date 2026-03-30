# tests/unit/test_financial_risk_service.py
"""财务风险同步服务单元测试"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from models.stock_financial_risk import StockFinancialRisk
from services.financial_risk_service import FinancialRiskService
from storage.clickhouse_repo import ClickHouseRepository


class TestStockFinancialRiskModel:
    """StockFinancialRisk模型测试"""

    def test_create_financial_risk_record(self):
        """测试创建财务风险记录"""
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

    def test_financial_risk_to_dict(self):
        """测试转换为字典"""
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
        assert data["stock_code"] == "600000"
        assert data["trade_date"] == date(2024, 1, 2)
        assert data["total_risk"] == 10
        assert data["no_risk"] == 3
        assert data["low_risk"] == 4
        assert data["medium_risk"] == 2
        assert data["high_risk"] == 1

    def test_financial_risk_validation(self):
        """测试数据验证"""
        # 正常情况
        risk = StockFinancialRisk(
            stock_code="600000",
            trade_date=date(2024, 1, 2),
            total_risk=10,
            no_risk=3,
            low_risk=4,
            medium_risk=2,
            high_risk=1
        )
        assert risk.total_risk == risk.no_risk + risk.low_risk + risk.medium_risk + risk.high_risk

    def test_financial_risk_sum_mismatch(self):
        """测试风险总数不一致时抛出异常"""
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

    def test_financial_risk_negative_count(self):
        """测试负数风险值时抛出异常"""
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

    def test_financial_risk_zero_values(self):
        """测试所有值为0的情况"""
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


class TestFinancialRiskService:
    """财务风险服务测试"""

    @pytest.fixture
    def mock_repo(self):
        """模拟存储库"""
        repo = AsyncMock(spec=ClickHouseRepository)
        repo.insert = AsyncMock(return_value=1)
        repo.upsert = AsyncMock(return_value=1)
        return repo

    @pytest.fixture
    def mock_playwright_client(self):
        """模拟Playwright爬虫客户端"""
        client = AsyncMock()
        client.get_financial_risk = AsyncMock(return_value=[
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
        return client

    @pytest.mark.asyncio
    async def test_sync_single_stock(self, mock_repo, mock_playwright_client):
        """测试单只股票同步"""
        service = FinancialRiskService(
            repo=mock_repo,
            playwright_client=mock_playwright_client
        )

        result = await service.sync_stock("600000")

        assert result["stock_code"] == "600000"
        assert result["records_synced"] == 1
        mock_playwright_client.get_financial_risk.assert_called_once_with("600000")
        mock_repo.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_with_empty_data(self, mock_repo, mock_playwright_client):
        """测试空数据情况"""
        mock_playwright_client.get_financial_risk = AsyncMock(return_value=[])

        service = FinancialRiskService(
            repo=mock_repo,
            playwright_client=mock_playwright_client
        )

        result = await service.sync_stock("600000")

        assert result["stock_code"] == "600000"
        assert result["records_synced"] == 0
        mock_repo.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_multiple_stocks(self, mock_repo, mock_playwright_client):
        """测试批量股票同步"""
        mock_playwright_client.get_financial_risk = AsyncMock(side_effect=[
            [
                StockFinancialRisk(
                    stock_code="600000",
                    trade_date=date(2024, 1, 2),
                    total_risk=10,
                    no_risk=3,
                    low_risk=4,
                    medium_risk=2,
                    high_risk=1
                )
            ],
            [
                StockFinancialRisk(
                    stock_code="000001",
                    trade_date=date(2024, 1, 2),
                    total_risk=8,
                    no_risk=2,
                    low_risk=3,
                    medium_risk=2,
                    high_risk=1
                )
            ]
        ])

        service = FinancialRiskService(
            repo=mock_repo,
            playwright_client=mock_playwright_client
        )

        results = await service.sync_stocks(["600000", "000001"])

        assert len(results) == 2
        assert results[0]["records_synced"] == 1
        assert results[1]["records_synced"] == 1

    @pytest.mark.asyncio
    async def test_sync_error_handling(self, mock_repo, mock_playwright_client):
        """测试错误处理"""
        from data_source.exceptions import NetworkError

        mock_playwright_client.get_financial_risk = AsyncMock(
            side_effect=NetworkError("Network failed")
        )

        service = FinancialRiskService(
            repo=mock_repo,
            playwright_client=mock_playwright_client
        )

        result = await service.sync_stock("600000")

        assert result["stock_code"] == "600000"
        assert result["status"] == "failed"
        assert "Network failed" in result.get("error_message", "")

    @pytest.mark.asyncio
    async def test_close_client(self, mock_repo, mock_playwright_client):
        """测试关闭客户端"""
        service = FinancialRiskService(
            repo=mock_repo,
            playwright_client=mock_playwright_client
        )

        await service.close()

        mock_playwright_client.close.assert_called_once()
