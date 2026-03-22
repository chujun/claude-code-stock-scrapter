# A股股票数据爬虫系统 - 技术方案

## 文档信息

| 项目 | 内容 |
|------|------|
| 项目名称 | A股股票数据爬虫系统 |
| 文档状态 | 待确认 |
| 当前位置 | /root/ai/claudecode/first/stock-scraper/docs/TECHNICAL.md |

---

## 目录

1. [版本变更记录](#一版本变更记录)
2. [技术架构概述](#二技术架构概述)
3. [技术选型](#三技术选型)
4. [项目结构](#四项目结构)
5. [模块设计](#五模块设计)
6. [数据模型](#六数据模型)
7. [接口设计](#七接口设计)
8. [异常处理策略](#八异常处理策略)
9. [存储设计](#九存储设计)
10. [任务调度设计](#十任务调度设计)
11. [实施路线图](#十一实施路线图)
12. [验证计划](#十二验证计划)

---

## 一、版本变更记录

### 版本历史

| 版本 | 日期 | 作者 | 变更概要 |
|------|------|------|----------|
| v1.0 | 2026-03-22 | - | 初始版本，技术方案初稿 |

### 详细变更记录

> **参考文档**：[TECHNICAL_CHANGELOG.md](./TECHNICAL_CHANGELOG.md)
>
> 详细的技术方案变更记录已拆分至独立的 `TECHNICAL_CHANGELOG.md` 文档，包括每次变更的变更前/变更后对比，便于审计追踪。
>
> 主技术文档仅保留版本概要，避免文档膨胀。

---

## 二、技术架构概述

### 2.1 整体架构

系统采用**四层架构**设计：

```
┌─────────────────────────────────────────────────────────────┐
│                      tasks层 (调度层)                        │
│   FullSyncTask | DailySyncTask | VerificationTask           │
├─────────────────────────────────────────────────────────────┤
│                     services层 (业务层)                      │
│   StockSyncService | QualityService | ReportService          │
├─────────────────────────────────────────────────────────────┤
│          data_source层 (数据源层)  │   storage层 (存储层)    │
│   AkshareClient                  │   ClickHouseRepository  │
├─────────────────────────────────────────────────────────────┤
│                     models (数据模型)                        │
│   StockDaily | SyncStatus | SyncError | StockInfo...        │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 架构原则

| 原则 | 说明 |
|------|------|
| 单一职责 | 每层职责清晰，互不越界 |
| 依赖倒置 | 上层依赖抽象接口，不依赖具体实现 |
| 可替换性 | 数据源层抽象，支持切换不同数据源 |
| 简化架构 | 非必要不引入新组件 |

### 2.3 技术特点

| 特点 | 说明 |
|------|------|
| 异步IO | asyncio + aiohttp，高并发请求 |
| 批量写入 | ClickHouse 1024行/批次 |
| 断点续传 | 基于sync_status表实现 |
| 指数退避 | 网络异常重试策略 |

---

## 三、技术选型

### 3.1 Python异步框架

**方案**：asyncio + aiohttp

| 维度 | 评估 |
|------|------|
| 并发能力 | 高，单进程可处理5000+股票 |
| 内存占用 | 低，协程切换开销小 |
| 请求控制 | 精确控制请求间隔，避免限流 |
| 学习曲线 | 较陡，需理解协程/事件循环 |

### 3.2 ClickHouse客户端

**方案**：clickhouse-driver

| 维度 | 评估 |
|------|------|
| 协议 | Native TCP协议，性能高 |
| 批量插入 | 支持，预留类型数组直接批量 |
| 类型映射 | 自动映射Python类型 |
| 依赖 | 轻量，只有一个driver |

### 3.3 任务调度

**方案**：APScheduler

| 维度 | 评估 |
|------|------|
| 功能 | 定时/周期任务 |
| cron表达式 | 支持 |
| 依赖 | 轻量 |
| 复杂度 | 低 |

### 3.4 核心依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| aiohttp | >=3.9.0 | 异步HTTP客户端 |
| clickhouse-driver | >=0.2.0 | ClickHouse客户端 |
| apscheduler | >=3.10.0 | 任务调度 |
| pydantic | >=2.0 | 数据验证 |
| pyyaml | >=6.0 | 配置文件 |

---

## 四、项目结构

### 4.1 目录结构

```
stock-scraper/
├── config/
│   ├── __init__.py
│   └── settings.py          # 配置管理
├── models/
│   ├── __init__.py
│   ├── base.py              # 基础模型
│   ├── stock_info.py        # 股票信息模型
│   ├── stock_daily.py       # 日线行情模型
│   ├── sync_status.py       # 同步状态模型
│   ├── sync_error.py        # 同步异常模型
│   ├── sync_report.py       # 同步报告模型
│   ├── daily_index.py       # 大盘指数模型
│   └── stock_split.py       # 分红送股模型
├── data_source/
│   ├── __init__.py
│   ├── base.py              # 数据源抽象基类
│   ├── akshare_client.py    # akshare数据源实现
│   └── exceptions.py        # 数据源异常定义
├── storage/
│   ├── __init__.py
│   ├── base.py              # 存储抽象基类
│   ├── clickhouse_repo.py   # ClickHouse存储实现
│   └── migrations/          # 表结构迁移
│       └── init.sql
├── services/
│   ├── __init__.py
│   ├── sync_service.py      # 同步服务
│   ├── quality_service.py    # 质量校验服务
│   ├── report_service.py     # 报告生成服务
│   └── exceptions.py        # 业务异常定义
├── tasks/
│   ├── __init__.py
│   ├── base.py              # 任务基类
│   ├── full_sync_task.py    # 全量同步任务
│   ├── daily_sync_task.py   # 每日增量任务
│   └── verification_task.py # 小批量验证任务
├── reports/                  # 同步报告输出目录
├── logs/                    # 日志目录
│   └── alerts.log          # 告警文件
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_quality_service.py
│   │   └── test_sync_service.py
│   └── conftest.py
├── requirements.txt
├── main.py                  # CLI入口
└── README.md
```

### 4.2 模块职责

| 模块 | 职责 |
|------|------|
| config/ | 配置管理，从配置文件读取 |
| models/ | Pydantic数据模型定义 |
| data_source/ | 数据源抽象和akshare实现 |
| storage/ | ClickHouse存储抽象和实现 |
| services/ | 业务逻辑（同步/质量/报告） |
| tasks/ | 任务调度（APScheduler） |

---

## 五、模块设计

### 5.1 配置管理 (config/settings.py)

```python
class Settings:
    """系统配置"""

    # ClickHouse配置
    clickhouse:
        host: str = "localhost"
        port: int = 9000
        database: str = "stock_scraper"
        user: str = "default"
        password: str = ""

    # 数据源配置
    data_source:
        name: str = "akshare"
        rate_limit:
            base_interval: float = 1.5  # 基础请求间隔(秒)
            max_interval: float = 10.0  # 最大间隔(秒)
            increase_factor: float = 1.5  # 失败后增加倍数

    # 同步配置
    sync:
        batch_size: int = 1024  # 批量写入大小
        max_retries: int = 3  # 最大重试次数
        retry_base_delay: float = 2.0  # 重试基础延迟(秒)

    # 任务调度配置
    scheduler:
        daily_sync_hour: int = 16  # 每日增量同步时间(时)
        daily_sync_minute: int = 0  # 每日增量同步时间(分)

    # 报告配置
    report:
        output_dir: str = "reports"
        alert_file: str = "logs/alerts.log"
```

### 5.2 数据模型 (models/)

#### 基础模型

```python
class BaseModel(PydanticBaseModel):
    """基础模型，所有数据模型的基类"""

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True
```

#### 股票日线模型

```python
class StockDaily(BaseModel):
    """股票日线行情"""

    stock_code: str = Field(..., description="股票代码")
    trade_date: date = Field(..., description="交易日期")
    open: Optional[float] = Field(None, description="前复权开盘价")
    high: Optional[float] = Field(None, description="前复权最高价")
    low: Optional[float] = Field(None, description="前复权最低价")
    close: float = Field(..., description="前复权收盘价")
    volume: Optional[int] = Field(None, description="成交量(手)")
    turnover: Optional[float] = Field(None, description="成交额(元)")
    change_pct: Optional[float] = Field(None, description="涨跌幅(%)")
    pre_close: Optional[float] = Field(None, description="前复权前收盘价")
    amplitude_pct: Optional[float] = Field(None, description="振幅(%)")
    turnover_rate: Optional[float] = Field(None, description="换手率(%)")
    total_market_cap: Optional[float] = Field(None, description="总市值(元)")
    float_market_cap: Optional[float] = Field(None, description="流通市值(元)")
    pe_ratio: Optional[float] = Field(None, description="市盈率(动态)")
    static_pe: Optional[float] = Field(None, description="静态市盈率")
    dynamic_pe: Optional[float] = Field(None, description="动态市盈率")
    pb_ratio: Optional[float] = Field(None, description="市净率")
    is_adjusted: bool = Field(True, description="是否复权数据")
    adjust_type: str = Field("qfq", description="复权类型")
    data_source: str = Field(..., description="数据来源标识")
    quality_flag: str = Field("good", description="数据质量标记")

    class Config:
        table_name = "stock_daily"
```

#### 同步状态模型

```python
class SyncStatus(BaseModel):
    """同步状态记录"""

    stock_code: Optional[str] = Field(None, description="股票代码，NULL表示全量任务")
    sync_type: str = Field(..., description="同步类型：full/daily/init")
    last_sync_date: Optional[date] = Field(None, description="最后同步日期")
    status: str = Field(..., description="状态：running/success/failed/partial")
    record_count: Optional[int] = Field(0, description="本次同步记录数")
    error_msg: Optional[str] = Field(None, description="错误信息")
    started_at: Optional[datetime] = Field(None, description="任务开始时间")
    finished_at: Optional[datetime] = Field(None, description="任务结束时间")

    class Config:
        table_name = "sync_status"
```

### 5.3 数据源层 (data_source/)

#### 抽象基类

```python
class BaseDataSource(ABC):
    """数据源抽象基类"""

    @abstractmethod
    async def get_stock_list(self) -> List[StockInfo]:
        """获取股票列表"""
        pass

    @abstractmethod
    async def get_daily(
        self,
        stock_code: str,
        start_date: date,
        end_date: date,
        adjust_type: str = "qfq"
    ) -> List[StockDaily]:
        """获取日线数据"""
        pass

    @abstractmethod
    async def get_index(
        self,
        index_code: str,
        start_date: date,
        end_date: date
    ) -> List[DailyIndex]:
        """获取指数数据"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
```

#### akshare实现

```python
class AkshareClient(BaseDataSource):
    """akshare数据源实现"""

    def __init__(self, settings: DataSourceSettings):
        self.settings = settings
        self.rate_limiter = RateLimiter(
            base_interval=settings.rate_limit.base_interval
        )
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_stock_list(self) -> List[StockInfo]:
        """获取A股所有股票列表"""
        await self.rate_limiter.wait()
        # 调用akshare API获取股票列表
        # 解析返回数据，转换为StockInfo列表
        pass

    async def get_daily(
        self,
        stock_code: str,
        start_date: date,
        end_date: date,
        adjust_type: str = "qfq"
    ) -> List[StockDaily]:
        """获取单只股票日线数据"""
        await self.rate_limiter.wait()
        # 调用akshare API获取历史K线
        # 解析返回数据，转换为StockDaily列表
        pass

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            await self.get_stock_list()
            return True
        except Exception:
            return False
```

### 5.4 存储层 (storage/)

#### 抽象基类

```python
class BaseRepository(ABC):
    """存储抽象基类"""

    @abstractmethod
    async def insert(self, table: str, records: List[dict]) -> int:
        """插入记录"""
        pass

    @abstractmethod
    async def upsert(self, table: str, records: List[dict]) -> int:
        """插入或更新记录"""
        pass

    @abstractmethod
    async def query(self, sql: str, params: dict = None) -> List[dict]:
        """查询"""
        pass

    @abstractmethod
    async def execute(self, sql: str, params: dict = None) -> None:
        """执行DDL/DML"""
        pass
```

#### ClickHouse实现

```python
class ClickHouseRepository(BaseRepository):
    """ClickHouse存储实现"""

    def __init__(self, settings: ClickHouseSettings):
        self.settings = settings
        self.client = ClickHouseClient(
            host=settings.host,
            port=settings.port,
            database=settings.database,
            user=settings.user,
            password=settings.password
        )
        self.batch_size = settings.batch_size

    async def upsert(self, table: str, records: List[dict]) -> int:
        """批量插入或更新（ClickHouse使用INSERT）"""
        if not records:
            return 0

        total = 0
        for i in range(0, len(records), self.batch_size):
            batch = records[i:i + self.batch_size]
            values = [tuple(r.values()) for r in batch]
            self.client.execute(
                f"INSERT INTO {table} VALUES",
                values
            )
            total += len(batch)
        return total

    async def query(self, sql: str, params: dict = None) -> List[dict]:
        """查询并返回字典列表"""
        result = self.client.execute(sql, params or {})
        # 转换结果为字典列表
        pass
```

### 5.5 服务层 (services/)

#### 同步服务

```python
class StockSyncService:
    """股票同步服务"""

    def __init__(
        self,
        data_source: BaseDataSource,
        repository: BaseRepository,
        quality_service: QualityService
    ):
        self.data_source = data_source
        self.repository = repository
        self.quality_service = quality_service

    async def sync_stock_daily(
        self,
        stock_code: str,
        start_date: date,
        end_date: date
    ) -> SyncResult:
        """同步单只股票日线数据"""
        # 1. 获取数据
        raw_data = await self.data_source.get_daily(
            stock_code, start_date, end_date
        )

        # 2. 数据质量校验
        validated_data, errors = await self.quality_service.validate(raw_data)

        # 3. 分类处理
        good_records = [r for r in validated_data if r.quality_flag == "good"]
        warn_records = [r for r in validated_data if r.quality_flag == "warn"]
        error_records = [r for r in validated_data if r.quality_flag == "error"]

        # 4. 批量入库
        if good_records or warn_records:
            await self.repository.upsert(
                "stock_daily",
                [r.model_dump() for r in good_records + warn_records]
            )

        # 5. 异常记录入库
        if error_records:
            await self._save_errors(error_records)

        return SyncResult(
            stock_code=stock_code,
            total=len(raw_data),
            success=len(good_records),
            warning=len(warn_records),
            error=len(error_records),
            errors=errors
        )

    async def full_sync(self, stock_codes: List[str]) -> SyncReport:
        """全量同步"""
        pass

    async def daily_sync(self) -> SyncReport:
        """每日增量同步"""
        pass
```

#### 质量服务

```python
class QualityService:
    """数据质量校验服务"""

    def __init__(self, settings: QualitySettings):
        self.settings = settings

    async def validate(self, records: List[StockDaily]) -> Tuple[List[StockDaily], List[QualityError]]:
        """数据质量校验"""
        validated = []
        errors = []

        for record in records:
            # 1. 字段完整性检查
            if not self._check_completeness(record):
                record.quality_flag = "warn"
                validated.append(record)
                continue

            # 2. 涨跌幅校验
            if not self._check_change_pct(record):
                errors.append(QualityError(
                    stock_code=record.stock_code,
                    trade_date=record.trade_date,
                    error_type="change_pct_exceeded",
                    error_msg=f"涨跌幅超限: {record.change_pct}%"
                ))
                continue

            # 3. OHLC关系校验
            if not self._check_ohlc_relation(record):
                # 自动修正
                record.high = max(record.open or 0, record.close or 0, record.high or 0)
                record.low = min(record.open or 0, record.close or 0, record.low or 0)
                record.quality_flag = "warn"

            validated.append(record)

        return validated, errors

    def _check_change_pct(self, record: StockDaily) -> bool:
        """涨跌幅校验：±10%以内（新股/ST股票允许±20%）"""
        if record.change_pct is None:
            return True

        limit = 20.0 if record.is_st or record.is_new else 10.0
        return abs(record.change_pct) <= limit

    def _check_ohlc_relation(self, record: StockDaily) -> bool:
        """OHLC关系校验：low <= open,close <= high"""
        if all(v is not None for v in [record.open, record.close, record.high, record.low]):
            return record.low <= record.open and record.close <= record.high
        return True
```

### 5.6 任务层 (tasks/)

#### 任务基类

```python
class BaseTask(ABC):
    """任务基类"""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"tasks.{name}")

    @abstractmethod
    async def execute(self) -> TaskResult:
        """执行任务"""
        pass

    async def run(self):
        """任务运行入口"""
        self.logger.info(f"Task {self.name} started")
        try:
            result = await self.execute()
            self.logger.info(f"Task {self.name} completed: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Task {self.name} failed: {e}")
            raise
```

#### 全量同步任务

```python
class FullSyncTask(BaseTask):
    """全量同步任务"""

    def __init__(
        self,
        sync_service: StockSyncService,
        repository: BaseRepository
    ):
        super().__init__("full_sync")
        self.sync_service = sync_service
        self.repository = repository

    async def execute(self) -> TaskResult:
        """执行全量同步"""
        # 1. 获取所有股票列表
        stock_list = await self.sync_service.get_all_stocks()

        # 2. 查询已同步状态
        synced_codes = await self.repository.query(
            "SELECT stock_code FROM sync_status WHERE status='success'"
        )

        # 3. 构建待同步列表（排除已成功）
        to_sync = [
            s for s in stock_list
            if s.stock_code not in {x["stock_code"] for x in synced_codes}
        ]

        # 4. 遍历同步
        results = []
        for stock in tqdm(to_sync):
            result = await self.sync_service.sync_stock_daily(
                stock.stock_code,
                start_date=date(2004, 1, 1),
                end_date=date.today()
            )
            results.append(result)

        # 5. 生成报告
        return self._aggregate_results(results)
```

---

## 六、数据模型

### 6.1 ClickHouse表结构

详见需求文档`docs/requirements.md`第四章数据模型。

### 6.2 索引设计

| 表名 | 唯一索引 | 普通索引 | 原因 |
|------|----------|----------|------|
| stock_daily | (trade_date, stock_code) | stock_code | 按股票+按日期范围查询 |
| stock_info | stock_code | market, status | 主键查询、行业统计 |
| sync_status | (stock_code, sync_type) | status | 断点续传的唯一性 |
| daily_index | (trade_date, index_code) | - | 唯一性保障 |
| stock_split | (stock_code, event_date, event_type) | - | 唯一性保障 |
| sync_error | id (自增) | stock_code, error_type, status | 异常查询 |
| sync_report | id (自增) | sync_type, started_at | 报告查询 |

### 6.3 批量写入策略

```python
# 推荐批量大小
BATCH_SIZE = 1024  # ClickHouse最佳实践

# 执行批量插入
async def batch_insert(table: str, records: List[dict]):
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        values = [tuple(r.values()) for r in batch]
        client.execute(f"INSERT INTO {table} VALUES", values)
```

---

## 七、接口设计

### 7.1 CLI接口

```bash
# 全量同步
python main.py full-sync [--stocks StockCode1,StockCode2]

# 每日增量
python main.py daily-sync

# 小批量验证
python main.py verify --count 5

# 查看同步状态
python main.py status [--stock StockCode]

# 查看同步报告
python main.py report [--date YYYY-MM-DD]
```

### 7.2 内部服务接口

#### StockSyncService

```python
class StockSyncService:
    async def sync_stock_daily(
        self,
        stock_code: str,
        start_date: date,
        end_date: date
    ) -> SyncResult:
        """同步单只股票日线数据"""

    async def sync_stock_list(self) -> SyncResult:
        """同步股票列表"""

    async def full_sync(self, stock_codes: List[str] = None) -> SyncReport:
        """全量同步"""

    async def daily_sync(self) -> SyncReport:
        """每日增量同步"""
```

#### QualityService

```python
class QualityService:
    async def validate(self, records: List[StockDaily]) -> Tuple[List[StockDaily], List[QualityError]]:
        """数据质量校验"""

    def check_completeness(self, record: StockDaily) -> bool:
        """字段完整性检查"""

    def check_change_pct(self, record: StockDaily) -> bool:
        """涨跌幅校验"""

    def check_ohlc_relation(self, record: StockDaily) -> bool:
        """OHLC关系校验"""
```

---

## 八、异常处理策略

### 8.1 异常分类体系

```python
# 异常基类
class ScraperException(Exception):
    """爬虫系统异常基类"""
    error_type: str = "unknown"

# 网络异常 - 可重试
class NetworkError(ScraperException):
    """网络相关异常"""
    error_type = "network"
    retryable = True

class TimeoutError(NetworkError):
    """请求超时"""
    error_code = "timeout"

class RateLimitError(NetworkError):
    """API限流"""
    error_code = "429"

class ServerError(NetworkError):
    """服务器错误"""
    error_code = "5xx"

# 数据异常 - 部分可修复
class DataError(ScraperException):
    """数据相关异常"""
    error_type = "data"
    retryable = False

class FieldMissingError(DataError):
    """字段缺失"""
    error_code = "field_missing"

class IntegrityError(DataError):
    """数据完整性错误"""
    error_code = "integrity"

# 业务异常 - 不重试
class BusinessError(ScraperException):
    """业务相关异常"""
    error_type = "business"
    retryable = False

class DelistedError(BusinessError):
    """股票已退市"""
    error_code = "delisted"

class NoDataError(BusinessError):
    """无数据"""
    error_code = "no_data"
```

### 8.2 重试机制

```python
# 重试配置
RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay": 2.0,      # 基础延迟(秒)
    "max_delay": 60.0,      # 最大延迟(秒)
    "exponential_base": 2   # 指数基数
}

async def retry_with_backoff(func, *args, **kwargs):
    """指数退避重试"""
    for attempt in range(RETRY_CONFIG["max_retries"]):
        try:
            return await func(*args, **kwargs)
        except NetworkError as e:
            if not e.retryable or attempt == RETRY_CONFIG["max_retries"] - 1:
                raise
            delay = min(
                RETRY_CONFIG["base_delay"] * (RETRY_CONFIG["exponential_base"] ** attempt),
                RETRY_CONFIG["max_delay"]
            )
            await asyncio.sleep(delay)
```

### 8.3 异常记录策略

| 异常类型 | 处理策略 |
|----------|----------|
| 网络异常 | 立即重试3次 → 仍失败 → 记录sync_error(status=pending) |
| 数据异常 | 可修复 → 自动修复+标记warn → 入库 |
| 数据异常 | 不可修复 → 记录sync_error(status=pending) |
| 业务异常 | 记录sync_error(status=resolved) → 跳过 |

### 8.4 告警机制

```python
# 告警输出到专门文件
ALERT_CONFIG = {
    "alert_file": "logs/alerts.log",
    "alert_threshold": {
        "error_rate": 0.05,      # 错误率超过5%告警
        "consecutive_failures": 10 # 连续失败10次告警
    }
}

async def check_and_alert(report: SyncReport):
    """检查是否需要告警"""
    if report.failed_count / report.total_stocks > ALERT_CONFIG["alert_threshold"]["error_rate"]:
        await write_alert(
            f"[ALERT] Error rate {report.failed_count/report.total_stocks:.2%} exceeded threshold",
            report
        )
```

---

## 九、存储设计

### 9.1 ClickHouse配置

```yaml
# config.yaml
clickhouse:
  host: "localhost"
  port: 9000
  database: "stock_scraper"
  user: "default"
  password: ""
  batch_size: 1024
```

### 9.2 表结构初始化

```sql
-- stock_daily表
CREATE TABLE IF NOT EXISTS stock_daily (
    stock_code String,
    trade_date Date,
    open Nullable(Float64),
    high Nullable(Float64),
    low Nullable(Float64),
    close Float64,
    volume Nullable(Int64),
    turnover Nullable(Float64),
    change_pct Nullable(Float64),
    pre_close Nullable(Float64),
    amplitude_pct Nullable(Float64),
    turnover_rate Nullable(Float64),
    total_market_cap Nullable(Float64),
    float_market_cap Nullable(Float64),
    pe_ratio Nullable(Float64),
    static_pe Nullable(Float64),
    dynamic_pe Nullable(Float64),
    pb_ratio Nullable(Float64),
    is_adjusted UInt8,
    adjust_type String,
    data_source String,
    quality_flag String DEFAULT 'good',
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, stock_code);

-- 唯一索引
ALTER TABLE stock_daily ADD UNIQUE INDEX idx_date_code (trade_date, stock_code);
```

### 9.3 连接池配置

```python
class ClickHousePool:
    """ClickHouse连接池"""

    def __init__(self, settings: ClickHouseSettings):
        self.settings = settings
        self._pool: Optional[ClickHouseClient] = None

    async def get_client(self) -> ClickHouseClient:
        """获取客户端"""
        if self._pool is None:
            self._pool = ClickHouseClient(
                host=self.settings.host,
                port=self.settings.port,
                database=self.settings.database,
                user=self.settings.user,
                password=self.settings.password,
                connect_timeout=10,
                send_receive_timeout=30
            )
        return self._pool

    async def close(self):
        """关闭连接池"""
        if self._pool:
            self._pool.disconnect()
            self._pool = None
```

---

## 十、任务调度设计

### 10.1 APScheduler配置

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

def create_scheduler() -> AsyncIOScheduler:
    """创建调度器"""
    scheduler = AsyncIOScheduler()

    # 每日16:00增量同步
    scheduler.add_job(
        func=daily_sync_job,
        trigger=CronTrigger(hour=16, minute=0),
        id="daily_sync",
        name="每日增量同步",
        replace_existing=True
    )

    return scheduler

async def daily_sync_job():
    """每日同步任务"""
    service = create_sync_service()
    report = await service.daily_sync()
    await generate_report(report)
```

### 10.2 任务状态管理

```python
class TaskState:
    """任务状态管理"""

    LOCK_FILE = "logs/task.lock"

    @staticmethod
    def acquire() -> bool:
        """获取任务锁"""
        lock_file = Path(TaskState.LOCK_FILE)
        if lock_file.exists():
            return False
        lock_file.write_text(str(os.getpid()))
        return True

    @staticmethod
    def release():
        """释放任务锁"""
        lock_file = Path(TaskState.LOCK_FILE)
        if lock_file.exists():
            lock_file.unlink()
```

---

## 十一、实施路线图

### Phase 0: 前置准备（1天）

| 任务 | 说明 | 状态 |
|------|------|------|
| P0.1 | ClickHouse部署 | 待定 |
| P0.2 | 项目结构创建 | - |
| P0.3 | 配置文件创建 | - |
| P0.4 | requirements.txt | - |

### Phase 1: 核心开发（3天）

| 任务 | 说明 | 状态 |
|------|------|------|
| P1.1 | 数据模型层 (models/) | - |
| P1.2 | 数据源层 (data_source/) | - |
| P1.3 | 存储层 (storage/) | - |
| P1.4 | 业务逻辑层 (services/) | - |
| P1.5 | 任务调度层 (tasks/) | - |

### Phase 2: 验证与测试（2天）

| 任务 | 说明 | 状态 |
|------|------|------|
| P2.1 | 单元测试 | - |
| P2.2 | 小批量验证（3-5只） | - |
| P2.3 | 数据质量报告 | - |

### Phase 3: 自动化（1天）

| 任务 | 说明 | 状态 |
|------|------|------|
| P3.1 | APScheduler定时任务 | - |
| P3.2 | 告警机制 | - |
| P3.3 | 全量验证 | - |

---

## 十二、验证计划

### 12.1 验证阶段（Phase 0）

**目标**：验证数据获取可行性

**验证步骤**：
1. 选取3-5只不同市场的股票
   - 600000（上海主板）
   - 000001（深圳主板）
   - 300750（创业板）
   - 688001（科创板）
2. 获取2004年至今的所有历史数据
3. 验证数据完整性、准确性
4. 验证ClickHouse存储和查询

**成功标准**：
- 数据完整率 > 99%
- 涨跌幅校验通过
- 查询响应正常

### 12.2 性能指标

| 指标 | 目标值 | 实际值 |
|------|--------|--------|
| 小批量验证 | < 1小时（3-5只） | 待测 |
| 单只股票平均耗时 | 1.5-2秒 | 待测 |
| 批量写入速度 | 1024条/批 | 待测 |
| 全量爬取时间 | < 8小时（分批） | 待测 |

### 12.3 正常股票验证用例

**目标**：验证系统对正常股票的完整处理流程

| 用例编号 | 股票代码 | 市场 | 验证要点 |
|----------|----------|------|----------|
| V-N-01 | 600000 | 上海主板 | 典型主板股票，数据完整性 |
| V-N-02 | 000001 | 深圳主板 | 典型主板股票，历史悠久 |
| V-N-03 | 300750 | 创业板 | 创业板股票，波动较大 |
| V-N-04 | 688001 | 科创板 | 科创板股票，上市时间短 |

**验证内容**：
- [ ] 数据获取成功（无网络错误）
- [ ] 数据完整率 > 99%
- [ ] 涨跌幅校验 ±10%范围内
- [ ] OHLC关系正确（low ≤ open,close ≤ high）
- [ ] 成功写入ClickHouse
- [ ] 同步报告生成正确

### 12.4 异常股票验证用例

**目标**：验证系统对异常场景的处理能力

#### 12.4.1 ST股票验证

| 用例编号 | 股票代码 | 说明 | 验证要点 |
|----------|----------|------|----------|
| V-ST-01 | *ST兴业 | 历史上ST | 涨跌幅限制±5%（旧规） |
| V-ST-02 | ST长生 | 已退市ST | 退市处理、异常记录 |

**验证内容**：
- [ ] 涨跌幅校验通过（ST股票允许±20%）
- [ ] 已退市股票正确标记delist_date
- [ ] 异常数据记录到sync_error表

#### 12.4.2 退市股票验证

| 用例编号 | 股票代码 | 说明 | 验证要点 |
|----------|----------|------|----------|
| V-DL-01 | 600654 | 已退市 | 退市后无数据处理 |
| V-DL-02 | 000003 | 历史上退市 | 完整历史+退市标记 |

**验证内容**：
- [ ] 历史数据完整（上市到退市）
- [ ] delist_date字段正确
- [ ] 退市后无新数据不报错

#### 12.4.3 新股验证

| 用例编号 | 股票代码 | 上市时间 | 验证要点 |
|----------|----------|----------|----------|
| V-NW-01 | 301538 | 上市未满一年 | 新股标记is_new=True |
| V-NW-02 | 688787 | 上市不足一年 | 新股涨跌幅限制±20% |

**验证内容**：
- [ ] is_new标记正确
- [ ] 新股涨跌幅允许±20%
- [ ] 数据完整无缺失

#### 12.4.4 停牌股票验证

| 用例编号 | 股票代码 | 说明 | 验证要点 |
|----------|----------|------|----------|
| V-SP-01 | 600212 | 历史上停牌 | 停牌期间无数据 |
| V-SP-02 | 000693 | 长期停牌 | 复牌后数据恢复 |

**验证内容**：
- [ ] 停牌期间日期无数据（正确跳过）
- [ ] 复牌后数据正常获取
- [ ] 不报异常错误

#### 12.4.5 极端价格验证

| 用例编号 | 情况 | 说明 | 验证要点 |
|----------|------|------|----------|
| V-EP-01 | 极高价格 | 单价>1000元 | 价格字段正确存储 |
| V-EP-02 | 极低价格 | 单价<1元 | 价格字段正确存储 |
| V-EP-03 | 涨跌停 | 10%/20%限幅 | 涨跌幅字段正确 |

**验证内容**：
- [ ] 高价股票数值精度正确
- [ ] 低价股票数值精度正确
- [ ] 涨跌停价格计算正确

#### 12.4.6 网络异常验证

| 用例编号 | 场景 | 模拟方式 | 验证要点 |
|----------|------|----------|----------|
| V-NE-01 | 超时 | 请求超时 | 指数退避重试 |
| V-NE-02 | 限流 | 429响应 | 自动暂停后恢复 |
| V-NE-03 | 服务端错误 | 500响应 | 重试后记录错误 |

**验证内容**：
- [ ] 超时后正确重试（最多3次）
- [ ] 限流后指数退避等待
- [ ] 错误记录到sync_error表

### 12.5 验证检查清单

| 编号 | 检查项 | 状态 |
|------|--------|------|
| 1 | akshare API连接正常 | ☐ |
| 2 | ClickHouse连接正常 | ☐ |
| 3 | 单只股票数据获取成功 | ☐ |
| 4 | 数据质量校验通过 | ☐ |
| 5 | 数据成功写入ClickHouse | ☐ |
| 6 | 同步报告生成正常 | ☐ |
| 7 | 异常处理机制正常 | ☐ |
| 8 | 断点续传机制正常 | ☐ |
| 9 | ST股票处理正常 | ☐ |
| 10 | 退市股票处理正常 | ☐ |
| 11 | 新股标记正确 | ☐ |
| 12 | 停牌股票处理正常 | ☐ |
| 13 | 网络异常重试正常 | ☐ |

---

**文档路径**: `/root/ai/claudecode/first/stock-scraper/docs/TECHNICAL.md`
