# services/financial_risk_service.py
"""财务风险同步服务"""

import asyncio
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from models.stock_financial_risk import StockFinancialRisk
from storage.base import BaseRepository


logger = logging.getLogger(__name__)


class FinancialRiskService:
    """财务风险同步服务

    负责从同花顺爬取财务风险数据并存储到ClickHouse
    """

    def __init__(
        self,
        repo: BaseRepository,
        playwright_client: Any  # THSClient
    ):
        """初始化服务

        Args:
            repo: 数据存储库
            playwright_client: 同花顺爬虫客户端
        """
        self.repo = repo
        self.client = playwright_client

    async def sync_stock(self, stock_code: str) -> Dict[str, Any]:
        """同步单只股票的财务风险数据

        Args:
            stock_code: 股票代码

        Returns:
            Dict: 包含同步结果的字典
        """
        result = {
            "stock_code": stock_code,
            "status": "success",
            "records_synced": 0,
            "error_message": None
        }

        try:
            # 爬取数据
            risk_data = await self.client.get_financial_risk(stock_code)

            if not risk_data:
                logger.info(f"No risk data for {stock_code}")
                return result

            # 转换为字典
            records = [r.model_dump() for r in risk_data]

            # 存储到数据库
            inserted = await self.repo.upsert(
                table="stock_financial_risk",
                records=records,
                unique_keys=["stock_code", "trade_date"]
            )

            result["records_synced"] = inserted
            logger.info(f"Synced {inserted} risk records for {stock_code}")

        except Exception as e:
            result["status"] = "failed"
            result["error_message"] = str(e)
            logger.error(f"Failed to sync risk data for {stock_code}: {e}")

        return result

    async def sync_stocks(self, stock_codes: List[str]) -> List[Dict[str, Any]]:
        """批量同步多只股票的财务风险数据

        Args:
            stock_codes: 股票代码列表

        Returns:
            List[Dict]: 每个股票的同步结果
        """
        results = []

        for stock_code in stock_codes:
            result = await self.sync_stock(stock_code)
            results.append(result)

            # 添加延迟，避免请求过快
            await asyncio.sleep(0.5)

        return results

    async def sync_all(
        self,
        stock_codes: Optional[List[str]] = None,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """同步所有或指定股票的财务风险数据

        Args:
            stock_codes: 股票代码列表，None表示从数据库获取所有股票
            max_concurrent: 最大并发数

        Returns:
            Dict: 同步汇总结果
        """
        start_time = datetime.now()

        if stock_codes is None:
            # 从数据库获取所有股票代码
            stock_codes = await self._get_all_stock_codes()

        total = len(stock_codes)
        success = 0
        failed = 0
        total_records = 0
        errors = []

        # 分批并发执行
        for i in range(0, total, max_concurrent):
            batch = stock_codes[i:i + max_concurrent]
            batch_results = await self.sync_stocks(batch)

            for r in batch_results:
                if r["status"] == "success":
                    success += 1
                    total_records += r["records_synced"]
                else:
                    failed += 1
                    if r.get("error_message"):
                        errors.append(f"{r['stock_code']}: {r['error_message']}")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return {
            "total_stocks": total,
            "success_count": success,
            "failed_count": failed,
            "total_records": total_records,
            "duration_seconds": duration,
            "errors": errors[:10]  # 最多记录10个错误
        }

    async def _get_all_stock_codes(self) -> List[str]:
        """从数据库获取所有股票代码"""
        try:
            result = await self.repo.query(
                "SELECT DISTINCT stock_code FROM stock_info WHERE status = 'active'"
            )
            return [row["stock_code"] for row in result]
        except Exception as e:
            logger.error(f"Failed to get stock codes: {e}")
            return []

    async def close(self) -> None:
        """关闭服务，释放资源"""
        if self.client:
            await self.client.close()
