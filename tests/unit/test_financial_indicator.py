# tests/unit/test_financial_indicator.py
"""财务指标获取测试"""

import pytest
from unittest.mock import Mock, AsyncMock
import sys
sys.path.insert(0, '/root/ai/claudecode/first/stock-scraper')

from data_source.akshare_client import AkshareClient
from data_source.base import BaseDataSource


class TestFinancialIndicator:
    """财务指标测试"""

    @pytest.fixture
    def data_source(self):
        """创建数据源实例"""
        return AkshareClient()

    def test_get_financial_indicator_returns_dict(self, data_source):
        """测试获取财务指标返回字典"""
        result = data_source.get_financial_indicator('600000')
        assert isinstance(result, dict), "返回值应该是字典"

    def test_get_financial_indicator_contains_required_fields(self, data_source):
        """测试返回包含必要字段"""
        result = data_source.get_financial_indicator('600000')
        required_fields = ['pe_ratio', 'pb_ratio', 'total_market_cap', 'float_market_cap']
        for field in required_fields:
            assert field in result, f"应包含字段: {field}"

    def test_get_financial_indicator_pe_ratio_is_numeric(self, data_source):
        """测试市盈率是数值类型"""
        result = data_source.get_financial_indicator('600000')
        pe = result.get('pe_ratio')
        if pe is not None:
            assert isinstance(pe, (int, float)), "市盈率应该是数值类型"

    def test_get_financial_indicator_pb_ratio_is_numeric(self, data_source):
        """测试市净率是数值类型"""
        result = data_source.get_financial_indicator('600000')
        pb = result.get('pb_ratio')
        if pb is not None:
            assert isinstance(pb, (int, float)), "市净率应该是数值类型"

    def test_get_financial_indicator_market_cap_is_numeric(self, data_source):
        """测试市值是数值类型"""
        result = data_source.get_financial_indicator('600000')
        mcap = result.get('total_market_cap')
        if mcap is not None:
            assert isinstance(mcap, (int, float)), "总市值应该是数值类型"

    @pytest.mark.asyncio
    async def test_get_financial_indicator_async(self, data_source):
        """测试异步获取财务指标"""
        result = await data_source.get_financial_indicator_async('600000')
        assert isinstance(result, dict), "返回值应该是字典"
        assert 'pe_ratio' in result, "应包含市盈率字段"


class TestFinancialIndicatorIntegration:
    """财务指标集成测试（需要实际API）"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要实际网络请求，仅手动验证")
    async def test_live_api_call(self):
        """测试实际API调用"""
        ds = AkshareClient()
        result = await ds.get_financial_indicator_async('600000')
        print(f"Result: {result}")
        # 市盈率应该大于0
        if result.get('pe_ratio'):
            assert result['pe_ratio'] > 0
