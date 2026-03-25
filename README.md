# A股股票数据爬虫系统

从AKShare获取A股数据，存储到ClickHouse的异步爬虫系统。

## 功能特性

- **异步数据获取**：基于asyncio + aiohttp，支持高并发请求
- **ClickHouse存储**：使用ReplacingMergeTree引擎表，自动去重
- **数据质量校验**：涨跌幅异常检测，OHLC关系校验
- **多种同步策略**：skip/overwrite/incremental三种模式
- **断点续传**：基于sync_status表实现
- **定时任务**：APScheduler每日16:00自动增量同步

## 环境要求

- Python 3.9+
- ClickHouse
- 网络连接到AKShare数据源

## 安装

```bash
# 克隆项目
git clone <repository-url>
cd stock-scraper

# 安装依赖
pip install -r requirements.txt

# 初始化数据库（首次运行前必须执行）
clickhouse-client --multiquery < storage/migrations/init.sql
```

## 配置

编辑 `config.yaml` 配置文件：

```yaml
clickhouse:
  host: "localhost"
  port: 9000
  database: "stock_scraper"
  user: "default"
  password: ""

data_source:
  name: "akshare"
  rate_limit:
    base_interval: 1.5  # 基础请求间隔(秒)

sync:
  batch_size: 1024  # 批量写入大小

scheduler:
  daily_sync_hour: 16  # 每日增量同步时间(时)
  daily_sync_minute: 0
  enabled: true
```

## 使用

### 小批量同步测试（开发环境）

```bash
python scripts/small_batch_sync.py
```

### 全量同步

```bash
# 增量同步（推荐日常使用）
python scripts/full_batch_sync.py --strategy incremental

# 全量覆盖
python scripts/full_batch_sync.py --strategy overwrite

# 跳过已存在（最快，适合恢复中断）
python scripts/full_batch_sync.py --strategy skip

# 指定数量测试
python scripts/full_batch_sync.py --limit 10 --offset 0 --days 30
```

### 同步策略说明

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| `skip` | 已存在的日期完全跳过，最快 | 首次同步后快速检查 |
| `overwrite` | 覆盖所有数据（默认） | 数据可能有修正 |
| `incremental` | 只同步新增日期 | 日常增量同步（推荐） |

### 参数说明

- `--limit N`：限制同步N只股票（用于测试）
- `--offset N`：从第N只股票开始
- `--days N`：抓取最近N天的数据
- `--strategy`：同步策略

## 测试

```bash
# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/unit/test_sync_service.py

# 运行单个测试函数
pytest tests/unit/test_sync_service.py::test_batch_sync

# 运行带覆盖率
pytest --cov=. --cov-report=term-missing
```

## 代码检查

```bash
ruff check .
mypy .
```

## 日志

日志输出到 `/data/logs/stock-scraper/` 目录：
- `sync.log` - 同步进度日志
- `detail.log` - API请求/响应详情
- `alerts.log` - 告警日志

## 项目结构

```
stock-scraper/
├── config/              # 配置管理
├── models/              # Pydantic数据模型
├── data_source/         # 数据源（akshare）
├── storage/             # ClickHouse存储
├── services/            # 业务逻辑
├── tasks/               # 任务调度
├── scripts/             # 入口脚本
├── tests/               # 测试
└── docs/                # 文档
```

## ClickHouse表

| 表名 | 用途 |
|------|------|
| stock_info | 股票基本信息 |
| stock_daily | 日线行情 |
| sync_status | 同步状态 |
| sync_error | 错误日志 |
| sync_report | 同步报告 |
| daily_index | 指数数据 |
| stock_split | 分红送股 |

## 文档

详细技术文档见 `docs/` 目录：
- `TECHNICAL.md` - 技术方案
- `stock_sync.md` - 同步详细设计
- `TASK_LIST.md` - 任务清单
- `CLICKHOUSE_STORAGE_MIGRATION_*.md` - ClickHouse存储迁移方案
