#!/usr/bin/env python3
"""
全量股票数据同步脚本
抓取全量股票最近一个月的数据入库
"""

import asyncio
import sys
import time
import logging
import logging.handlers
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_source.akshare_client import AkshareClient
from storage.clickhouse_repo import ClickHouseRepository
from services.quality_service import QualityService
from services.sync_service import StockSyncService, SyncStrategy
from config.settings import get_settings

# 配置日志 - 输出到/data路径，包含应用名称，支持日志滚动
APP_NAME = "stock-scraper"
log_dir = Path("/data/logs") / APP_NAME
log_dir.mkdir(parents=True, exist_ok=True)

# 主日志格式
main_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# 文件日志 - 同步进度日志（支持滚动）
progress_file_handler = logging.handlers.TimedRotatingFileHandler(
    filename=log_dir / "sync.log",
    when="midnight",
    interval=1,
    backupCount=7,
    encoding="utf-8"
)
progress_file_handler.setFormatter(main_formatter)
progress_file_handler.setLevel(logging.INFO)

# 详细日志 - API请求/响应和每日期同步详情（单独文件）
detail_file_handler = logging.handlers.TimedRotatingFileHandler(
    filename=log_dir / "detail.log",
    when="midnight",
    interval=1,
    backupCount=7,
    encoding="utf-8"
)
detail_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
detail_file_handler.setLevel(logging.INFO)

# 控制台日志 - 进度显示
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(
    '\r%(asctime)s - %(message)s'
))

# 配置根日志
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers.clear()
root_logger.addHandler(progress_file_handler)
root_logger.addHandler(console_handler)

# 配置详细日志logger（API和每日期详情）
detail_logger = logging.getLogger("stock-scraper.detail")
detail_logger.setLevel(logging.INFO)
detail_logger.addHandler(detail_file_handler)

# 配置API日志logger
api_logger = logging.getLogger("stock-scraper.api")
api_logger.setLevel(logging.INFO)
api_logger.addHandler(detail_file_handler)

logger = logging.getLogger(__name__)


