# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

A股股票数据爬虫系统 - 从AKShare获取A股数据，存储到ClickHouse。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

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

# 小批量同步测试
python scripts/small_batch_sync.py
```

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

### 配置

- `config.yaml` - YAML配置文件
- `config/settings.py` - Pydantic Settings加载配置
- 环境变量 `CONFIG_PATH` 可指定配置文件路径

### 复权类型

数据支持三种复权类型: `qfq`(前复权)、`hfq`(后复权)、`none`(不复权)，默认使用前复权。

### 质量校验

QualityService对涨跌幅进行校验，异常值标记为warn/error，默认阈值为±10%(ST股±20%)。
