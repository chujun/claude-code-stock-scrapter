# services/sync_service.py
"""股票同步服务"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from data_source.base import BaseDataSource
from storage.base import BaseRepository
from models.stock_daily import StockDaily
from models.sync_report import SyncReport
from services.quality_service import QualityService
from services.report_service import ReportService
from services.exceptions import BusinessError


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
        self.mark_sync_start(stock_code)

        try:
            # 如果没有指定日期范围，从3年前开始
            if end_date is None:
                end_date = date.today()

            # 获取历史数据
            records = await self.data_source.get_daily(
                stock_code=stock_code,
                start_date=start_date or date(end_date.year - 3, end_date.month, end_date.day),
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
                    'message': 'No data available'
                }

            # 质量校验
            quality_result = await self.quality_service.batch_validate(records)

            # 只插入通过校验的数据
            valid_records = [
                r for r, flag in zip(records, quality_result['quality_flags'])
                if flag == 'good'
            ]

            if valid_records:
                # 转换为字典格式
                record_dicts = [r.model_dump() for r in valid_records]
                # 转换 date 为字符串
                for d in record_dicts:
                    if 'trade_date' in d and isinstance(d['trade_date'], date):
                        d['trade_date'] = d['trade_date'].isoformat()
                await self.storage.insert('stock_daily', record_dicts)

            self.mark_sync_end(stock_code, success=True)

            return {
                'stock_code': stock_code,
                'total_records': len(records),
                'success_count': quality_result['passed'],
                'failed_count': quality_result['failed'],
                'status': 'success',
                'quality_flags': quality_result['quality_flags']
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
