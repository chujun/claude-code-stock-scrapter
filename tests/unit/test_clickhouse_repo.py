# tests/unit/test_clickhouse_repo.py
"""ClickHouseRepository单元测试"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, AsyncMock, patch
import sys
sys.path.insert(0, '/root/ai/claudecode/first/stock-scraper')

from storage.clickhouse_repo import ClickHouseRepository, _validate_table_name
from storage.base import BaseRepository


class TestClickHouseRepository:
    """ClickHouseRepository测试"""

    def test_initialization(self):
        """测试初始化"""
        repo = ClickHouseRepository()
        # 不直接访问 client 属性，避免创建真实连接
        assert repo._executor is not None
        assert repo.host == "localhost"
        assert repo.database == "stock_scraper"

    def test_inherits_from_base_repository(self):
        """测试继承BaseRepository"""
        assert issubclass(ClickHouseRepository, BaseRepository)

    def test_insert_accepts_records_parameter(self):
        """测试insert方法签名"""
        import inspect
        sig = inspect.signature(ClickHouseRepository.insert)
        params = list(sig.parameters.keys())
        assert 'records' in params

    def test_upsert_accepts_unique_keys_parameter(self):
        """测试upsert方法签名"""
        import inspect
        sig = inspect.signature(ClickHouseRepository.upsert)
        params = list(sig.parameters.keys())
        assert 'unique_keys' in params

    @pytest.mark.asyncio
    async def test_insert_single_record(self):
        """测试插入单条记录"""
        repo = ClickHouseRepository()
        mock_client = Mock()
        # DESC returns list of tuples
        mock_client.execute.return_value = [('stock_code', 'String'), ('stock_name', 'String')]
        repo._client = mock_client
        result = await repo.insert('stock_info', [{'stock_code': '600000', 'stock_name': '测试'}])
        assert result == 1

    @pytest.mark.asyncio
    async def test_insert_multiple_records(self):
        """测试批量插入多条记录"""
        repo = ClickHouseRepository()
        records = [
            {'stock_code': '600000', 'stock_name': '测试1'},
            {'stock_code': '600001', 'stock_name': '测试2'}
        ]
        mock_client = Mock()
        mock_client.execute.return_value = [('stock_code', 'String'), ('stock_name', 'String')]
        repo._client = mock_client
        result = await repo.insert('stock_info', records)
        assert result == 2

    @pytest.mark.asyncio
    async def test_query_returns_list(self):
        """测试查询返回列表"""
        repo = ClickHouseRepository()
        mock_client = Mock()
        mock_client.execute.return_value = (['stock_code', 'stock_name'], [('600000', '测试')])
        repo._client = mock_client
        result = await repo.query("SELECT * FROM stock_info WHERE stock_code = '600000'")
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_execute_returns_affected_rows(self):
        """测试execute返回影响行数"""
        repo = ClickHouseRepository()
        mock_client = Mock()
        mock_client.execute.return_value = (1,)
        repo._client = mock_client
        result = await repo.execute("DROP TABLE IF EXISTS test_table")
        assert result == 1

    def test_get_table_columns(self):
        """测试获取表字段"""
        repo = ClickHouseRepository()
        mock_client = Mock()
        mock_client.execute.return_value = [('stock_code', 'String'), ('stock_name', 'String')]
        repo._client = mock_client
        columns = repo.get_table_columns('stock_info')
        assert isinstance(columns, list)
        assert 'stock_code' in columns
        assert 'stock_name' in columns

    @pytest.mark.asyncio
    async def test_insert_invalid_table_name_raises_error(self):
        """测试插入无效表名抛出错误"""
        repo = ClickHouseRepository()
        with pytest.raises(ValueError) as exc_info:
            await repo.insert('invalid_table_name', [{'key': 'value'}])
        assert 'not in allowed tables list' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_insert_sql_injection_attempt_blocked(self):
        """测试SQL注入尝试被阻止"""
        repo = ClickHouseRepository()
        with pytest.raises(ValueError):
            # 尝试注入SQL
            await repo.insert("stock_info; DROP TABLE stock_info--", [{}])

    def test_validate_table_name_valid(self):
        """测试有效表名通过验证"""
        for table in ['stock_info', 'stock_daily', 'sync_status']:
            _validate_table_name(table)  # 不应抛出异常

    def test_validate_table_name_invalid(self):
        """测试无效表名抛出错误"""
        invalid_names = ['', '123table', 'table-name', 'table.name', 'table name']
        for name in invalid_names:
            with pytest.raises(ValueError):
                _validate_table_name(name)

    def test_context_manager(self):
        """测试上下文管理器"""
        import asyncio
        repo = ClickHouseRepository()
        # 验证 __aenter__ 和 __aexit__ 存在
        assert hasattr(repo, '__aenter__')
        assert hasattr(repo, '__aexit__')
