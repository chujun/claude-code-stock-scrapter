#!/usr/bin/env python3
"""小批量同步测试脚本 - 验证3-5只股票写入ClickHouse"""

import asyncio
import sys
from datetime import date, timedelta

sys.path.insert(0, '/root/ai/claudecode/first/stock-scraper')

from data_source.akshare_client import AkshareClient
from storage.clickhouse_repo import ClickHouseRepository
from services.sync_service import StockSyncService
from services.quality_service import QualityService


async def main():
    print("=" * 60)
    print("小批量同步测试 - 3-5只股票写入验证")
    print("=" * 60)

    # 初始化组件
    data_source = AkshareClient()
    storage = ClickHouseRepository()
    quality_service = QualityService()
    sync_service = StockSyncService(
        data_source=data_source,
        storage=storage,
        quality_service=quality_service
    )

    # 测试股票列表 (沪市1只, 深市2只, 创业板1只)
    test_stocks = ['600000', '000001', '300750', '688001']
    # 限制日期范围（最近30天）
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    print(f"\n测试股票: {test_stocks}")
    print(f"日期范围: {start_date} ~ {end_date}")
    print()

    # 执行同步
    results = await sync_service.batch_sync(
        stock_codes=test_stocks,
        start_date=start_date,
        end_date=end_date
    )

    # 输出结果
    print("\n" + "=" * 60)
    print("同步结果")
    print("=" * 60)
    print(f"总数: {results['total']}")
    print(f"成功: {results['success_count']}")
    print(f"失败: {results['failed_count']}")
    print()

    # 输出详细结果
    print("\n详细结果:")
    for r in results.get('results', []):
        status = r.get('status', 'unknown')
        code = r.get('stock_code', '?')
        error = r.get('error', '')
        print(f"  {code}: {status} {error if error else ''}")

    # 验证数据库写入
    print("=" * 60)
    print("数据库验证")
    print("=" * 60)

    for stock_code in test_stocks:
        query = """
            SELECT count() as cnt FROM stock_daily
            WHERE stock_code = %(stock_code)s
        """
        records = await storage.query(query, {'stock_code': stock_code})
        cnt = records[0]['cnt'] if records else 0
        print(f"  {stock_code}: {cnt} 条记录")

    # 统计总记录数
    total_query = "SELECT count() as total FROM stock_daily"
    total_result = await storage.query(total_query)
    total = total_result[0]['total'] if total_result else 0
    print(f"\nstock_daily表总记录: {total}")

    # 关闭连接
    storage.close()

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

    return results


if __name__ == '__main__':
    results = asyncio.run(main())
    sys.exit(0 if results['failed_count'] == 0 else 1)
