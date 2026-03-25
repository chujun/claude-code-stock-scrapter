-- storage/migrations/002_add_skip_indexes.sql
-- A股股票数据爬虫系统 - 跳数索引优化
-- 创建时间: 2026-03-25
-- 说明: 为 stock_daily 表添加跳数索引，加速单股票查询和日期范围查询

-- =====================================================
-- 1. 股票代码跳数索引
-- 作用: 加速 WHERE stock_code = 'xxx' 类型查询
-- 原理: 在每个数据块(8192行)存储minmax统计，快速跳过不相关数据块
-- =====================================================
ALTER TABLE stock_scraper.stock_daily
    ADD INDEX idx_stock_code stock_code TYPE minmax;

-- =====================================================
-- 2. 交易日期跳数索引
-- 作用: 加速 WHERE trade_date BETWEEN ... 类型查询
-- 原理: 记录每个数据块的日期范围，支持日期分区裁剪
-- =====================================================
ALTER TABLE stock_scraper.stock_daily
    ADD INDEX idx_trade_date trade_date TYPE minmax;

-- =====================================================
-- 3. 为历史数据生成索引 (MATERIALIZE)
-- 注意: 此操作需扫描全表，建议在业务低峰期执行
-- 执行方式: 在ClickHouse客户端单独执行
-- =====================================================
-- ALTER TABLE stock_scraper.stock_daily MATERIALIZE INDEX idx_stock_code;
-- ALTER TABLE stock_scraper.stock_daily MATERIALIZE INDEX idx_trade_date;

-- =====================================================
-- 4. 验证索引是否创建成功
-- =====================================================
-- SELECT database, table, name, type, expr FROM system.skipping_indices
-- WHERE database = 'stock_scraper' AND table = 'stock_daily';
