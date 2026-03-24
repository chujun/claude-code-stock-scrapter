# services/sync_service.py
"""股票同步服务"""

import logging
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from data_source.base import BaseDataSource
from storage.base import BaseRepository
from models.stock_info import StockInfo
from models.stock_daily import StockDaily
from models.sync_report import SyncReport
from services.quality_service import QualityService
from services.report_service import ReportService
from services.exceptions import BusinessError

logger = logging.getLogger(__name__)


class SyncStrategy(str, Enum):
    """同步策略枚举

    - skip: 已存在的日期跳过（最快，适合增量后不再更新的历史数据）
    - overwrite: 覆盖所有数据（默认，ReplacingMergeTree自动去重）
    - incremental: 只同步新增日期（智能增量，平衡速度和数据新鲜度）
    """
    SKIP = "skip"
    OVERWRITE = "overwrite"
    INCREMENTAL = "incremental"


class StockSyncService:
    """股票数据同步服务

    负责从数据源获取股票数据，进行质量校验后存入存储层
    """

    def __init__(
        self,
        data_source: BaseDataSource,
        storage: BaseRepository,
        quality_service: QualityService,
        report_service: Optional[ReportService] = None
    ):
        """初始化同步服务

        Args:
            data_source: 数据源
            storage: 存储层
            quality_service: 质量服务
            report_service: 报告服务（可选）
        """
        self.data_source = data_source
        self.storage = storage
        self.quality_service = quality_service
        self.report_service = report_service

        # 同步状态缓存
        self._sync_status: Dict[str, Dict[str, Any]] = {}

    def mark_sync_start(self, stock_code: str) -> None:
        """标记同步开始

        Args:
            stock_code: 股票代码
        """
        self._sync_status[stock_code] = {
            'stock_code': stock_code,
            'status': 'running',
            'start_time': datetime.now(),
            'records': 0,
            'errors': []
        }

    def mark_sync_end(self, stock_code: str, success: bool = True) -> None:
        """标记同步结束

        Args:
            stock_code: 股票代码
            success: 是否成功
        """
        if stock_code in self._sync_status:
            status = self._sync_status[stock_code]
            status['status'] = 'success' if success else 'failed'
            status['end_time'] = datetime.now()
            if 'start_time' in status:
                duration = (status['end_time'] - status['start_time']).total_seconds()
                status['duration_seconds'] = duration

    def get_sync_status(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取同步状态

        Args:
            stock_code: 股票代码

        Returns:
            Optional[Dict]: 同步状态
        """
        return self._sync_status.get(stock_code)

    async def sync_stock_daily(
        self,
        stock_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        adjust_type: str = "qfq"
    ) -> Dict[str, Any]:
        """同步单只股票的历史数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期（默认为上市日或3年前）
            end_date: 结束日期（默认为今天）
            adjust_type: 复权类型

        Returns:
            Dict: 同步结果统计
        """
        return await self.sync_single_stock(stock_code, start_date, end_date, adjust_type)

    async def sync_single_stock(
        self,
        stock_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        adjust_type: str = "qfq",
        strategy: SyncStrategy = SyncStrategy.OVERWRITE
    ) -> Dict[str, Any]:
        """同步单只股票的历史数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期（默认为上市日或3年前）
            end_date: 结束日期（默认为今天）
            adjust_type: 复权类型
            strategy: 同步策略，决定如何处理已存在的数据

        Returns:
            Dict: 同步结果统计
        """
        self.mark_sync_start(stock_code)

        try:
            # 如果没有指定日期范围，从3年前开始
            if end_date is None:
                end_date = date.today()

            # 根据策略过滤已存在的数据
            existing_dates: Set[date] = set()
            filtered_start_date = start_date

            # SKIP和INCREMENTAL策略都需要先检查数据库
            if strategy in (SyncStrategy.SKIP, SyncStrategy.INCREMENTAL):
                # 获取交易日历（排除周末和节假日）
                trading_dates = await self.data_source.get_trading_dates(
                    start_date or date(end_date.year - 3, end_date.month, end_date.day),
                    end_date
                )

                existing_dates = await self.storage.get_existing_dates(
                    'stock_daily', stock_code, 'trade_date'
                )
                if existing_dates and trading_dates:
                    # 只比较交易日，排除周末和节假日
                    missing_trading_dates = trading_dates - existing_dates

                    if start_date is None:
                        # 无开始日期，检查是否有最新日期之外的数据需要同步
                        latest_existing = max(existing_dates)
                        latest_trading = max(trading_dates)
                        if latest_existing >= latest_trading:
                            self.mark_sync_end(stock_code, success=True)
                            return {
                                'stock_code': stock_code,
                                'success_count': 0,
                                'failed_count': 0,
                                'skipped_count': 0,
                                'status': 'success',
                                'message': f'All trading dates already exist (latest: {latest_existing})',
                                'strategy': strategy.value
                            }
                        # 继续同步，从最新日期之后开始
                        filtered_start_date = date.fromordinal(latest_existing.toordinal() + 1)
                    else:
                        # 有开始日期，检查是否所有交易日都已存在
                        if not missing_trading_dates:
                            self.mark_sync_end(stock_code, success=True)
                            return {
                                'stock_code': stock_code,
                                'success_count': 0,
                                'failed_count': 0,
                                'skipped_count': len(trading_dates),
                                'status': 'success',
                                'message': 'All trading dates already exist',
                                'strategy': strategy.value
                            }

            # 获取历史数据
            records = await self.data_source.get_daily(
                stock_code=stock_code,
                start_date=filtered_start_date or date(end_date.year - 3, end_date.month, end_date.day),
                end_date=end_date,
                adjust_type=adjust_type
            )

            if not records:
                self.mark_sync_end(stock_code, success=True)
                return {
                    'stock_code': stock_code,
                    'success_count': 0,
                    'failed_count': 0,
                    'status': 'success',
                    'message': 'No data available',
                    'strategy': strategy.value
                }

            # 根据策略过滤已存在的日期
            if strategy == SyncStrategy.INCREMENTAL:
                if not existing_dates:
                    existing_dates = await self.storage.get_existing_dates(
                        'stock_daily', stock_code, 'trade_date'
                    )
                if existing_dates:
                    original_count = len(records)
                    records = [r for r in records if r.trade_date not in existing_dates]
                    filtered_count = original_count - len(records)
                    if filtered_count > 0:
                        logger.info(f"{stock_code}: 过滤 {filtered_count} 条已存在的数据")

            # 质量校验
            quality_result = await self.quality_service.batch_validate(records)

            # 只插入通过校验的数据
            valid_records = [
                r for r, flag in zip(records, quality_result['quality_flags'])
                if flag == 'good'
            ]

            inserted_count = 0
            if valid_records:
                # 转换为字典格式
                record_dicts = [r.model_dump() for r in valid_records]
                # 转换 date 为字符串
                for d in record_dicts:
                    if 'trade_date' in d and isinstance(d['trade_date'], date):
                        d['trade_date'] = d['trade_date'].isoformat()
                inserted_count = await self.storage.insert('stock_daily', record_dicts)

            self.mark_sync_end(stock_code, success=True)

            return {
                'stock_code': stock_code,
                'total_records': len(records),
                'success_count': inserted_count,
                'failed_count': quality_result['failed'],
                'status': 'success',
                'quality_flags': quality_result['quality_flags'],
                'strategy': strategy.value
            }

        except BusinessError as e:
            self.mark_sync_end(stock_code, success=False)
            if stock_code in self._sync_status:
                self._sync_status[stock_code]['errors'].append(str(e))
            return {
                'stock_code': stock_code,
                'success_count': 0,
                'failed_count': 1,
                'status': 'failed',
                'error': str(e)
            }
        except Exception as e:
            self.mark_sync_end(stock_code, success=False)
            if stock_code in self._sync_status:
                self._sync_status[stock_code]['errors'].append(str(e))
            return {
                'stock_code': stock_code,
                'success_count': 0,
                'failed_count': 1,
                'status': 'failed',
                'error': f'Unexpected error: {str(e)}'
            }

    async def sync_stock_info(self, stocks: List[StockInfo]) -> Dict[str, Any]:
        """同步股票基本信息

        Args:
            stocks: 股票信息列表

        Returns:
            Dict: 同步结果统计
        """
        if not stocks:
            return {
                'total': 0,
                'success_count': 0,
                'failed_count': 0,
                'status': 'success',
                'message': 'No stock info to sync'
            }

        try:
            # 转换为字典格式
            record_dicts = [s.model_dump() for s in stocks]
            # 转换日期/日期时间为 ISO 字符串
            for d in record_dicts:
                for key, value in d.items():
                    if isinstance(value, datetime):
                        # 确保 datetime 有时区信息
                        if value.tzinfo is None:
                            value = value.replace(tzinfo=timezone.utc)
                        d[key] = value.isoformat()
                    elif isinstance(value, date):
                        d[key] = value.isoformat()

            # 插入数据库
            await self.storage.insert('stock_info', record_dicts)

            return {
                'total': len(stocks),
                'success_count': len(stocks),
                'failed_count': 0,
                'status': 'success'
            }
        except Exception as e:
            return {
                'total': len(stocks),
                'success_count': 0,
                'failed_count': len(stocks),
                'status': 'failed',
                'error': str(e)
            }

    async def batch_sync(
        self,
        stock_codes: List[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """批量同步多只股票

        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            Dict: 批量同步结果统计
        """
        total = len(stock_codes)
        success_count = 0
        failed_count = 0
        results = []

        for stock_code in stock_codes:
            result = await self.sync_single_stock(stock_code, start_date, end_date)
            results.append(result)
            if result['status'] == 'success':
                success_count += 1
            else:
                failed_count += 1

        return {
            'total': total,
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results
        }
