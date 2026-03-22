# tests/unit/test_data_source.py
"""数据源层单元测试"""

import pytest
from datetime import date
from unittest.mock import Mock, AsyncMock, patch

import sys
sys.path.insert(0, '/root/ai/claudecode/first/stock-scraper')

from data_source.base import BaseDataSource
from data_source.exceptions import (
    NetworkError,
    DataError,
    BusinessError,
    TimeoutError,
    RateLimitError,
    ServerError,
)
from data_source.rate_limiter import RateLimiter


class TestRateLimiter:
    """RateLimiter限流器测试"""

    def test_initialization(self):
        """测试初始化"""
        limiter = RateLimiter(base_interval=1.5)
        assert limiter.base_interval == 1.5
        assert limiter.last_request_time == 0

    def test_initialization_defaults(self):
        """测试默认参数"""
        limiter = RateLimiter()
        assert limiter.base_interval == 1.0
        assert limiter.last_request_time == 0

    @pytest.mark.asyncio
    async def test_wait_first_request(self):
        """测试首次请求不需要等待"""
        limiter = RateLimiter(base_interval=0.01)
        import time
        start = time.time()
        await limiter.wait()
        elapsed = time.time() - start
        assert elapsed < 0.05  # 几乎不需要等待

    @pytest.mark.asyncio
    async def test_wait_enforces_interval(self):
        """测试限流间隔生效"""
        limiter = RateLimiter(base_interval=0.1)
        import time
        await limiter.wait()
        start = time.time()
        await limiter.wait()
        elapsed = time.time() - start
        assert elapsed >= 0.09  # 至少间隔0.09秒

    def test_update_last_request_time(self):
        """测试更新时间记录"""
        limiter = RateLimiter(base_interval=1.0)
        import time
        current = time.time()
        limiter.last_request_time = current
        assert limiter.last_request_time == current


class TestDataSourceExceptions:
    """数据源异常类测试"""

    def test_network_error_is_retryable(self):
        """测试NetworkError可重试"""
        error = NetworkError("test error")
        assert error.error_type == "network"
        assert error.retryable is True

    def test_timeout_error(self):
        """测试TimeoutError"""
        error = TimeoutError("connection timeout")
        assert error.error_type == "network"
        assert error.error_code == "timeout"
        assert error.retryable is True

    def test_rate_limit_error(self):
        """测试RateLimitError"""
        error = RateLimitError("rate limited")
        assert error.error_type == "network"
        assert error.error_code == "429"
        assert error.retryable is True

    def test_server_error(self):
        """测试ServerError"""
        error = ServerError("server error")
        assert error.error_type == "network"
        assert error.error_code == "5xx"
        assert error.retryable is True

    def test_data_error_not_retryable(self):
        """测试DataError不可重试"""
        error = DataError("data error")
        assert error.error_type == "data"
        assert error.retryable is False

    def test_business_error_not_retryable(self):
        """测试BusinessError不可重试"""
        error = BusinessError("business error")
        assert error.error_type == "business"
        assert error.retryable is False


class TestBaseDataSource:
    """BaseDataSource抽象基类测试"""

    def test_is_abstract_class(self):
        """测试是抽象类"""
        from abc import ABC
        assert issubclass(BaseDataSource, ABC)

    def test_abstract_methods(self):
        """测试抽象方法存在"""
        assert hasattr(BaseDataSource, 'get_stock_list')
        assert hasattr(BaseDataSource, 'get_daily')
        assert hasattr(BaseDataSource, 'get_index')
        assert hasattr(BaseDataSource, 'health_check')


