# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

A股股票数据爬虫系统 - 从AKShare获取A股数据，存储到ClickHouse。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库（首次运行前必须执行）
clickhouse-client --multiquery < storage/migrations/init.sql

# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/unit/test_sync_service.py

# 运行单个测试函数
pytest tests/unit/test_sync_service.py::test_batch_sync

# 运行带覆盖率
pytest --cov=. --cov-report=term-missing

# 代码检查
ruff check .
mypy .

# 小批量同步测试（开发环境）
python scripts/small_batch_sync.py

# 全量同步（生产环境）
python scripts/full_batch_sync.py

# 指定数量测试同步
python scripts/full_batch_sync.py --limit 10 --offset 0 --days 30 --strategy skip
```

## 日志

日志输出到 `/data/logs/stock-scraper/` 目录：
- `sync.log` - 同步进度日志（滚动）
- `detail.log` - API请求/响应和每日期同步详情（滚动）
- 告警输出到 `/data/logs/alerts.log`

## 架构

```
akshare (数据源)
    ↓
data_source/akshare_client.py  (异步封装 + 限流)
    ↓
models/ (Pydantic模型)
    ↓
services/sync_service.py  (业务编排 + 质量校验)
    ↓
storage/clickhouse_repo.py  (ClickHouse存储)
```

### 分层说明

- **data_source**: 通过akshare库获取数据，封装为异步接口，包含限流器(RateLimiter)防止请求过快
- **models**: Pydantic模型定义数据结构，使用date类型存储日期
- **services**: 业务逻辑层，StockSyncService编排数据流，QualityService做数据质量校验
- **storage**: ClickHouse访问层，使用ReplacingMergeTree引擎表，自动去重
- **tasks**: 任务层，FullSyncTask/DailySyncTask实现不同同步策略

### ClickHouse表结构

| 表名 | 用途 | 引擎 |
|------|------|------|
| stock_info | 股票基本信息 | ReplacingMergeTree |
| stock_daily | 日线行情 | ReplacingMergeTree |
| sync_status | 同步状态 | ReplacingMergeTree |
| sync_error | 错误日志 | MergeTree |
| sync_report | 同步报告 | MergeTree |
| daily_index | 指数数据 | ReplacingMergeTree |
| stock_split | 分红送股 | MergeTree |

### 同步策略

支持三种同步策略，通过 `--strategy` 参数控制：

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| `skip` | 已存在的日期完全跳过，最快 | 首次同步后快速检查 |
| `overwrite` | 覆盖所有数据（默认） | 数据可能有修正 |
| `incremental` | 只同步新增日期 | 日常增量同步（推荐） |

```bash
# 跳过已存在（最快，适合恢复中断）
python scripts/full_batch_sync.py --strategy skip

# 增量同步（推荐日常使用）
python scripts/full_batch_sync.py --strategy incremental

# 全量同步
python scripts/full_batch_sync.py --strategy overwrite
```

### 配置

- `config.yaml` - YAML配置文件（配置优先级高于环境变量）
- `config/settings.py` - Pydantic Settings加载配置
- 环境变量 `CONFIG_PATH` 可指定配置文件路径

### 复权类型

数据支持三种复权类型: `qfq`(前复权)、`hfq`(后复权)、`none`(不复权)，默认使用前复权。

### 质量校验

QualityService对涨跌幅进行校验，异常值标记为warn/error，默认阈值为±10%(ST股±20%)。

### 北交所股票

北交所股票代码以8开头，同步时会自动从新浪财经获取数据。

### 数据库初始化

首次使用需执行数据库初始化脚本:
```bash
clickhouse-client --multiquery < storage/migrations/init.sql
```
