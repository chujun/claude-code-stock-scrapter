# tests/unit/test_storage.py
"""存储层单元测试"""

import pytest
from abc import ABC

import sys
sys.path.insert(0, '/root/ai/claudecode/first/stock-scraper')

from storage.base import BaseRepository


class TestBaseRepository:
    """BaseRepository抽象基类测试"""

    def test_is_abstract_class(self):
        """测试是抽象类"""
        assert issubclass(BaseRepository, ABC)

    def test_abstract_methods_exist(self):
        """测试抽象方法存在"""
        methods = ['insert', 'upsert', 'query', 'execute']
        for m in methods:
            assert hasattr(BaseRepository, m), f'{m} 方法缺失'

    def test_insert_is_abstract(self):
        """测试 insert 是抽象方法"""
        from abc import abstractmethod
        # 获取 insert 方法的属性
        insert_method = getattr(BaseRepository, 'insert')
        # 抽象方法会被标记为 abstractmethod
        assert getattr(insert_method, '__isabstractmethod__', False) is True

    def test_upsert_is_abstract(self):
        """测试 upsert 是抽象方法"""
        upsert_method = getattr(BaseRepository, 'upsert')
        assert getattr(upsert_method, '__isabstractmethod__', False) is True

    def test_query_is_abstract(self):
        """测试 query 是抽象方法"""
        query_method = getattr(BaseRepository, 'query')
        assert getattr(query_method, '__isabstractmethod__', False) is True

    def test_execute_is_abstract(self):
        """测试 execute 是抽象方法"""
        execute_method = getattr(BaseRepository, 'execute')
        assert getattr(execute_method, '__isabstractmethod__', False) is True

    def test_insert_accepts_list_of_records(self):
        """测试 insert 方法签名接受 records 参数"""
        import inspect
        sig = inspect.signature(BaseRepository.insert)
        params = list(sig.parameters.keys())
        assert 'records' in params

    def test_upsert_accepts_unique_keys(self):
        """测试 upsert 方法签名接受 unique_keys 参数"""
        import inspect
        sig = inspect.signature(BaseRepository.upsert)
        params = list(sig.parameters.keys())
        assert 'unique_keys' in params
