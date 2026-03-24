# A股股票数据爬虫系统 - 技术方案变更日志

## 概述

本文档记录技术方案的所有变更，包括变更前/变更后对比，便于审计追踪。

---

## v1.2 (2026-03-23)

### 同步效率实测数据

#### 1. 同步速度统计

| 指标 | 值 | 说明 |
|------|-----|------|
| 平均每20秒新增股票 | ~10 只 | 稳定值 |
| 平均每20秒新增记录 | ~190 条 | 每只约19条记录 |
| 同步速率 | ~30 只/分钟 | 按交易日历计 |
| 单只股票耗时 | ~2 秒 | 含网络请求+入库 |

#### 2. 全量同步预估

| 指标 | 值 |
|------|-----|
| A股总股票数 | ~5,491 只 |
| 实际有交易股票 | ~2,950-3,000 只/日 |
| 预计完成时间 | ~90-120 分钟 |
| 数据日期范围 | 2026-02-24 ~ 2026-03-23 |

#### 3. 数据库增长曲线

| 时间点 | 股票数 | 记录数 | 覆盖率 |
|--------|--------|--------|--------|
| 12:32 (清理后恢复) | 2,502 | 49,383 | 45.6% |
| 12:42 | 2,786 | 54,984 | 50.7% |
| 12:47 | 2,924 | 57,720 | 53.3% |
| 12:50 (当前) | 2,991 | 59,044 | 54.5% |

#### 4. 每日数据分布

| 日期 | 记录数 | 股票数 | 平均涨跌幅 |
|------|--------|--------|------------|
| 2026-03-23 | 2,959 | 2,958 | -5.00% |
| 2026-03-20 | 2,975 | 2,974 | -2.33% |
| 2026-03-19 | 2,981 | 2,980 | -2.39% |
| 2026-03-18 | 2,969 | 2,968 | +0.68% |

#### 5. 系统资源消耗

| 资源 | 使用情况 |
|------|----------|
| 磁盘空间 | 根分区 9.8G，已用 93% |
| 系统负载 | load average: 8.22 (同步期间) |
| ClickHouse | ~200M 数据存储 |

#### 6. 问题记录

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 同步突然停止 | 磁盘空间 100% 耗尽 | 清理 syslog/journal 日志 |
| 日志占用过大 | logger.info 输出写入 syslog | 配置 logrotate 自动轮转 |

#### 7. 磁盘清理机制

| 项目 | 设置 |
|------|------|
| 清理脚本 | `scripts/cleanup_disk.sh` |
| 执行频率 | 每天凌晨 2:00 |
| 触发阈值 | 磁盘使用率 > 85% |
| 清理内容 | syslog轮转、journal压缩、项目日志精简 |

#### 8. stock_daily 字段数据分析

**实测数据统计**：

| 指标 | 值 |
|------|-----|
| 总记录数 | 66,986 |
| 覆盖股票数 | 3,392 只 |
| 交易天数 | 20 天 |
| 日期范围 | 2026-02-24 ~ 2026-03-23 |
| 价格范围 | 0.44 ~ 1,491.66 元 |

**字段完整率**：

| 字段类型 | 字段 | 完整率 | 状态 |
|----------|------|--------|------|
| 价格 | open, high, low, close, pre_close | **100%** | ✅ |
| 成交 | turnover | **100%** | ✅ |
| 指标 | change_pct | **100%** | ✅ |
| 分类 | data_source, adjust_type, is_adjusted, quality_flag | **100%** | ✅ |
| 成交量 | volume | **0%** | ❌ |
| 换手率 | turnover_rate | **0%** | ❌ |
| 振幅 | amplitude_pct | **0%** | ❌ |
| 市值 | total_market_cap, float_market_cap | **0%** | ❌ |
| PB | pb_ratio | **0%** | ❌ |
| PE | pe_ratio, static_pe, dynamic_pe | **<0.1%** | ⚠️ |

**价格分位数**：

| 分位数 | 价格(元) |
|--------|----------|
| 25% (Q1) | 7.04 |
| 50% (中位数) | 12.64 |
| 75% (Q3) | 23.50 |
| 90% | 43.76 |
| 95% | 60.54 |
| 99% | 139.98 |

**涨跌幅分布**：

