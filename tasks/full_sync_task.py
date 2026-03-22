# tasks/full_sync_task.py
"""全量同步任务"""

from typing import Any, Dict, List, Optional
from datetime import date

from tasks.base import BaseTask
from services.sync_service import StockSyncService
from storage.base import BaseRepository


class FullSyncTask(BaseTask):
    """全量同步任务

    负责全量同步所有股票的历史数据
    """

    def __init__(
        self,
        sync_service: StockSyncService,
        storage: BaseRepository,
        stock_list: Optional[List[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ):
        """初始化全量同步任务

        Args:
            sync_service: 同步服务
            storage: 存储库
            stock_list: 股票代码列表（None表示同步所有）
            start_date: 开始日期
            end_date: 结束日期
        """
        super().__init__(task_name='full_sync', sync_service=sync_service, storage=storage)
        self.stock_list = stock_list
        self.start_date = start_date
        self.end_date = end_date

    async def execute(self) -> Dict[str, Any]:
        """执行全量同步

        Returns:
            Dict: 同步结果统计
        """
        # 如果没有指定股票列表，从存储获取所有股票
        stock_list = self.stock_list
        if stock_list is None:
            stock_list = await self._get_all_stocks()

        if not stock_list:
            return {
                'total': 0,
                'success_count': 0,
                'failed_count': 0,
                'results': [],
                'message': 'No stocks to sync'
            }

        # 使用同步服务批量同步
        result = await self.sync_service.batch_sync(
            stock_codes=stock_list,
            start_date=self.start_date,
            end_date=self.end_date
        )

        return result

    async def _get_all_stocks(self) -> List[str]:
        """获取所有股票代码

        Returns:
            List[str]: 股票代码列表
        """
        try:
            # 从stock_info表获取所有股票代码
            result = await self.storage.query(
                "SELECT stock_code FROM stock_info WHERE is_active = 1"
            )
            return [r['stock_code'] for r in result]
        except Exception:
            return []
