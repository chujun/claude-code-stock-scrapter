# data_source/akshare_client.py
"""akshare数据源实现"""

import asyncio
import logging
import time
from datetime import date, datetime
from typing import List, Optional

import akshare as ak
import pandas as pd

logger = logging.getLogger(__name__)

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
    """akshare数据源实现

    使用akshare库获取A股数据
    """

    def __init__(self, settings=None):
        """初始化akshare客户端

        Args:
            settings: 配置对象，默认从配置文件加载
        """
        self.settings = settings or get_settings().data_source
        self.rate_limiter = RateLimiter(
            base_interval=self.settings.rate_limit.base_interval
        )

    async def close(self) -> None:
        """关闭客户端"""
        pass  # akshare不需要关闭连接

    def _run_sync(self, func, *args, **kwargs):
        """在线程池中运行同步函数"""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(
            None, lambda: func(*args, **kwargs)
        )

    async def get_stock_list(self) -> List[StockInfo]:
        """获取A股所有股票列表

        Returns:
            List[StockInfo]: 股票信息列表

        Raises:
            NetworkError: 网络请求失败
            DataError: 数据解析失败
        """
        try:
            await self.rate_limiter.wait()

            # 使用akshare获取股票列表
            df = await self._run_sync(ak.stock_info_a_code_name)

            stocks = []
            for _, row in df.iterrows():
                stock = StockInfo(
                    stock_code=str(row['code']),
                    stock_name=str(row['name']),
                    market="SSE" if str(row['code']).startswith(("6", "9")) else "SZSE",
                    status="active"
                )
                stocks.append(stock)

            return stocks
        except BusinessError:
            raise
        except Exception as e:
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
            await self.rate_limiter.wait()

            # akshare的adjust参数映射
            adjust_map = {"qfq": "qfq", "hfq": "hfq", "none": ""}
            ak_adjust = adjust_map.get(adjust_type, "qfq")

            # 使用腾讯数据源获取日线数据 (eastmoney被代理屏蔽)
            # 腾讯接口需要带市场前缀
            symbol_with_prefix = f"sh{stock_code}" if stock_code.startswith(("6", "9")) else f"sz{stock_code}"
            df = await self._run_sync(
                ak.stock_zh_a_hist_tx,
                symbol=symbol_with_prefix,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust=ak_adjust
            )

            if df is None or df.empty:
                return []

            daily_list = []
            for _, row in df.iterrows():
                # 处理日期 (腾讯数据源使用 'date')
                trade_date = row.get('date')
                if isinstance(trade_date, str):
                    trade_date = datetime.strptime(trade_date, "%Y-%m-%d").date()
                elif hasattr(trade_date, 'date'):
                    trade_date = trade_date.date()

                # 计算涨跌幅 (腾讯数据源不直接提供，通过前后收盘价计算)
                close = float(row.get('close', 0))
                open_price = float(row.get('open', 0))
                if len(daily_list) > 0:
                    pre_close = daily_list[-1].close
                    change_pct = (close - pre_close) / pre_close * 100 if pre_close != 0 else 0
                else:
                    pre_close = close
                    change_pct = 0

                daily = StockDaily(
                    stock_code=stock_code,
                    trade_date=trade_date,
                    open=open_price,
                    high=float(row.get('high', 0)),
                    low=float(row.get('low', 0)),
                    close=close,
                    volume=0,  # 腾讯数据源不提供成交量
                    turnover=float(row.get('amount', 0)) if pd.notna(row.get('amount')) else 0,
                    change_pct=change_pct,
                    pre_close=pre_close,
                    amplitude_pct=0,  # 腾讯数据源不提供振幅
                    turnover_rate=0,  # 腾讯数据源不提供换手率
                    data_source="akshare_tx",
                    adjust_type=adjust_type,
                    is_adjusted=(adjust_type != "none")
                )
                daily_list.append(daily)

            return daily_list
        except BusinessError:
            raise
        except Exception as e:
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
            await self.rate_limiter.wait()

            # 指数代码映射到akshare格式
            index_map = {
                "000001": "sh000001",  # 上证指数
                "399001": "sz399001",  # 深证成指
                "399006": "sz399006",  # 创业板指
            }

            symbol = index_map.get(index_code, index_code)

            # 使用akshare获取指数数据
            df = await self._run_sync(
                ak.stock_zh_index_daily,
                symbol=symbol
            )

            if df is None or df.empty:
                return []

            # 过滤日期范围
            index_list = []
            index_name_map = {
                "000001": "上证指数",
                "399001": "深证成指",
                "399006": "创业板指"
            }

            for _, row in df.iterrows():
                trade_date = row['date']
                if isinstance(trade_date, str):
                    trade_date = datetime.strptime(trade_date, "%Y-%m-%d").date()

                # 过滤日期范围
                if trade_date < start_date or trade_date > end_date:
                    continue

                # 计算涨跌幅 (需要前一天的收盘价)
                close = float(row.get('close', 0))
                if len(index_list) > 0:
                    pre_close = index_list[-1].close
                    change_pct = (close - pre_close) / pre_close * 100 if pre_close != 0 else 0
                else:
                    change_pct = 0

                index = DailyIndex(
                    index_code=index_code,
                    index_name=index_name_map.get(index_code, index_code),
                    trade_date=trade_date,
                    open=float(row.get('open', 0)),
                    high=float(row.get('high', 0)),
                    low=float(row.get('low', 0)),
                    close=close,
                    volume=int(row.get('volume', 0)),
                    turnover=0,  # stock_zh_index_daily不提供
                    change_pct=change_pct,
                    data_source="akshare"
                )
                index_list.append(index)

            return index_list
        except Exception as e:
            raise NetworkError(f"Failed to get index data for {index_code}: {str(e)}")

    async def get_split(
        self,
        stock_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List["StockSplit"]:
        """获取分红送股数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            List[StockSplit]: 分红送股记录列表
        """
        try:
            await self.rate_limiter.wait()

            # 使用akshare获取分红数据
            df = await self._run_sync(
                ak.stock_history_dividend_detail,
                symbol=stock_code
            )

            if df is None or df.empty:
                return []

            from models.stock_split import StockSplit

            split_list = []
            for _, row in df.iterrows():
                # 处理除权除息日
                event_date = row.get('除权除息日')
                if pd.isna(event_date) or event_date is None:
                    continue
                if isinstance(event_date, str):
                    event_date = datetime.strptime(event_date, "%Y-%m-%d").date()
                elif hasattr(event_date, 'date'):
                    event_date = event_date.date()

                # 过滤日期范围
                if start_date and event_date < start_date:
                    continue
                if end_date and event_date > end_date:
                    continue

                # 判断事件类型
                bonus = float(row.get('送股', 0) or 0)
                transfer = float(row.get('转增', 0) or 0)
                dividend = float(row.get('派息', 0) or 0)

                if bonus > 0 or transfer > 0:
                    event_type = "split"
                elif dividend > 0:
                    event_type = "dividend"
                else:
                    event_type = "allot"

                split = StockSplit(
                    stock_code=stock_code,
                    event_date=event_date,
                    event_type=event_type,
                    bonus_ratio=bonus if bonus > 0 else None,
                    dividend_ratio=dividend if dividend > 0 else None,
                    price_adjust=None,
                    data_source="akshare"
                )
                split_list.append(split)

            return split_list
        except Exception as e:
            raise NetworkError(f"Failed to get split data for {stock_code}: {str(e)}")

    def get_financial_indicator(self, stock_code: str) -> dict:
        """获取股票财务指标

        Args:
            stock_code: 股票代码

        Returns:
            dict: 包含财务指标的字典
        """
        if not stock_code:
            raise ValueError("stock_code cannot be empty")

        # 标准化股票代码格式
        symbol = stock_code
        if not symbol.startswith(('sh', 'sz', 'SH', 'SZ')):
            # 添加市场前缀
            if symbol.startswith(('6', '9')):
                symbol = f"SH{symbol}"
            else:
                symbol = f"SZ{symbol}"

        try:
            # 同步限流 - 使用time.sleep而非异步wait
            current_time = time.time()
            elapsed = current_time - self.rate_limiter.last_request_time
            if elapsed < self.rate_limiter.base_interval:
                time.sleep(self.rate_limiter.base_interval - elapsed)
            self.rate_limiter.last_request_time = time.time()

            # 初始化结果
            result = {
                'pe_ratio': None,
                'static_pe': None,
                'dynamic_pe': None,
                'pb_ratio': None,
                'total_market_cap': None,
                'float_market_cap': None
            }

            # 优先使用雪球API（eastmoney被代理屏蔽）
            try:
                df = ak.stock_individual_basic_info_xq(symbol=symbol)
                if df is not None and not df.empty:
                    info_dict = dict(zip(df['item'].values, df['value'].values))
                    # 解析发行PE（雪球只提供发行市盈率）
                    pe_value = info_dict.get('pe_after_issuing')
                    if pe_value and pe_value != '-' and pe_value != 'nan':
                        try:
                            result['pe_ratio'] = float(pe_value)
                            result['static_pe'] = float(pe_value)
                            result['dynamic_pe'] = float(pe_value)
                        except (ValueError, TypeError):
                            pass
                    logger.debug(f"Xueqiu API got pe_after_issuing: {pe_value}")
            except Exception as e:
                logger.debug(f"Xueqiu API failed for {symbol}: {e}")

            # 如果雪球没有获取到PE，尝试东方财富API（可能被屏蔽）
            if result['pe_ratio'] is None:
                try:
                    df = ak.stock_individual_info_em(symbol=stock_code)
                    if df is not None and not df.empty:
                        info_dict = dict(zip(df['item'].values, df['value'].values))
                        # 解析各项指标
                        for key, value in info_dict.items():
                            if not value or value == '-':
                                continue
                            try:
                                # 市盈率相关（互斥匹配）
                                if key == '市盈率' or key == 'PE(动静态)':
                                    result['pe_ratio'] = float(value)
                                elif key == '静态市盈率':
                                    result['static_pe'] = float(value)
                                elif key == '动态市盈率':
                                    result['dynamic_pe'] = float(value)
                                # 市净率
                                elif key == '市净率' or key == 'PB':
                                    result['pb_ratio'] = float(value)
                                # 总市值
                                elif '总市值' in key:
                                    result['total_market_cap'] = self._parse_market_cap(value)
                                # 流通市值
                                elif '流通市值' in key:
                                    result['float_market_cap'] = self._parse_market_cap(value)
                            except (ValueError, TypeError):
                                continue
                except Exception as e:
                    logger.debug(f"Eastmoney API failed for {stock_code}: {e}")

            return result

        except Exception as e:
            # 返回默认值而非抛出异常，避免中断主流程
            logger.warning(f"Failed to get financial indicator for {stock_code}: {e}")
            return {
                'pe_ratio': None,
                'static_pe': None,
                'dynamic_pe': None,
                'pb_ratio': None,
                'total_market_cap': None,
                'float_market_cap': None
            }

    def _parse_market_cap(self, value) -> Optional[float]:
        """解析市值字符串

        Args:
            value: 市值字符串，如 "1.23万亿"

        Returns:
            float: 市值数值
        """
        if not value or value == '-':
            return None

        try:
            value = str(value).strip()

            # 处理万亿
            if '万亿' in value:
                return float(value.replace('万亿', '')) * 1e12
            # 处理亿
            elif '亿' in value:
                return float(value.replace('亿', '')) * 1e8
            # 处理万
            elif '万' in value:
                return float(value.replace('万', '')) * 1e4
            else:
                return float(value)

        except (ValueError, AttributeError):
            return None

    async def get_financial_indicator_async(self, stock_code: str) -> dict:
        """异步获取股票财务指标

        Args:
            stock_code: 股票代码

        Returns:
            dict: 包含财务指标的字典
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_financial_indicator, stock_code)

    async def health_check(self) -> bool:
        """健康检查

        Returns:
            bool: 服务是否可用
        """
        try:
            # 简单测试：获取一只股票的数据
            await self.get_daily(
                stock_code='600000',
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 10),
                adjust_type='qfq'
            )
            return True
        except Exception:
            return False
