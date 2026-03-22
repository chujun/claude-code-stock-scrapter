# storage/base.py
"""存储层抽象基类"""

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional


class BaseRepository(ABC):
    """数据访问层抽象基类

    定义数据存储的标准接口，具体实现由子类完成
    """

    @abstractmethod
    async def insert(self, table: str, records: List[Dict[str, Any]]) -> int:
        """批量插入数据

        Args:
            table: 表名
            records: 要插入的数据列表

        Returns:
            int: 插入的条数
        """
        pass

    @abstractmethod
    async def upsert(self, table: str, records: List[Dict[str, Any]], unique_keys: List[str]) -> int:
        """插入或更新数据

        Args:
            table: 表名
            records: 要插入/更新的数据列表
            unique_keys: 用于判断唯一性的字段列表

        Returns:
            int: 影响的行数
        """
        pass

    @abstractmethod
    async def query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """执行查询

        Args:
            sql: SQL语句
            params: 查询参数

        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        pass

    @abstractmethod
    async def execute(self, sql: str, params: Optional[Dict[str, Any]] = None) -> int:
        """执行SQL语句

        Args:
            sql: SQL语句
            params: 执行参数

        Returns:
            int: 影响的行数
        """
        pass
