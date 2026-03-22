-- storage/migrations/init.sql
-- A股股票数据爬虫系统 - ClickHouse 表结构初始化

-- 1. 股票信息表
CREATE TABLE IF NOT EXISTS stock_info
(
    stock_code String,
    stock_name String,
    market String,
    industry Nullable(String),
    sub_industry Nullable(String),
    list_date Nullable(Date),
    delist_date Nullable(Date),
    stock_type Nullable(String),
    is_st Nullable(Bool),
    is_new Nullable(Bool),
    total_shares Nullable(Float64),
    outstanding_shares Nullable(Float64),
    status Nullable(String),
    is_hs300 Nullable(Bool),
    is_zz500 Nullable(Bool),
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (stock_code, market)
SETTINGS index_granularity = 8192;

-- 2. 股票日线数据表
CREATE TABLE IF NOT EXISTS stock_daily
(
    stock_code String,
    trade_date Date,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume Int64,
    turnover Float64,
    change_pct Float64,
    pre_close Float64,
    amplitude_pct Float64,
    turnover_rate Float64,
    data_source String,
    adjust_type String,
    is_adjusted Bool,
    quality_flag String DEFAULT 'good',
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (stock_code, trade_date)
SETTINGS index_granularity = 8192;

-- 3. 同步状态表
CREATE TABLE IF NOT EXISTS sync_status
(
    stock_code String,
    sync_type String,
    status String,
    last_sync_time Nullable(DateTime),
    records_synced Int64 DEFAULT 0,
    error_message Nullable(String),
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (stock_code, sync_type)
SETTINGS index_granularity = 8192;

-- 4. 同步错误表
CREATE TABLE IF NOT EXISTS sync_error
(
    stock_code String,
    error_type String,
    error_message String,
    error_code Nullable(String),
    retry_count Int32 DEFAULT 0,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (stock_code, created_at)
SETTINGS index_granularity = 8192;

-- 5. 同步报告表
CREATE TABLE IF NOT EXISTS sync_report
(
    id UInt64 DEFAULT rowNumberInAllBlocks(),
    sync_type String,
    trigger_type String,
    total_stocks Int64,
    success_count Int64,
    failed_count Int64,
    quality_pass_count Int64 DEFAULT 0,
    quality_fail_count Int64 DEFAULT 0,
    status String,
    start_time DateTime,
    end_time Nullable(DateTime),
    duration_seconds Nullable(Int64),
    error_details String DEFAULT '',
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (id)
SETTINGS index_granularity = 8192;

-- 6. 指数日线数据表
CREATE TABLE IF NOT EXISTS daily_index
(
    index_code String,
    index_name String,
    trade_date Date,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume Int64,
    turnover Float64,
    change_pct Float64,
    data_source String,
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (index_code, trade_date)
SETTINGS index_granularity = 8192;

-- 7. 股票分红送股表
CREATE TABLE IF NOT EXISTS stock_split
(
    stock_code String,
    trade_date Date,
    event_type String,
    before_quantity Nullable(Float64),
    after_quantity Nullable(Float64),
    ratio_before Nullable(Float64),
    ratio_after Nullable(Float64),
    data_source String,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (stock_code, trade_date)
SETTINGS index_granularity = 8192;
