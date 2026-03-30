-- storage/migrations/003_stock_financial_risk.sql
-- 股票财务风险表
-- 数据来源：同花顺网站 (ths)

CREATE TABLE IF NOT EXISTS stock_financial_risk
(
    stock_code String COMMENT '股票代码，如 600000、000001',
    trade_date Date COMMENT '交易日期',
    total_risk Int32 COMMENT '总风险数量',
    no_risk Int32 COMMENT '无风险数量',
    low_risk Int32 COMMENT '低风险数量',
    medium_risk Int32 COMMENT '中等风险数量',
    high_risk Int32 COMMENT '高风险数量',
    data_source String DEFAULT 'ths' COMMENT '数据来源，同花顺=ths',
    created_at DateTime DEFAULT now() COMMENT '记录创建时间',
    updated_at DateTime DEFAULT now() COMMENT '记录更新时间'
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (stock_code, trade_date)
SETTINGS index_granularity = 8192;