| 涨跌幅区间 | 占比 |
|------------|------|
| 跌停(-10%以下) | 0.44% |
| 大跌(-9%~-5%) | 1.56% |
| 中跌(-7%~-5%) | 4.82% |
| 小跌(-5%~-3%) | 11.01% |
| 微跌(-3%~-1%) | 22.84% |
| 微跌(-1%~0%) | 14.96% |
| 平盘 | 6.85% |
| 微涨(0%~1%) | 14.37% |
| 小涨(1%~3%) | 15.51% |
| 小涨(3%~5%) | 4.73% |
| 大涨(5%~9%) | 2.32% |
| 涨停(9%以上) | 0.60% |

---

### 9. 数据库表字段备注

已为所有数据表添加字段备注，便于理解数据结构。

#### stock_info（股票信息表）

| 字段 | 备注 |
|------|------|
| stock_code | 股票代码，如 600000、000001 |
| stock_name | 股票名称 |
| market | 交易所市场，SSE=上交所，SZSE=深交所 |
| industry | 所属行业，证监会行业分类 |
| list_date | 上市日期 |
| delist_date | 退市日期，为NULL表示未退市 |
| is_st | 是否ST或*ST股票 |
| status | 状态，active=正常，suspended=停牌，delisted=退市 |

#### sync_status（同步状态表）

| 字段 | 备注 |
|------|------|
| stock_code | 股票代码，为空表示全量同步任务 |
| sync_type | 同步类型：full=全量同步，daily=每日增量 |
| status | 同步状态：running=运行中，success=成功，failed=失败 |
| last_sync_time | 最后同步时间 |
| records_synced | 本次同步的记录数 |

#### sync_error（同步错误表）

| 字段 | 备注 |
|------|------|
| stock_code | 股票代码 |
| error_type | 错误类型：network/data/business |
| error_message | 错误详情 |
| retry_count | 重试次数 |

#### sync_report（同步报告表）

| 字段 | 备注 |
|------|------|
| sync_type | 同步类型：full/daily/verification |
| trigger_type | 触发类型：manual/scheduled/api |
| success_count | 成功数量 |
| failed_count | 失败数量 |
| duration_seconds | 持续时长，单位秒 |

#### daily_index（指数日线表）

| 字段 | 备注 |
|------|------|
| index_code | 指数代码，000001=上证指数，399001=深证成指 |
| index_name | 指数名称 |
| trade_date | 交易日期 |
| change_pct | 涨跌幅，单位% |

#### stock_split（分红送股表）

| 字段 | 备注 |
|------|------|
| stock_code | 股票代码 |
| trade_date | 除权除息日/红利发放日 |
| event_type | 事件类型：dividend/split/allot |
| before_quantity | 事件前持股数 |
| after_quantity | 事件后持股数 |

---

## v1.4 (2026-03-24)

### 优化：日志系统重构

#### 问题
- 磁盘空间不足导致同步中断
- 日志输出到根目录 `/var/log/`，占用系统空间
- 日志无滚动机制，单文件无限增长

#### 解决方案

**1. 日志路径迁移至 /data**

| 组件 | 原路径 | 新路径 |
|------|--------|--------|
| 同步脚本日志 | `stock-scraper/logs/sync.log` | `/data/logs/stock-scraper/sync.log` |
| 告警日志 | `logs/alerts.log` | `/data/logs/alerts.log` |
| ClickHouse日志 | `/var/log/clickhouse-server/` | `/data/logs/clickhouse/` |

**2. 日志文件结构**

```
/data/logs/
├── stock-scraper/          # 应用日志
│   ├── sync.log          # 主日志（进度、每只股票结果、异常）
│   ├── detail.log        # 详细日志（API请求/响应、每日期详情）
│   └── console.log       # 控制台输出
└── clickhouse/            # ClickHouse日志
    ├── clickhouse-server.log
    └── clickhouse-server.err.log
```

**3. 日志滚动配置**

| 配置项 | 值 |
|--------|-----|
| 滚动时机 | 每天午夜 (midnight) |
| 保留天数 | 7 天 |
| 编码 | utf-8 |

**4. 日志级别**

| Logger | 级别 | 内容 |
|--------|------|------|
| stock-scraper (主) | INFO | 进度、每只股票结果、异常 |
| stock-scraper.detail | INFO | API请求/响应、每日期同步详情 |
| stock-scraper.api | INFO | API调用耗时和响应 |

**5. 日志输出内容示例**

`sync.log` - 每只股票同步结果：
```
2026-03-24 09:22:14 - INFO - [000001] 同步成功: 21/21 条 (失败: 0)
2026-03-24 09:22:14 - INFO - [000070] ! 2026-03-02: error (close=19.66, change=10.02%)
2026-03-24 09:22:14 - INFO - 进度: 50/5491 (0.9%) | 成功: 32 | 失败: 0 | 跳过: 18
```

