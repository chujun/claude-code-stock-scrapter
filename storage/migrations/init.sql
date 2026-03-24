-- storage/migrations/init.sql
-- A股股票数据爬虫系统 - ClickHouse 表结构初始化

-- 1. 股票信息表
-- 存储A股股票的基本信息
CREATE TABLE IF NOT EXISTS stock_info
(
    stock_code String COMMENT '股票代码，如 600000、000001',
    stock_name String COMMENT '股票名称',
    market String COMMENT '交易所市场，SSE=上交所，SZSE=深交所',
    industry Nullable(String) COMMENT '所属行业，证监会行业分类',
    sub_industry Nullable(String) COMMENT '细分行业',
    list_date Nullable(Date) COMMENT '上市日期',
    delist_date Nullable(Date) COMMENT '退市日期，为NULL表示未退市',
    stock_type Nullable(String) COMMENT '股票类型，如 common、preferred',
    is_st Nullable(Bool) COMMENT '是否ST或*ST股票',
    is_new Nullable(Bool) COMMENT '是否新股（上市一年以内）',
    total_shares Nullable(Float64) COMMENT '总股本，单位股',
    outstanding_shares Nullable(Float64) COMMENT '流通股本，单位股',
    status Nullable(String) COMMENT '状态，active=正常，suspended=停牌，delisted=退市',
    is_hs300 Nullable(Bool) COMMENT '是否沪深300成分股',
    is_zz500 Nullable(Bool) COMMENT '是否中证500成分股',
    created_at DateTime DEFAULT now() COMMENT '记录创建时间',
    updated_at DateTime DEFAULT now() COMMENT '记录更新时间'
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (stock_code, market)
SETTINGS index_granularity = 8192;

-- 2. 股票日线数据表
-- 数据来源：akshare (腾讯数据源 stock_zh_a_hist_tx)
-- 复权类型：qfq (前复权)
CREATE TABLE IF NOT EXISTS stock_daily
(
    stock_code String COMMENT '股票代码，如 600000、000001',
    trade_date Date COMMENT '交易日期',
    open Float64 COMMENT '开盘价，单位元，腾讯数据源提供',
    high Float64 COMMENT '最高价，单位元，腾讯数据源提供',
    low Float64 COMMENT '最低价，单位元，腾讯数据源提供',
    close Float64 COMMENT '收盘价，单位元，腾讯数据源提供',
    volume Int64 COMMENT '成交量，单位股，腾讯数据源不提供，固定为0',
    turnover Float64 COMMENT '成交额，单位元，腾讯数据源提供(对应amount字段)',
    change_pct Float64 COMMENT '涨跌幅，单位%，通过前后收盘价计算得出',
    pre_close Float64 COMMENT '前收盘价，根据复权类型计算',
    amplitude_pct Float64 COMMENT '振幅，单位%，腾讯数据源不提供，固定为0',
    turnover_rate Float64 COMMENT '换手率，单位%，腾讯数据源不提供，固定为0',
    total_market_cap Nullable(Float64) COMMENT '总市值，单位元，未采集',
    float_market_cap Nullable(Float64) COMMENT '流通市值，单位元，未采集',
    pe_ratio Nullable(Float64) COMMENT '市盈率(静动态)，从雪球API采集，覆盖率<1%',
    static_pe Nullable(Float64) COMMENT '静态市盈率，从雪球API采集，覆盖率<1%',
    dynamic_pe Nullable(Float64) COMMENT '动态市盈率，从雪球API采集，覆盖率<1%',
    pb_ratio Nullable(Float64) COMMENT '市净率，未采集，固定为NULL',
    data_source String COMMENT '数据源标识，固定为 akshare_tx',
    adjust_type String COMMENT '复权类型，固定为 qfq (前复权)',
    is_adjusted Bool COMMENT '是否复权，固定为 true',
    quality_flag String DEFAULT 'good' COMMENT '数据质量标记：good/warn/error',
    created_at DateTime DEFAULT now() COMMENT '记录创建时间',
    updated_at DateTime DEFAULT now() COMMENT '记录更新时间'
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (stock_code, trade_date)
SETTINGS index_granularity = 8192;

-- 3. 同步状态表
-- 记录每只股票的同步进度，支持断点续传
CREATE TABLE IF NOT EXISTS sync_status
(
    stock_code String COMMENT '股票代码，为空表示全量同步任务',
    sync_type String COMMENT '同步类型：full=全量同步，daily=每日增量',
    status String COMMENT '同步状态：running=运行中，success=成功，failed=失败，partial=部分成功',
    last_sync_time Nullable(DateTime) COMMENT '最后同步时间',
    records_synced Int64 DEFAULT 0 COMMENT '本次同步的记录数',
    error_message Nullable(String) COMMENT '错误信息',
    created_at DateTime DEFAULT now() COMMENT '记录创建时间',
    updated_at DateTime DEFAULT now() COMMENT '记录更新时间'
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (stock_code, sync_type)
SETTINGS index_granularity = 8192;

-- 4. 同步错误表
-- 记录同步过程中的错误信息
CREATE TABLE IF NOT EXISTS sync_error
(
    stock_code String COMMENT '股票代码',
    error_type String COMMENT '错误类型：network=网络错误，data=数据错误，business=业务错误',
    error_message String COMMENT '错误详情',
    error_code Nullable(String) COMMENT '错误代码',
    retry_count Int32 DEFAULT 0 COMMENT '重试次数',
    created_at DateTime DEFAULT now() COMMENT '记录创建时间'
)
ENGINE = MergeTree()
ORDER BY (stock_code, created_at)
SETTINGS index_granularity = 8192;

-- 5. 同步报告表
-- 记录每次同步任务的汇总报告
CREATE TABLE IF NOT EXISTS sync_report
(
    id UInt64 DEFAULT rowNumberInAllBlocks() COMMENT '报告ID，自增',
    sync_type String COMMENT '同步类型：full=全量，daily=增量，verification=验证',
    trigger_type String COMMENT '触发类型：manual=手动，scheduled=定时，api=API调用',
    total_stocks Int64 COMMENT '目标股票总数',
    success_count Int64 COMMENT '成功数量',
    failed_count Int64 COMMENT '失败数量',
    quality_pass_count Int64 DEFAULT 0 COMMENT '质量校验通过数量',
    quality_fail_count Int64 DEFAULT 0 COMMENT '质量校验失败数量',
    status String COMMENT '任务状态：running=运行中，success=成功，failed=失败',
    start_time DateTime COMMENT '开始时间',
    end_time Nullable(DateTime) COMMENT '结束时间',
    duration_seconds Nullable(Int64) COMMENT '持续时长，单位秒',
    error_details String DEFAULT '' COMMENT '错误详情汇总',
    created_at DateTime DEFAULT now() COMMENT '记录创建时间'
)
ENGINE = MergeTree()
ORDER BY (id)
SETTINGS index_granularity = 8192;

-- 6. 指数日线数据表
-- 存储大盘指数的日线数据
CREATE TABLE IF NOT EXISTS daily_index
(
    index_code String COMMENT '指数代码，如 000001=上证指数，399001=深证成指，399006=创业板指',
    index_name String COMMENT '指数名称，如 上证指数、深证成指、创业板指',
    trade_date Date COMMENT '交易日期',
    open Float64 COMMENT '开盘点位',
    high Float64 COMMENT '最高点位',
    low Float64 COMMENT '最低点位',
    close Float64 COMMENT '收盘点位',
    volume Int64 COMMENT '成交量，单位股',
    turnover Float64 COMMENT '成交额，单位元',
    change_pct Float64 COMMENT '涨跌幅，单位%',
    data_source String COMMENT '数据源标识，如 akshare',
    created_at DateTime DEFAULT now() COMMENT '记录创建时间',
    updated_at DateTime DEFAULT now() COMMENT '记录更新时间'
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (index_code, trade_date)
SETTINGS index_granularity = 8192;

-- 7. 股票分红送股表
-- 记录股票的分红、送股、转增事件
CREATE TABLE IF NOT EXISTS stock_split
(
    stock_code String COMMENT '股票代码',
    trade_date Date COMMENT '除权除息日/红利发放日',
    event_type String COMMENT '事件类型：dividend=分红，split=送股，allot=配股',
    before_quantity Nullable(Float64) COMMENT '事件前持股数',
    after_quantity Nullable(Float64) COMMENT '事件后持股数',
    ratio_before Nullable(Float64) COMMENT '送股前比例（如每10股送X股）',
    ratio_after Nullable(Float64) COMMENT '送股后比例',
    data_source String COMMENT '数据源标识',
    created_at DateTime DEFAULT now() COMMENT '记录创建时间'
)
ENGINE = MergeTree()
ORDER BY (stock_code, trade_date)
SETTINGS index_granularity = 8192;
