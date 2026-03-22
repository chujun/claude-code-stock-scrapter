# tasks/verification_task.py
"""数据验证任务"""

from typing import Any, Dict, List, Optional
from datetime import date

from tasks.base import BaseTask
from services.sync_service import StockSyncService
from storage.base import BaseRepository
from services.quality_service import QualityService
from models.stock_daily import StockDaily


class VerificationTask(BaseTask):
    """数据验证任务

    负责验证已同步数据的完整性和质量
    """

    def __init__(
        self,
        sync_service: StockSyncService,
        storage: BaseRepository,
        stock_list: Optional[List[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ):
        """初始化验证任务

        Args:
            sync_service: 同步服务
            storage: 存储库
            stock_list: 股票代码列表（None表示验证所有）
            start_date: 开始日期
            end_date: 结束日期
        """
        super().__init__(task_name='verification', sync_service=sync_service, storage=storage)
        self.stock_list = stock_list
        self.start_date = start_date
        self.end_date = end_date

        # 验证日期范围
        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date must be <= end_date")

        self.quality_service = QualityService()

    async def execute(self) -> Dict[str, Any]:
        """执行数据验证

        Returns:
            Dict: 验证结果统计
        """
        # 如果没有指定股票列表，从存储获取所有活跃股票
        stock_list = self.stock_list
        if stock_list is None:
            stock_list = await self._get_active_stocks()

        if not stock_list:
            return {
                'total': 0,
                'verified': 0,
                'issues': [],
                'message': 'No stocks to verify'
            }

        total_issues = []
        verified_count = 0

        for stock_code in stock_list:
            issues = await self._verify_stock(stock_code)
            if not issues:
                verified_count += 1
            total_issues.extend(issues)

        return {
            'total': len(stock_list),
            'verified': verified_count,
            'issues': total_issues,
            'issue_count': len(total_issues)
        }

    async def _verify_stock(self, stock_code: str) -> List[Dict[str, Any]]:
        """验证单只股票的数据

        Args:
            stock_code: 股票代码

        Returns:
            List[Dict]: 问题列表
        """
        issues = []

        try:
            # 查询该股票的数据
            start_date_str = self.start_date.isoformat() if self.start_date else '1970-01-01'
            end_date_str = self.end_date.isoformat() if self.end_date else date.today().isoformat()

            query = """
                SELECT * FROM stock_daily
                WHERE stock_code = %(stock_code)s
                AND trade_date BETWEEN %(start_date)s AND %(end_date)s
                ORDER BY trade_date
            """

            records = await self.storage.query(query, {
                'stock_code': stock_code,
                'start_date': start_date_str,
                'end_date': end_date_str
            })

            if not records:
                issues.append({
                    'stock_code': stock_code,
                    'issue_type': 'no_data',
                    'message': f'No data found for {stock_code}'
                })
                return issues

            # 转换为StockDaily对象进行质量校验
            stock_daily_list = []
            for r in records:
                try:
                    stock_daily = StockDaily.model_construct(**r)
                    stock_daily_list.append(stock_daily)
                except Exception:
                    issues.append({
                        'stock_code': stock_code,
                        'issue_type': 'parse_error',
                        'message': f'Failed to parse record for {stock_code}'
                    })

            # 批量质量校验
            if stock_daily_list:
                quality_result = await self.quality_service.batch_validate(stock_daily_list)

                # 检查失败记录
                for i, flag in enumerate(quality_result['quality_flags']):
                    if flag != 'good':
                        record = stock_daily_list[i]
                        issues.append({
                            'stock_code': stock_code,
                            'issue_type': 'quality_failed',
                            'trade_date': str(record.trade_date),
                            'message': f'Quality check failed for {stock_code} on {record.trade_date}'
                        })

            # 检查数据完整性（连续交易日）
            issues.extend(self._check_continuity(stock_code, records))

        except Exception as e:
            issues.append({
                'stock_code': stock_code,
                'issue_type': 'verification_error',
                'message': f'Verification error: {str(e)}'
            })

        return issues

    def _check_continuity(self, stock_code: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检查数据连续性

        Args:
            stock_code: 股票代码
            records: 数据记录列表

        Returns:
            List[Dict]: 问题列表
        """
        from datetime import datetime

        issues = []

        if len(records) < 2:
            return issues

        # 按日期排序
        sorted_records = sorted(records, key=lambda x: x['trade_date'])

        # 检查相邻记录是否是连续交易日
        for i in range(len(sorted_records) - 1):
            current_date = datetime.strptime(sorted_records[i]['trade_date'], '%Y-%m-%d').date()
            next_date = datetime.strptime(sorted_records[i + 1]['trade_date'], '%Y-%m-%d').date()

            # 排除周末
            days_diff = (next_date - current_date).days
            if days_diff > 3:  # 超过3个自然日不是连续交易日
                issues.append({
                    'stock_code': stock_code,
                    'issue_type': 'missing_trading_day',
                    'from_date': str(current_date),
                    'to_date': str(next_date),
                    'message': f'Missing trading days between {current_date} and {next_date} for {stock_code}'
                })

        return issues

    async def _get_active_stocks(self) -> List[str]:
        """获取所有活跃股票代码

        Returns:
            List[str]: 股票代码列表
        """
        try:
            # 从stock_info表获取活跃股票代码
            result = await self.storage.query(
                "SELECT stock_code FROM stock_info WHERE is_active = 1"
            )
            return [r['stock_code'] for r in result]
        except Exception:
            return []