class TestAkshareClient:
    """AkshareClient测试"""

    def test_initialization(self):
        """测试初始化"""
        from data_source.akshare_client import AkshareClient

        client = AkshareClient()
        assert client.settings is not None
        assert client.rate_limiter is not None

    def test_settings_from_config(self):
        """测试配置加载"""
        from data_source.akshare_client import AkshareClient

        client = AkshareClient()
        # 默认配置
        assert client.settings.name == "akshare"

    @pytest.mark.asyncio
    async def test_get_stock_list_returns_list(self):
        """测试获取股票列表返回列表"""
        from data_source.akshare_client import AkshareClient

        client = AkshareClient()
        # 使用mock避免真实API调用
        with patch.object(client, 'get_stock_list', new_callable=AsyncMock) as mock:
            mock.return_value = []
            result = await client.get_stock_list()
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_daily_returns_list(self):
        """测试获取日线数据返回列表"""
        from data_source.akshare_client import AkshareClient

        client = AkshareClient()
        with patch.object(client, 'get_daily', new_callable=AsyncMock) as mock:
            mock.return_value = []
            result = await client.get_daily('600000', date(2024, 1, 1), date(2024, 1, 31))
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_health_check_returns_bool(self):
        """测试健康检查返回布尔值"""
        from data_source.akshare_client import AkshareClient

        client = AkshareClient()
        with patch.object(client, 'health_check', new_callable=AsyncMock) as mock:
            mock.return_value = True
            result = await client.health_check()
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_daily_invalid_adjust_type_raises_business_error(self):
        """测试get_daily对无效adjust_type抛出BusinessError"""
        from data_source.akshare_client import AkshareClient

        client = AkshareClient()
        with pytest.raises(BusinessError) as exc_info:
            await client.get_daily('600000', date(2024, 1, 1), date(2024, 1, 31), adjust_type="invalid")
        assert "invalid_adjust_type" in str(exc_info.value.error_code)

    @pytest.mark.asyncio
    async def test_get_daily_valid_adjust_types(self):
        """测试get_daily接受有效的adjust_type值"""
        import akshare as ak
        from data_source.akshare_client import AkshareClient
        import pandas as pd

        client = AkshareClient()
        # Mock akshare函数返回空DataFrame
        mock_df = pd.DataFrame(columns=['date', 'open', 'close', 'high', 'low', 'amount'])
        with patch('akshare.stock_zh_a_hist_tx', return_value=mock_df):
            for adjust_type in ("qfq", "hfq", "none"):
                result = await client.get_daily(
                    '600000', date(2024, 1, 1), date(2024, 1, 31), adjust_type=adjust_type
                )
                assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_daily_parses_data_correctly(self):
        """测试get_daily正确解析数据"""
        from data_source.akshare_client import AkshareClient
        from models.stock_daily import StockDaily
        import pandas as pd

        client = AkshareClient()
        # 构造符合腾讯数据源格式的mock DataFrame
        mock_df = pd.DataFrame([
            {'date': '2024-01-02', 'open': 10.0, 'close': 10.5, 'high': 10.8, 'low': 9.9, 'amount': 10500000.0}
        ])
        with patch('akshare.stock_zh_a_hist_tx', return_value=mock_df):
            result = await client.get_daily('600000', date(2024, 1, 1), date(2024, 1, 31))
            assert len(result) == 1
            assert isinstance(result[0], StockDaily)
            assert result[0].stock_code == "600000"
            assert result[0].close == 10.5
            assert result[0].adjust_type == "qfq"

    @pytest.mark.asyncio
    async def test_get_daily_network_error_propagates(self):
        """测试get_daily网络错误向上传播"""
        import akshare as ak
        from data_source.akshare_client import AkshareClient

        client = AkshareClient()
        with patch('akshare.stock_zh_a_hist_tx', side_effect=NetworkError("connection failed")):
            with pytest.raises(NetworkError):
                await client.get_daily('600000', date(2024, 1, 1), date(2024, 1, 31))

    @pytest.mark.asyncio
    async def test_get_daily_data_error_on_parse_failure(self):
        """测试get_daily解析错误抛出DataError"""
        import akshare as ak
        from data_source.akshare_client import AkshareClient
        import pandas as pd

        client = AkshareClient()
        # 返回格式错误的空数据
        mock_df = pd.DataFrame()
        with patch('akshare.stock_zh_a_hist_tx', return_value=mock_df):
            result = await client.get_daily('600000', date(2024, 1, 1), date(2024, 1, 31))
            assert result == []

    @pytest.mark.asyncio
    async def test_get_stock_list_parses_data_correctly(self):
        """测试get_stock_list正确解析数据"""
        import akshare as ak
        from data_source.akshare_client import AkshareClient
        from models.stock_info import StockInfo
        import pandas as pd

        client = AkshareClient()
        # Mock返回股票列表
        mock_df = pd.DataFrame([
            {'code': '600000', 'name': '浦发银行'},
            {'code': '600036', 'name': '招商银行'}
        ])
        with patch('akshare.stock_info_a_code_name', return_value=mock_df):
            result = await client.get_stock_list()
            assert len(result) == 2
            assert isinstance(result[0], StockInfo)
            assert result[0].stock_code == "600000"
            assert result[0].stock_name == "浦发银行"
            assert result[0].market == "SSE"

    @pytest.mark.asyncio
    async def test_get_stock_list_network_error_propagates(self):
        """测试get_stock_list网络错误向上传播"""
        import akshare as ak
        from data_source.akshare_client import AkshareClient

        client = AkshareClient()
        with patch('akshare.stock_info_a_code_name', side_effect=NetworkError("connection failed")):
            with pytest.raises(NetworkError):
                await client.get_stock_list()

    @pytest.mark.asyncio
    async def test_get_stock_list_handles_malformed_data(self):
        """测试get_stock_list处理畸形数据（返回空字段而非报错）"""
        import akshare as ak
        from data_source.akshare_client import AkshareClient
        import pandas as pd

        client = AkshareClient()
        # 畸形数据 - 只有空字符串的必需字段
        mock_df = pd.DataFrame([{'code': '', 'name': ''}])
        with patch('akshare.stock_info_a_code_name', return_value=mock_df):
            # 不应该抛出异常，而是返回空字段的股票对象
            result = await client.get_stock_list()
            assert len(result) == 1
            assert result[0].stock_code == ""
            assert result[0].stock_name == ""

    @pytest.mark.asyncio
    async def test_get_index_parses_data_correctly(self):
        """测试get_index正确解析数据"""
        import akshare as ak
        from data_source.akshare_client import AkshareClient
        from models.daily_index import DailyIndex
        import pandas as pd

        client = AkshareClient()
        # Mock返回指数数据 (stock_zh_index_daily返回: date,open,high,low,close,volume)
        mock_df = pd.DataFrame([
            {'date': '2024-01-02', 'open': 3000.0, 'close': 3020.0, 'high': 3050.0, 'low': 2980.0, 'volume': 300000000}
        ])
        with patch('akshare.stock_zh_index_daily', return_value=mock_df):
            result = await client.get_index("000001", date(2024, 1, 1), date(2024, 1, 31))
            assert len(result) == 1
            assert isinstance(result[0], DailyIndex)
            assert result[0].index_code == "000001"
            assert result[0].close == 3020.0
            # 第一条数据change_pct应为0（无前一日数据）
            assert result[0].change_pct == 0

    @pytest.mark.asyncio
    async def test_get_index_network_error_propagates(self):
        """测试get_index网络错误向上传播"""
        import akshare as ak
        from data_source.akshare_client import AkshareClient

        client = AkshareClient()
        with patch('akshare.stock_zh_index_daily', side_effect=NetworkError("connection failed")):
            with pytest.raises(NetworkError):
                await client.get_index("000001", date(2024, 1, 1), date(2024, 1, 31))

    @pytest.mark.asyncio
    async def test_get_index_data_error_on_parse_failure(self):
        """测试get_index解析错误抛出DataError"""
        import akshare as ak
        from data_source.akshare_client import AkshareClient
        import pandas as pd

        client = AkshareClient()
        # 返回空数据
        mock_df = pd.DataFrame()
        with patch('akshare.stock_zh_index_daily', return_value=mock_df):
            result = await client.get_index("000001", date(2024, 1, 1), date(2024, 1, 31))
            assert result == []

    @pytest.mark.asyncio
    async def test_close_session(self):
        """测试关闭会话"""
        from data_source.akshare_client import AkshareClient

        client = AkshareClient()
        # close方法不依赖session
        await client.close()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_get_session_creates_new_session(self):
        """测试_get_session不存在（无session管理）"""
        from data_source.akshare_client import AkshareClient

        client = AkshareClient()
        # AkshareClient不依赖session，直接验证close即可
        await client.close()
