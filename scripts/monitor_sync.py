#!/usr/bin/env python3
"""数据库同步监控脚本

每分钟监控股票日线数据同步情况，分析异常数据
"""

import sys
import time
from datetime import datetime, date
from collections import defaultdict

# 添加项目根目录到路径
sys.path.insert(0, '/root/ai/claudecode/first/stock-scraper')

try:
    from clickhouse_driver import Client
except ImportError:
    print("错误: 需要安装 clickhouse-driver")
    print("  pip install clickhouse-driver")
    sys.exit(1)


def get_client():
    """获取ClickHouse客户端"""
    return Client(
        host='localhost',
        port=9000,
        database='stock_scraper',
        user='default',
        password='',
        connect_timeout=10
    )


def monitor_sync():
    """监控同步进度"""
    print("=" * 80)
    print(f"股票日线数据同步监控")
    print(f"监控时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    try:
        client = get_client()

        # 1. 获取股票总数和已同步数量
        print("\n【1. 同步进度统计】")

        # 股票总数
        total_stocks_result = client.execute("SELECT COUNT(DISTINCT stock_code) FROM stock_info")
        total_stocks = total_stocks_result[0][0] if total_stocks_result else 0
        print(f"  股票总数: {total_stocks}")

        # 今日同步的股票数
        today = date.today().strftime('%Y-%m-%d')
        synced_today_result = client.execute("""
            SELECT COUNT(DISTINCT stock_code)
            FROM stock_daily
            WHERE toDate(trade_date) = today()
        """)
        synced_today = synced_today_result[0][0] if synced_today_result else 0
        print(f"  今日已同步股票数: {synced_today}")

        # 日线数据总记录数
        total_records_result = client.execute("SELECT COUNT(*) FROM stock_daily")
        total_records = total_records_result[0][0] if total_records_result else 0
        print(f"  日线数据总记录数: {total_records:,}")

        # 2. 按年份统计记录数分布
        print("\n【2. 数据年份分布】")
        year_stats = client.execute("""
            SELECT
                toYear(trade_date) as year,
                COUNT(*) as count,
                COUNT(DISTINCT stock_code) as stock_count
            FROM stock_daily
            GROUP BY toYear(trade_date)
            ORDER BY year DESC
            LIMIT 20
        """)

        print(f"  {'年份':<8} {'记录数':<15} {'股票数':<10}")
        print(f"  {'-'*35}")
        for row in year_stats:
            year, count, stock_count = row
            print(f"  {year:<8} {count:<15,} {stock_count:<10,}")

        # 3. 检查数据质量 - 涨跌幅异常
        print("\n【3. 数据质量检查 - 涨跌幅异常】")

        # 涨跌幅 > 20% 或 < -20% 的记录
        extreme_changes = client.execute("""
            SELECT
                stock_code,
                trade_date,
                change_pct,
                close,
                pre_close
            FROM stock_daily
            WHERE abs(change_pct) > 20
            ORDER BY abs(change_pct) DESC
            LIMIT 20
        """)

        if extreme_changes:
            print(f"  发现 {len(extreme_changes)} 条涨跌幅异常记录 (>20%):")
            print(f"  {'股票代码':<10} {'日期':<12} {'涨跌幅':<10} {'收盘价':<12} {'前收盘':<12}")
            print(f"  {'-'*56}")
            for row in extreme_changes[:10]:
                stock_code, trade_date, change_pct, close, pre_close = row
                print(f"  {stock_code:<10} {str(trade_date):<12} {change_pct:>8.2f}% {close:>10.2f} {pre_close:>10.2f}")
        else:
            print("  未发现涨跌幅异常记录")

        # 4. 检查停牌股票（连续交易日无波动）
        print("\n【4. 检查异常数据】")

        # 成交量为0的记录
        zero_volume = client.execute("""
            SELECT COUNT(*) FROM stock_daily WHERE volume = 0
        """)
        print(f"  成交量为0的记录数: {zero_volume[0][0]:,}")

        # 价格为0的记录
        zero_price = client.execute("""
            SELECT COUNT(*) FROM stock_daily WHERE close = 0 OR open = 0 OR high = 0 OR low = 0
        """)
        print(f"  价格为0的记录数: {zero_price[0][0]:,}")

        # 5. 最新同步的股票
        print("\n【5. 最新同步的股票】")
        latest_sync = client.execute("""
            SELECT
                stock_code,
                MAX(trade_date) as latest_date,
                COUNT(*) as record_count
            FROM stock_daily
            WHERE toDate(trade_date) >= today() - 7
            GROUP BY stock_code
            ORDER BY latest_date DESC
            LIMIT 10
        """)

        print(f"  {'股票代码':<10} {'最新日期':<12} {'记录数':<10}")
        print(f"  {'-'*34}")
        for row in latest_sync:
            stock_code, latest_date, record_count = row
            print(f"  {stock_code:<10} {str(latest_date):<12} {record_count:<10,}")

        # 6. 预估完成时间
        print("\n【6. 完成时间预估】")
        if synced_today > 0:
            remaining = total_stocks - synced_today
            avg_time_per_stock = 60  # 假设每只股票约1秒
            remaining_seconds = remaining * avg_time_per_stock
            remaining_hours = remaining_seconds / 3600
            print(f"  剩余股票数: {remaining}")
            print(f"  预估剩余时间: {remaining_hours:.1f} 小时")
        else:
            print("  等待同步开始...")

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\n监控出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行一次监控
    monitor_sync()
