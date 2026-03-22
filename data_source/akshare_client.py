# data_source/akshare_client.py
"""akshare数据源实现"""

import asyncio
from datetime import date, datetime
from typing import List, Optional

import aiohttp

from data_source.base import BaseDataSource
from data_source.exceptions import (
    NetworkError,
    TimeoutError,
    RateLimitError,
    ServerError,
    BusinessError,
    NoDataError,
    DataError,
)
from data_source.rate_limiter import RateLimiter
from models.stock_info import StockInfo
from models.stock_daily import StockDaily
from models.daily_index import DailyIndex
from config.settings import get_settings


class AkshareClient(BaseDataSource):
    """akshare数据源实现"""

    def __init__(self, settings=None):
        """初始化akshare客户端

        Args:
            settings: 配置对象，默认从配置文件加载
        """
        self.settings = settings or get_settings().data_source
        self.rate_limiter = RateLimiter(
            base_interval=self.settings.rate_limit.base_interval
        )
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建HTTP会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """关闭HTTP会话"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        url: str,
        params: dict = None,
        method: str = "GET"
    ) -> dict:
        """发送HTTP请求

        Args:
            url: 请求URL
            params: 请求参数
            method: 请求方法

        Returns:
            dict: 响应数据
        """
        await self.rate_limiter.wait()
        session = await self._get_session()

        try:
            async with session.request(
                method,
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    raise RateLimitError("API rate limit exceeded")
                elif response.status >= 500:
                    raise ServerError(f"Server error: {response.status}")
                else:
                    raise NetworkError(
                        f"Request failed with status {response.status}",
                        error_code=str(response.status)
                    )
        except asyncio.TimeoutError:
            raise TimeoutError("Request timeout")
        except aiohttp.ClientError as e:
            raise NetworkError(f"Client error: {str(e)}")

    async def get_stock_list(self) -> List[StockInfo]:
        """获取A股所有股票列表

        Returns:
            List[StockInfo]: 股票信息列表

        Raises:
            NetworkError: 网络请求失败
            DataError: 数据解析失败
        """
        try:
            url = "http://api.avic.com.cn/stock/list"
            params = {"market": "sh"}
            data = await self._request(url, params)

            stocks = []
            for item in data.get("data", []):
                stock = StockInfo(
                    stock_code=item.get("code", ""),
                    stock_name=item.get("name", ""),
                    market="SSE" if item.get("code", "").startswith(("6", "9")) else "SZSE",
                    status="active"
                )
                stocks.append(stock)

            return stocks
        except NetworkError:
            # 网络错误向上传播，不包装
            raise
        except (KeyError, ValueError, TypeError) as e:
            # 数据解析错误，标记为 DataError
            raise DataError(f"Failed to parse stock list data: {str(e)}")
        except Exception as e:
            # 其他错误包装为 NetworkError（可重试）
            raise NetworkError(f"Failed to get stock list: {str(e)}")

    async def get_daily(
        self,
        stock_code: str,
        start_date: date,
        end_date: date,
        adjust_type: str = "qfq"
    ) -> List[StockDaily]:
        """获取单只股票日线数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            adjust_type: 复权类型 (qfq/hfq/none)

        Returns:
            List[StockDaily]: 日线数据列表

        Raises:
            BusinessError: adjust_type 无效
            NetworkError: 网络请求失败
            DataError: 数据解析失败
        """
        # 验证 adjust_type 参数
        valid_adjust_types = ("qfq", "hfq", "none")
        if adjust_type not in valid_adjust_types:
            raise BusinessError(
                f"Invalid adjust_type: {adjust_type}. Must be one of {valid_adjust_types}",
                error_code="invalid_adjust_type"
            )

        try:
            url = f"http://api.avic.com.cn/stock/daily"
            params = {
                "code": stock_code,
                "start_date": start_date.strftime("%Y%m%d"),
                "end_date": end_date.strftime("%Y%m%d"),
                "adjust": adjust_type
            }
            data = await self._request(url, params)

            daily_list = []
            for item in data.get("data", []):
                daily = StockDaily(
                    stock_code=stock_code,
                    trade_date=datetime.strptime(item.get("date", ""), "%Y-%m-%d").date(),
                    open=float(item.get("open", 0)),
                    high=float(item.get("high", 0)),
                    low=float(item.get("low", 0)),
                    close=float(item.get("close", 0)),
                    volume=int(item.get("volume", 0)),
                    turnover=float(item.get("turnover", 0)),
                    change_pct=float(item.get("change_pct", 0)),
                    pre_close=float(item.get("pre_close", 0)),
                    amplitude_pct=float(item.get("amplitude", 0)),
                    turnover_rate=float(item.get("turnover_rate", 0)),
                    data_source="akshare",
                    adjust_type=adjust_type,
                    is_adjusted=(adjust_type != "none")
                )
                daily_list.append(daily)

            return daily_list
        except NetworkError:
            # 网络错误向上传播，不包装
            raise
        except (KeyError, ValueError, TypeError) as e:
            # 数据解析错误，应该被标记为 DataError
            raise DataError(f"Failed to parse daily data for {stock_code}: {str(e)}")
        except Exception as e:
            # 其他错误包装为 NetworkError（可重试）
            raise NetworkError(f"Failed to get daily data for {stock_code}: {str(e)}")

    async def get_index(
        self,
        index_code: str,
        start_date: date,
        end_date: date
    ) -> List[DailyIndex]:
        """获取指数数据

        Args:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            List[DailyIndex]: 指数数据列表

        Raises:
            NetworkError: 网络请求失败
            DataError: 数据解析失败
        """
        try:
            url = f"http://api.avic.com.cn/index/daily"
            params = {
                "code": index_code,
                "start_date": start_date.strftime("%Y%m%d"),
                "end_date": end_date.strftime("%Y%m%d")
            }
            data = await self._request(url, params)

            index_list = []
            index_name_map = {
                "000001": "上证指数",
                "399001": "深证成指",
                "399006": "创业板指"
            }

            for item in data.get("data", []):
                index = DailyIndex(
                    index_code=index_code,
                    index_name=index_name_map.get(index_code, index_code),
                    trade_date=datetime.strptime(item.get("date", ""), "%Y-%m-%d").date(),
                    open=float(item.get("open", 0)),
                    high=float(item.get("high", 0)),
                    low=float(item.get("low", 0)),
                    close=float(item.get("close", 0)),
                    volume=int(item.get("volume", 0)),
                    turnover=float(item.get("turnover", 0)),
                    change_pct=float(item.get("change_pct", 0)),
                    data_source="akshare"
                )
                index_list.append(index)

            return index_list
        except NetworkError:
            # 网络错误向上传播，不包装
            raise
        except (KeyError, ValueError, TypeError) as e:
            # 数据解析错误，标记为 DataError
            raise DataError(f"Failed to parse index data for {index_code}: {str(e)}")
        except Exception as e:
            # 其他错误包装为 NetworkError（可重试）
            raise NetworkError(f"Failed to get index data for {index_code}: {str(e)}")

    async def health_check(self) -> bool:
        """健康检查

        Returns:
            bool: 服务是否可用
        """
        try:
            # 简单测试：检查是否能获取股票列表
            await self.get_stock_list()
            return True
        except Exception:
            return False