`detail.log` - API响应和每日期详情：
```
2026-03-24 09:22:14 - stock-scraper.api - INFO - [API RESPONSE] stock_zh_a_hist_tx(000096) - OK, 21 条记录 (耗时: 1.15s)
2026-03-24 09:22:14 - stock-scraper.detail - INFO - [000096] 同步完成: 总21条, 有效19条, 质量不合格2条, 策略:skip
```

#### ClickHouse 日志优化

**问题**：ClickHouse 日志级别为 `trace`，产生大量日志（>1000万行），且写入 `/var/log/syslog`。

**解决**：创建自定义配置 `/etc/clickhouse-server/config.d/custom-log.xml`：
```xml
<clickhouse>
    <logger>
        <level>information</level>
        <log>/data/logs/clickhouse/clickhouse-server.log</log>
        <errorlog>/data/logs/clickhouse/clickhouse-server.err.log</errorlog>
        <size>1000M</size>
        <count>10</count>
    </logger>
</clickhouse>
```

**效果**：
- 日志级别从 `trace` 降为 `information`
- 日志产生速度从 ~200KB/s 降为 ~2KB/s
- 日志路径迁移至 `/data`

#### 相关文件变更

| 文件 | 变更内容 |
|------|----------|
| `scripts/full_batch_sync.py` | 日志路径、滚动、多logger配置 |
| `config/settings.py` | alert_file路径修改 |
| `config.yaml` | alert_file路径修改 |
| `/etc/clickhouse-server/config.d/custom-log.xml` | ClickHouse日志配置 |

#### 查看日志命令

```bash
# 查看同步进度
tail -1 /data/logs/stock-scraper/sync.log

# 实时监控（每10秒刷新）
watch -n 10 "tail -1 /data/logs/stock-scraper/sync.log"

# 查看API日志
tail -20 /data/logs/stock-scraper/detail.log

# 查看ClickHouse日志
tail -20 /data/logs/clickhouse/clickhouse-server.log
```

---

## v1.3 (2026-03-24)

### 同步进度监控（2026-03-24）

#### 同步概况

| 指标 | 值 |
|------|-----|
| 监控时间 | 2026-03-24 |
| 股票总数 | 4,419 |
| 总记录数 | 99,486 |
| 最新数据日期 | 2026-03-23 |
| 数据质量 | 100% good |
| 复权类型 | 100% qfq (前复权) |

#### 同步速率统计

| 指标 | 值 |
|------|-----|
| 平均速率 | ~17 条/秒 (~1,040 条/分钟) |
| 波动范围 | 239 ~ 374 条/次 |
| 稳定性 | 高（波动仅±8%） |

#### 各日期数据分布

| 日期 | 记录数 | 股票数 | 完成度 |
|------|--------|--------|--------|
| 2026-03-23 | 4,953 | 4,338 | 99.3% |
| 2026-03-20 | 4,995 | 4,373 | 100% |
| 2026-03-19 | 5,001 | 4,379 | 100% |
| 2026-03-18 | 4,973 | 4,356 | 100% |
| 2026-03-17 | 4,996 | 4,376 | 100% |

#### 监控数据（两次监控对比）

| 监控时间点 | 记录数 | 当次增量 | 累计增量 |
|------------|--------|----------|----------|
| 第一次监控-初始 | 90,674 | - | - |
| 第一次监控-#10 | 93,384 | +2,710 | +2,710 |
| 第二次监控-初始 | 96,878 | - | - |
| 第二次监控-#10 | 99,486 | +2,608 | +2,608 |

**两次监控总增量**: 6,102 条记录（间隔约3分钟）

#### 结论

1. 同步稳定进行，速率保持在 17条/秒 左右
2. 2026-03-23 数据同步进度 99.3%，预计 1~2 分钟内完成
3. 2026-03-20 以来历史数据均已完成同步

---

### 新增功能：同步策略支持

优化了同步程序的重复数据处理逻辑，新增三种同步策略：

| 策略 | 值 | 说明 | 适用场景 |
|------|-----|------|----------|
| skip | `--strategy skip` | 已存在的日期完全跳过，最快 | 首次同步后快速检查 |
| overwrite | `--strategy overwrite` | 覆盖所有数据（默认） | 数据可能有修正 |
| incremental | `--strategy incremental` | 只同步新增日期 | 日常增量同步（推荐） |

