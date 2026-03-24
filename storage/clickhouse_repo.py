# storage/clickhouse_repo.py
"""ClickHouse数据访问实现"""

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set

from clickhouse_driver import Client

from storage.base import BaseRepository


# 表名验证正则：只允许字母、数字、下划线
VALID_TABLE_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# 允许的表名列表（白名单）
ALLOWED_TABLES = {
    'stock_info', 'stock_daily', 'sync_status', 'sync_error',
    'sync_report', 'daily_index', 'stock_split'
}


def _validate_table_name(table: str) -> None:
    """验证表名是否合法

    Args:
        table: 表名

    Raises:
        ValueError: 表名不合法
    """
    if not table:
        raise ValueError("Table name cannot be empty")
    if not VALID_TABLE_NAME_PATTERN.match(table):
        raise ValueError(f"Invalid table name: {table}. Must match pattern: {VALID_TABLE_NAME_PATTERN.pattern}")
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Table {table} not in allowed tables list")


class ClickHouseRepository(BaseRepository):
    """ClickHouse数据访问层实现"""

    def __init__(
        self,
        config=None,
        host: str = "localhost",
        port: int = 9000,
        database: str = "stock_scraper",
        user: str = "default",
        password: str = "",
        max_workers: int = 10
    ):
        """初始化ClickHouse连接

        Args:
            config: ClickHouseSettings配置对象（优先使用）
            host: ClickHouse主机地址
            port: ClickHouse端口
            database: 数据库名称
            user: 用户名
            password: 密码
            max_workers: 线程池最大工作线程数
        """
        # 如果提供了config对象，优先使用其中的配置
        if config is not None:
            self.host = config.host
            self.port = config.port
            self.database = config.database
            self.user = config.user
            self.password = config.password
        else:
            self.host = host
            self.port = port
            self.database = database
            self.user = user
            self.password = password
        self._client: Optional[Client] = None
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    @property
    def client(self) -> Client:
        """获取或创建ClickHouse客户端"""
        if self._client is None:
            self._client = Client(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
        return self._client

    async def insert(self, table: str, records: List[Dict[str, Any]]) -> int:
        """批量插入数据

        Args:
            table: 表名
            records: 要插入的记录列表

        Returns:
            int: 插入的条数

        Raises:
            ValueError: 表名不合法
        """
        if not records:
            return 0

        _validate_table_name(table)

        # 获取表字段（在线程池中执行以避免线程问题）
        loop = asyncio.get_event_loop()
        columns = await loop.run_in_executor(
            self._executor,
            lambda: self.get_table_columns(table)
        )
        if not columns:
            raise ValueError(f"Table {table} not found or has no columns")

        # 过滤掉不在表字段中的键
        filtered_records = []
        for record in records:
            filtered = {k: v for k, v in record.items() if k in columns}
            filtered_records.append(filtered)

        if not filtered_records:
            return 0

        # 构建插入SQL - 表名已通过验证
        sample = filtered_records[0]
        col_list = ", ".join(sample.keys())
        sql = f"INSERT INTO {table} ({col_list}) VALUES"

        # 日期列需要转换为date/datetime对象，ClickHouse驱动不接受字符串
        date_columns = {'trade_date', 'list_date', 'delist_date'}
        datetime_columns = {'created_at', 'updated_at'}
        processed_values = []
        for record in filtered_records:
            processed = []
            for k in sample.keys():
                v = record.get(k)
                if isinstance(v, str):
                    if k in date_columns:
                        # 解析为 date 对象
                        try:
                            v = datetime.strptime(v, '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                v = datetime.strptime(v, '%Y-%m-%d %H:%M:%S').date()
                            except ValueError:
                                pass
                    elif k in datetime_columns:
                        # 解析为 datetime 对象，保留时区信息
                        try:
                            # 先尝试解析带时区的 ISO 格式
                            v = datetime.fromisoformat(v)
                        except ValueError:
                            try:
                                v = datetime.strptime(v, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                pass
                processed.append(v)
            processed_values.append(tuple(processed))

        values = processed_values

        result = await loop.run_in_executor(
            self._executor,
            lambda: self.client.execute(sql, values)
        )

        # ClickHouse driver returns (number_of_rows, ) for INSERT
        if isinstance(result, tuple):
            return result[0] if result else len(filtered_records)
        return len(filtered_records)

    async def upsert(
        self,
        table: str,
        records: List[Dict[str, Any]],
        unique_keys: List[str]
    ) -> int:
        """插入或更新数据

        使用 INSERT INTO ... VALUES 然后由 ReplacingMergeTree 引擎处理重复数据

        Args:
            table: 表名
            records: 要插入/更新的记录列表
            unique_keys: 用于判断唯一性的字段列表（传递给 ReplacingMergeTree）

        Returns:
            int: 插入的条数
        """
        _validate_table_name(table)
        # unique_keys 用于文档目的，实际去重由 ClickHouse ReplacingMergeTree 引擎处理
        return await self.insert(table, records)

    async def query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """执行查询

        Args:
            sql: SQL语句（必须使用参数化查询以防止SQL注入）
            params: 查询参数

        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        loop = asyncio.get_event_loop()
        if params:
            result = await loop.run_in_executor(
                self._executor,
                lambda: self.client.execute(sql, params, with_column_types=True)
            )
        else:
            result = await loop.run_in_executor(
                self._executor,
                lambda: self.client.execute(sql, with_column_types=True)
            )

        # 转换结果为字典列表
        # result 格式: (rows, columns) 其中 columns = [(name, type), ...]
        if not result or not result[0]:
            return []

        rows, columns = result
        if not rows:
            return []

        # 提取列名
        col_names = [col[0] for col in columns]

        # 转换每一行
        return [dict(zip(col_names, row)) for row in rows]

    async def execute(self, sql: str, params: Optional[Dict[str, Any]] = None) -> int:
        """执行SQL语句

        Args:
            sql: SQL语句
            params: 执行参数

        Returns:
            int: 影响的行数
        """
        loop = asyncio.get_event_loop()
        if params:
            result = await loop.run_in_executor(
                self._executor,
                lambda: self.client.execute(sql, params)
            )
        else:
            result = await loop.run_in_executor(
                self._executor,
                lambda: self.client.execute(sql)
            )

        if isinstance(result, tuple):
            return result[0] if result else 0
        return result if result else 0

    async def get_existing_dates(
        self,
        table: str,
        stock_code: str,
        date_column: str = "trade_date"
    ) -> Set[date]:
        """获取股票已存在的日期集合

        Args:
            table: 表名
            stock_code: 股票代码
            date_column: 日期列名

        Returns:
            Set[date]: 已存在的日期集合
        """
        _validate_table_name(table)
        sql = f"SELECT {date_column} FROM {table} WHERE stock_code = %(stock_code)s"
        result = await self.query(sql, {"stock_code": stock_code})
        return {row[date_column] for row in result}

    def get_table_columns(self, table: str) -> List[str]:
        """获取表的字段列表

        Args:
            table: 表名

        Returns:
            List[str]: 字段列表

        Raises:
            ValueError: 表名不合法或表不存在
        """
        _validate_table_name(table)

        try:
            result = self.client.execute(f"DESC {table}")
            return [row[0] for row in result]
        except Exception as e:
            raise ValueError(f"Failed to get columns for table {table}: {str(e)}")

    async def __aenter__(self) -> "ClickHouseRepository":
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器退出"""
        self.close()

    def close(self) -> None:
        """关闭连接和线程池"""
        if self._client:
            self._client.disconnect()
            self._client = None
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None
