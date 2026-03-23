# data_source/base.py
"""数据源抽象基类"""

from abc import ABC, abstractmethod
from typing import List

from models.stock_info import StockInfo
from models.stock_daily import StockDaily
from models.daily_index import DailyIndex
from models.stock_split import StockSplit


class BaseDataSource(ABC):
    """数据源抽象基类"""

    @abstractmethod
    async def get_stock_list(self) -> List[StockInfo]:
        """获取股票列表

        Returns:
            List[StockInfo]: 股票信息列表
        """
        pass

    @abstractmethod
    async def get_daily(
        self,
        stock_code: str,
        start_date,
        end_date,
        adjust_type: str = "qfq"
    ) -> List[StockDaily]:
        """获取日线数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            adjust_type: 复权类型 (qfq/hfq/none)

        Returns:
            List[StockDaily]: 日线数据列表
        """
        pass

    @abstractmethod
    async def get_index(
        self,
        index_code: str,
        start_date,
        end_date
    ) -> List[DailyIndex]:
        """获取指数数据

        Args:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            List[DailyIndex]: 指数数据列表
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查

        Returns:
            bool: 服务是否可用
        """
        pass

    @abstractmethod
    async def get_split(
        self,
        stock_code: str,
        start_date=None,
        end_date=None
    ) -> List[StockSplit]:
        """获取分红送股数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            List[StockSplit]: 分红送股记录列表
        """
        pass

    @abstractmethod
    def get_financial_indicator(self, stock_code: str) -> dict:
        """获取股票财务指标

        Args:
            stock_code: 股票代码

        Returns:
            dict: 包含财务指标的字典
                - pe_ratio: 市盈率（动态）
                - static_pe: 静态市盈率
                - dynamic_pe: 动态市盈率
                - pb_ratio: 市净率
                - total_market_cap: 总市值
                - float_market_cap: 流通市值
        """
        pass

    @abstractmethod
    async def get_financial_indicator_async(self, stock_code: str) -> dict:
        """异步获取股票财务指标

        Args:
            stock_code: 股票代码

        Returns:
            dict: 包含财务指标的字典
        """
        pass
