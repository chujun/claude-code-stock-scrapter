# storage/__init__.py
"""存储层模块"""

from storage.base import BaseRepository
from storage.clickhouse_repo import ClickHouseRepository

__all__ = [
    "BaseRepository",
    "ClickHouseRepository",
]
