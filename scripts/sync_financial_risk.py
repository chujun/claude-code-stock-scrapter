#!/usr/bin/env python3
"""同步同花顺财务风险数据脚本"""

import asyncio
import logging
import sys
from datetime import date
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_source.ths_client import THSClient
from storage.clickhouse_repo import ClickHouseRepository
from config.settings import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 测试股票列表（10只）
TEST_STOCKS = [
    "600000",  # 浦发银行
    "000001",  # 平安银行
    "600036",  # 招商银行
    "600519",  # 贵州茅台
    "000858",  # 五粮液
    "601318",  # 中国平安
    "000333",  # 美的集团
    "002594",  # 比亚迪
    "300750",  # 宁德时代
    "688981",  # 中芯国际
]


async def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始同步同花顺财务风险数据")
    logger.info("=" * 60)

    # 初始化组件
    settings = get_settings()
    repo = ClickHouseRepository(config=settings.clickhouse)
    ths_client = THSClient(
        headless=True,
        timeout=30000,
        rate_limit_interval=2.0  # 2秒间隔
    )

    # 去重股票列表
    unique_stocks = list(set(TEST_STOCKS))
    logger.info(f"待同步股票数量: {len(unique_stocks)}")
    logger.info(f"股票列表: {unique_stocks}")

    success_count = 0
    fail_count = 0
    total_records = 0

    try:
        # 同步每只股票
        for i, stock_code in enumerate(unique_stocks, 1):
            logger.info(f"[{i}/{len(unique_stocks)}] 正在同步 {stock_code}...")
            try:
                # 获取财务风险数据
                risk_data = await ths_client.get_financial_risk(stock_code)

                if risk_data:
                    # 转换为字典并存储
                    records = [r.model_dump() for r in risk_data]
                    inserted = await repo.upsert(
                        table="stock_financial_risk",
                        records=records,
                        unique_keys=["stock_code", "trade_date"]
                    )
                    success_count += 1
                    total_records += inserted
                    logger.info(f"  ✓ {stock_code} 同步成功，记录数: {inserted}")
                    for r in risk_data:
                        logger.info(f"    - 日期: {r.trade_date}, 总风险: {r.total_risk}, 无风险: {r.no_risk}, 低风险: {r.low_risk}, 中风险: {r.medium_risk}, 高风险: {r.high_risk}")
                else:
                    fail_count += 1
                    logger.warning(f"  ⚠ {stock_code} 无数据")

            except Exception as e:
                fail_count += 1
                logger.error(f"  ✗ {stock_code} 异常: {str(e)}")

            # 间隔2秒
            if i < len(unique_stocks):
                await asyncio.sleep(2)

        logger.info("=" * 60)
        logger.info(f"同步完成: 成功 {success_count}, 失败 {fail_count}, 总记录 {total_records}")
        logger.info("=" * 60)

    finally:
        # 关闭资源
        await ths_client.close()
        repo.close()


if __name__ == "__main__":
    asyncio.run(main())
