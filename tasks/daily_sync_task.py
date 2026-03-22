# tasks/daily_sync_task.py
"""每日增量同步任务"""

from typing import Any, Dict, List, Optional
from datetime import date, timedelta

from tasks.base import BaseTask
from services.sync_service import StockSyncService
from storage.base import BaseRepository


class DailySyncTask(BaseTask):
    """每日增量同步任务

    负责同步今日最新数据（增量同步）
    """

    def __init__(
        self,
        sync_service: StockSyncService,
        storage: BaseRepository,
        stock_list: Optional[List[str]] = None
    ):
        """初始化每日同步任务

        Args:
            sync_service: 同步服务
            storage: 存储库
            stock_list: 股票代码列表（None表示同步所有）
        """
        super().__init__(task_name='daily_sync', sync_service=sync_service, storage=storage)
        self.stock_list = stock_list

    async def execute(self) -> Dict[str, Any]:
        """执行每日增量同步

        Returns:
            Dict: 同步结果统计
        """
        # 如果没有指定股票列表，从存储获取所有活跃股票
        stock_list = self.stock_list
        if stock_list is None:
            stock_list = await self._get_active_stocks()

        if not stock_list:
            return {
                'total': 0,
                'success_count': 0,
                'failed_count': 0,
                'results': [],
                'message': 'No stocks to sync'
            }

        # 增量同步：只同步最近几天（覆盖可能的补休交易日）
        today = date.today()
        start_date = today - timedelta(days=7)
        end_date = today

        # 使用同步服务批量同步
        result = await self.sync_service.batch_sync(
            stock_codes=stock_list,
            start_date=start_date,
            end_date=end_date
        )

        return result

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