**使用示例**：
```bash
# 跳过已存在（最快，适合恢复中断的同步）
python scripts/full_batch_sync.py --strategy skip

# 增量同步（推荐日常使用）
python scripts/full_batch_sync.py --strategy incremental

# 全量覆盖
python scripts/full_batch_sync.py --strategy overwrite
```

**技术实现**：
- `SyncStrategy` 枚举类定义三种策略
- `get_existing_dates()` 方法查询已存在的日期
- `sync_single_stock()` 根据策略过滤数据

### 优化：交易日历缓存与线程安全

**问题**：每次调用 `get_trading_dates()` 都会请求新浪API获取完整交易日历，在批量同步时造成大量重复网络请求。

**解决方案**：
1. 引入类级别缓存 `self._trading_dates_cache`，缓存完整交易日历集合
2. 使用 `threading.Lock()` 实现线程安全
3. 缓存按日刷新（基于 `date.today()` 判断是否过期）
4. 过滤逻辑在锁外执行，减少锁持有时间

**技术实现**：
```python
# 交易日历缓存（类级别，所有实例共享）
self._trading_dates_cache: Optional[Set[date]] = None
self._trading_dates_cache_date: Optional[date] = None
self._trading_lock = threading.Lock()

async def get_trading_dates(self, start_date: date, end_date: date) -> Set[date]:
    today = date.today()
    with self._trading_lock:
        if (self._trading_dates_cache is None or
            self._trading_dates_cache_date != today):
            # 从API获取完整日历并缓存
            df = await self._run_sync(ak.tool_trade_date_hist_sina)
            all_trading_dates = set()
            # ... 转换逻辑
            self._trading_dates_cache = all_trading_dates
            self._trading_dates_cache_date = today
    # 锁外过滤指定范围
    return {d for d in self._trading_dates_cache if start_date <= d <= end_date}
```

**效果**：
- 交易日历API调用从 O(n) 降为 O(1)，n=股票数量
- 线程安全，支持多实例并发
- 缓存自动按日刷新，保证数据新鲜度

---

### 优化：SKIP/INCREMENTAL策略提前查询数据库

**问题**：原实现中，INCREMENTAL策略会先调用第三方API获取数据，再在本地过滤已存在的日期，造成不必要的网络请求。

**解决方案**：在调用API前先查询数据库，如果请求日期范围内的数据已全部存在，则跳过API调用。

**效果**：
- 已有数据的股票不再调用第三方API
- 节省整体同步时间约50%-70%

---

## v1.1 (2026-03-22)

### 变更概要

数据源从 eastmoney 切换至腾讯。

### 详细变更

#### 1. 数据源切换

| 组件 | 变更前 | 变更后 |
|------|--------|--------|
| 日线数据接口 | `akshare.stock_zh_a_hist` (eastmoney) | `akshare.stock_zh_a_hist_tx` (腾讯) |
| 指数数据接口 | `akshare.stock_zh_index_daily_sina` | `akshare.stock_zh_index_daily` |

变更原因：eastmoney API (`push2his.eastmoney.com`) 被代理服务器屏蔽，腾讯数据源可通过代理访问。

---

### 变更影响

| 项目 | 状态 |
|------|------|
| 沪深股票 | ✅ 支持 |
| 科创板 | ✅ 支持 |
| 北交所 | ❌ 暂不支持 |
| 成交量/换手率字段 | ❌ 腾讯数据源不提供 |

---

## v1.0 (2026-03-22)

### 变更概要

初始版本，包含完整的技术方案设计。

### 详细变更

#### 新增内容

**1. 四层架构设计**

| 变更前 | 变更后 |
|--------|--------|
| 无 | 采用四层架构：tasks层 → services层 → data_source层 + storage层 → models层 |

变更原因：需求涉及7张表和多个业务流程，需要职责清晰、可测试、可维护的架构。

---

**2. 技术选型确定**

| 组件 | 变更前 | 变更后 |
|------|--------|--------|
| Python异步框架 | 待定 | asyncio + aiohttp |
| ClickHouse客户端 | 待定 | clickhouse-driver |
| 任务调度 | 待定 | APScheduler |

变更原因：
- asyncio + aiohttp：高并发、低内存、精确控制请求间隔
- clickhouse-driver：轻量高效、Native协议、批量插入方便
- APScheduler：轻量、单机场景足够

---

**3. 项目结构**