class FullBatchSync:
    """全量股票批量同步"""

    def __init__(self, days: int = 30, strategy: SyncStrategy = SyncStrategy.OVERWRITE):
        self.settings = get_settings()
        self.data_source = AkshareClient()
        self.storage = ClickHouseRepository(self.settings.clickhouse)
        self.quality = QualityService(self.settings)
        self.service = StockSyncService(
            data_source=self.data_source,
            storage=self.storage,
            quality_service=self.quality
        )
        self.days = days
        self.strategy = strategy
        self.start_date = date.today() - timedelta(days=days)
        self.end_date = date.today()

        # 统计
        self.total = 0
        self.success = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []

    async def get_stock_list(self) -> list:
        """获取股票列表"""
        logger.info("获取股票列表...")
        stocks = await self.data_source.get_stock_list()
        self.total = len(stocks)
        logger.info(f"获取到 {self.total} 只股票")
        return stocks

    async def sync_stock(self, stock_code: str) -> dict:
        """同步单只股票"""
        try:
            result = await self.service.sync_single_stock(
                stock_code,
                start_date=self.start_date,
                end_date=self.end_date,
                strategy=self.strategy
            )

            # 记录每只股票同步结果到主日志
            if result.get('status') == 'success':
                total = result.get('total_records', 0)
                inserted = result.get('success_count', 0)
                failed = result.get('failed_count', 0)
                if inserted > 0:
                    logger.info(f"[{stock_code}] 同步成功: {inserted}/{total} 条 (失败: {failed})")
                else:
                    logger.info(f"[{stock_code}] 无新数据: {result.get('message', 'skipped')}")
            else:
                logger.error(f"[{stock_code}] 同步失败: {result.get('error', 'Unknown error')}")

            return {
                'code': stock_code,
                'success_count': result.get('success_count', 0),
                'failed_count': result.get('failed_count', 0),
                'status': 'success'
            }
        except Exception as e:
            logger.error(f"[{stock_code}] 同步异常: {type(e).__name__}: {str(e)}")
            return {
                'code': stock_code,
                'success': 0,
                'warning': 0,
                'error': 1,
                'status': 'failed',
                'error_msg': str(e)[:100]
            }

    async def run(self, limit: int = None, offset: int = 0):
        """执行全量同步

        Args:
            limit: 限制数量（用于测试），None表示全部
            offset: 起始偏移
        """
        logger.info(f"=" * 60)
        logger.info(f"全量股票数据同步")
        logger.info(f"=" * 60)
        logger.info(f"日期范围: {self.start_date} ~ {self.end_date}")
        logger.info(f"同步策略: {self.strategy.value}")
        logger.info(f"限流间隔: {self.data_source.rate_limiter.base_interval}s")
        logger.info(f"=" * 60)

        # 获取股票列表
        stocks = await self.get_stock_list()

        # 同步股票基本信息
        logger.info(f"开始同步股票基本信息...")
        info_result = await self.service.sync_stock_info(stocks)
        logger.info(f"股票基本信息同步完成: 成功 {info_result.get('success_count', 0)} 条")
        if info_result.get('status') == 'failed':
            logger.warning(f"股票基本信息同步失败: {info_result.get('error', 'Unknown error')}")

        # 限制数量
        if limit:
            stocks = stocks[offset:offset + limit]
            logger.info(f"测试模式: 只同步 {len(stocks)} 只股票")

        total_to_sync = len(stocks)
        logger.info(f"待同步: {total_to_sync} 只股票")
        logger.info(f"预计耗时: {total_to_sync * self.data_source.rate_limiter.base_interval / 60:.1f} 分钟")
        logger.info(f"=" * 60)

        # 开始同步
        start_time = time.time()
        success_count = 0
        failed_count = 0
        warning_count = 0

        for i, stock in enumerate(stocks):
            stock_code = stock.stock_code

            # 同步
            result = await self.sync_stock(stock_code)

            # 统计
            if result['status'] == 'success':
                success_count += result['success_count']
                if result['success_count'] > 0:
                    self.success += 1
                else:
                    self.skipped += 1
            else:
                failed_count += 1
                self.failed += 1
                self.errors.append(f"{stock_code}: {result.get('error_msg', 'Unknown error')}")

            # 进度输出
            if (i + 1) % 50 == 0 or (i + 1) == total_to_sync:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                remaining = (total_to_sync - i - 1) / rate if rate > 0 else 0

                logger.info(
                    f"进度: {i + 1}/{total_to_sync} "
                    f"({(i + 1) / total_to_sync * 100:.1f}%) | "
                    f"成功: {self.success} | "
                    f"失败: {self.failed} | "
                    f"跳过: {self.skipped} | "
                    f"剩余: {remaining / 60:.1f}分钟"
                )

        # 最终统计
        elapsed = time.time() - start_time

        logger.info(f"=" * 60)
        logger.info(f"全量同步完成")
        logger.info(f"=" * 60)
        logger.info(f"总耗时: {elapsed / 60:.1f} 分钟")
        logger.info(f"成功股票: {self.success}")
        logger.info(f"失败股票: {self.failed}")
        logger.info(f"跳过股票: {self.skipped}")
        logger.info(f"总记录: {success_count}")
        logger.info(f"=" * 60)

        # 显示错误
        if self.errors:
            logger.info(f"错误列表 (前10条):")
            for err in self.errors[:10]:
                logger.info(f"  - {err}")

        return {
            'total': total_to_sync,
            'success': self.success,
            'failed': self.failed,
            'skipped': self.skipped,
            'records': success_count
        }

    def close(self):
        """关闭连接"""
        self.storage.close()


async def main():
    import argparse

    parser = argparse.ArgumentParser(description='全量股票数据同步')
    parser.add_argument('--limit', type=int, default=None, help='限制数量（用于测试）')
    parser.add_argument('--offset', type=int, default=0, help='起始偏移')
    parser.add_argument('--days', type=int, default=30, help='抓取天数')
    parser.add_argument(
        '--strategy',
        type=str,
        choices=['skip', 'overwrite', 'incremental'],
        default='overwrite',
        help='同步策略: skip=跳过已存在, overwrite=覆盖, incremental=增量(默认)'
    )
    args = parser.parse_args()

    strategy = SyncStrategy(args.strategy)
    sync = FullBatchSync(days=args.days, strategy=strategy)
    try:
        result = await sync.run(limit=args.limit, offset=args.offset)
        return result
    finally:
        sync.close()


if __name__ == '__main__':
    asyncio.run(main())