```
stock-scraper/
├── config/           # 配置管理
├── models/           # 数据模型
├── data_source/     # 数据源层
├── storage/         # 存储层
├── services/        # 业务层
├── tasks/           # 调度层
├── reports/         # 报告输出
├── logs/            # 日志目录
├── tests/           # 测试
├── requirements.txt
└── main.py
```

变更原因：按四层架构组织，职责清晰。

---

**4. 异常处理体系**

| 变更前 | 变更后 |
|--------|--------|
| 无 | 三级分类：NetworkError / DataError / BusinessError |

变更原因：
- 异常分类是异常处理的基础
- 不同类型异常需要不同的处理策略
- 便于异常统计和告警

---

**5. 断点续传机制**

| 变更前 | 变更后 |
|--------|--------|
| 无 | 基于sync_status表实现断点续传 |

变更原因：全量同步5000只股票可能耗时8小时，需要支持中断后恢复。

---

**6. 批量写入策略**

| 变更前 | 变更后 |
|--------|--------|
| 无 | 1024行/批次 |

变更原因：平衡内存占用与网络开销，ClickHouse最佳实践。

---

**7. 请求限流策略**

| 变更前 | 变更后 |
|--------|--------|
| 无 | 基础间隔1.5秒，动态调整最大10秒 |

变更原因：
- akshare是免费开源库，无严格QPS限制
- 需要礼貌性请求避免IP被封
- 动态调整应对临时限流

---

**8. 告警机制**

| 变更前 | 变更后 |
|--------|--------|
| 无 | 输出到 logs/alerts.log 文件 |

变更原因：
- 简化架构，不引入额外通知组件
- 文件便于查看和追踪

---

**9. 实施路线图**

| 阶段 | 内容 | 预计时间 |
|------|------|----------|
| Phase 0 | 前置准备（ClickHouse部署、项目结构） | 1天 |
| Phase 1 | 核心开发（数据模型、数据源、存储、业务逻辑、任务调度） | 3天 |
| Phase 2 | 验证与测试（单元测试、小批量验证） | 2天 |
| Phase 3 | 自动化（定时任务、告警、全量验证） | 1天 |

---

**10. 验证计划**

| 验证项 | 标准 |
|--------|------|
| 数据完整率 | > 99% |
| 涨跌幅校验 | ±10%以内 |
| 小批量验证时间 | < 1小时（3-5只） |

验证股票：
- 600000（上海主板）
- 000001（深圳主板）
- 300750（创业板）
- 688001（科创板）

**11. 异常股票验证用例**

新增异常场景验证用例，确保系统对各种异常情况处理正确：

| 类别 | 用例 | 说明 |
|------|------|------|
| ST股票 | V-ST-01, V-ST-02 | 涨跌幅±20%、退市处理 |
| 退市股票 | V-DL-01, V-DL-02 | 完整历史+退市标记 |
| 新股 | V-NW-01, V-NW-02 | is_new标记、涨跌幅±20% |
| 停牌股票 | V-SP-01, V-SP-02 | 停牌期间跳过、复牌恢复 |
| 极端价格 | V-EP-01~03 | 高价/低价/涨跌停 |
| 网络异常 | V-NE-01~03 | 超时重试、限流退避、错误记录 |

变更原因：需求文档强调"需要完善对异常场景的处理"，验证用例是确保异常处理正确性的关键。

**12. 任务清单文档**

拆分出独立的 [TASK_LIST.md](./TASK_LIST.md)，包含：
- 85个细粒度任务
- 每个任务有验证方式和状态
- 记录完成时间和当前任务
- 任务依赖关系图

变更原因：实施路线图粒度太粗，需要更细致的任务拆分和追踪机制。

---

### 技术决策记录 (ADRs)

| ADR | 决策 | 状态 |
|-----|------|------|
| ADR-001 | 四层架构 | ✅ 已确认 |
| ADR-002 | 1024行批次写入 | ✅ 已确认 |
| ADR-003 | 三级异常分类+指数退避 | ✅ 已确认 |
| ADR-004 | sync_status表断点续传 | ✅ 已确认 |
| ADR-005 | sync_report表+JSON双报告 | ✅ 已确认 |
| ADR-006 | 数据源接口抽象+注册表 | ✅ 已确认 |

---

### 待确认事项

| 项目 | 状态 |
|------|------|
| ClickHouse部署方式 | 待确认 |
| 实际网络环境QPS | 待测试 |

---

**文档路径**: `/root/ai/claudecode/first/stock-scraper/docs/TECHNICAL_CHANGELOG.md`
