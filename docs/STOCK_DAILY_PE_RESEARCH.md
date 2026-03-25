# 股票日线PE数据调研报告

## 1. 调研背景

项目需要获取A股股票的财务指标数据，包括：
- 市盈率（动态）
- 静态市盈率
- 滚动市盈率（TTM）
- 市净率
- 总市值
- 流通市值

本报告调研AKShare数据源是否支持获取上述指标的历史数据。

---

## 2. 调研方法

### 2.1 调研对象

| 数据源 | 接口名称 | 说明 |
|--------|---------|------|
| 腾讯财经 | `stock_zh_a_hist_tx` | 项目当前使用的日线数据接口 |
| 腾讯财经 | `stock_zh_a_daily` | 腾讯日线（含流通股本） |
| 东方财富 | `stock_individual_info_em` | 个股实时信息 |
| 雪球 | `stock_individual_basic_info_xq` | 雪球基础信息 |
| 全市场 | `stock_a_ttm_lyr` | A股TTM/LYR市盈率 |
| 全市场 | `stock_a_all_pb` | A股市净率 |

### 2.2 测试环境

- Python 3.12
- AKShare version: 最新版本
- 测试股票：600000（浦发银行）
- 测试日期范围：2024-01-02 ~ 2024-01-10

---

## 3. 测试结果

### 3.1 腾讯财经日线接口

#### `stock_zh_a_hist_tx`（项目当前使用）

```
字段列表: ['date', 'open', 'close', 'high', 'low', 'amount']

示例数据:
| date       | open | close | high | low  | amount   |
|------------|------|-------|------|------|----------|
| 2024-01-02 | 5.90 | 5.87  | 5.92 | 5.87 | 220667.0 |
| 2024-01-03 | 5.86 | 5.91  | 5.92 | 5.86 | 182037.0 |
```

**结论**: ❌ 不包含PE、市值、市净率字段

---

#### `stock_zh_a_daily`（腾讯日线增强版）

```
字段列表: ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'outstanding_share', 'turnover']

示例数据:
| date       | open | high  | low  | close | volume    | amount       | outstanding_share | turnover |
|------------|------|-------|------|-------|-----------|--------------|-------------------|----------|
| 2024-01-02 | 6.63 | 6.65  | 6.59 | 6.60  | 20880400.0 | 146066304.0  | 2.935218e+10      | 0.000752 |
```

**结论**: ⚠️ 包含流通股本(outstanding_share)，可计算流通市值，但无PE字段

---

### 3.2 雪球财经接口

#### `stock_individual_basic_info_xq`

```
字段列表:
| item                    | value                                      |
|-------------------------|--------------------------------------------|
| org_name_cn             | 上海浦东发展银行股份有限公司                |
| pe_after_issuing        | 26.3                                       |
| ...                                             |
```

**结论**: ⚠️ 仅返回 `pe_after_issuing`（发行市盈率），非动态/静态/TTM市盈率

---

### 3.3 全市场PE/PB接口

#### `stock_a_ttm_lyr`（市场TTM/LYR PE）

```
字段列表: ['date', 'middlePETTM', 'close', 'quantileInRecent10YearsAveragePeLyr', ...]

示例数据:
| date       | middlePETTM | close |
|------------|-------------|-------|
| 2005-01-05 | 28.79       | 0.0   |
| 2005-01-06 | 29.18       | 0.0   |
```

**结论**: ✅ 有PE数据，但是**全市场整体PE**，非个股PE

---

#### `stock_a_all_pb`（市场市净率）

```
字段列表: ['date', 'middlePB', 'equalWeightAveragePB', 'close', ...]
```

**结论**: ✅ 有PB数据，但是**全市场整体PB**，非个股PB

---

### 3.4 东方财富接口

#### `stock_individual_info_em`

```
字段列表:
| item   | value                  |
|--------|------------------------|
| 最新   | 10.04                  |
| 总市值 | 334390616532.0         |
| 流通市值 | 334390616532.0       |
| 市盈率 | XX.XX                  |
| ...    | ...                    |
```

**结论**: ✅ 有PE和市值，但该接口在当前网络环境下**被屏蔽**（Connection Aborted）

---

## 4. 数据可用性分析

### 4.1 个股历史PE

| 类型 | 可获取性 | 说明 |
|------|---------|------|
| 动态市盈率 | ❌ 不可获取 | AKShare无此接口 |
| 静态市盈率 | ❌ 不可获取 | AKShare无此接口 |
| 滚动市盈率(TTM) | ❌ 不可获取 | AKShare无此接口 |
| 市净率 | ❌ 不可获取 | AKShare无个股历史PB |

**原因**: 国内股票数据监管限制，PE/PB等估值数据通常需要付费数据源支持。

---

### 4.2 可替代方案

#### 方案A：使用腾讯日线数据计算流通市值

腾讯日线接口(`stock_zh_a_daily`)提供 `outstanding_share`（流通股本），可计算流通市值：

```python
float_market_cap = outstanding_share × close_price
```

**注意**: 总市值需要总股本，腾讯接口未提供。

---

#### 方案B：调用实时API获取当前PE

每次同步日线数据后，调用 `get_financial_indicator_async()` 获取当前PE，填充到**最新一条记录**。

**缺点**:
- 非真正历史PE
- 同一交易日内PE可能随股价变化
- 覆盖率低（接口不稳定）

---

#### 方案C：切换到专业数据源

| 数据源 | 说明 |
|--------|------|
| Tushare Pro | 付费数据源，提供完整历史PE/PB |
| 聚宽 | 付费数据源，提供完整历史PE/PB |
| 万得(Wind) | 专业机构数据源，数据最全面 |

---

## 5. 当前系统现状

### 5.1 数据库字段设计

`stock_daily` 表已设计PE相关字段：

```sql
total_market_cap Nullable(Float64)  -- 总市值，单位元（当前未采集）
float_market_cap Nullable(Float64)  -- 流通市值，单位元（当前未采集）
pe_ratio Nullable(Float64)          -- 市盈率(静动态)（当前未采集）
static_pe Nullable(Float64)         -- 静态市盈率（当前未采集）
dynamic_pe Nullable(Float64)        -- 动态市盈率（当前未采集）
pb_ratio Nullable(Float64)          -- 市净率（当前未采集）
```

### 5.2 现有获取方法

`AkshareClient` 类已有 `get_financial_indicator_async()` 方法：

```python
async def get_financial_indicator_async(self, stock_code: str) -> dict:
    """获取股票财务指标"""
    # 优先使用雪球API
    df = ak.stock_individual_basic_info_xq(symbol=symbol)
    # 解析 pe_after_issuing

    # 备用东方财富API
    df = ak.stock_individual_info_em(symbol=stock_code)
    # 解析 市盈率、静态市盈率、动态市盈率、市净率、总市值、流通市值
```

**问题**: 东方财富接口被屏蔽，雪球仅返回发行PE。

---

## 6. 结论与建议

### 6.1 结论

| 数据项 | 可获取性 | 推荐方案 |
|--------|---------|---------|
| 动态市盈率 | ❌ 不可获取 | 使用实时PE填充 |
| 静态市盈率 | ❌ 不可获取 | 使用实时PE填充 |
| 滚动市盈率(TTM) | ❌ 不可获取 | 使用实时PE填充 |
| 市净率 | ❌ 不可获取 | 使用实时数据填充 |
| 总市值 | ⚠️ 部分可获取 | 东方财富实时API（不稳定） |
| 流通市值 | ✅ 可计算 | 腾讯日线 `outstanding_share × close` |

### 6.2 建议

1. **短期方案**: 利用腾讯日线接口的 `outstanding_share` 字段计算流通市值，调用实时API获取当前PE（仅填充最新记录）

2. **中期方案**: 接入Tushare Pro等付费数据源，获取完整历史PE/PB数据

3. **数据标注**: 在数据库字段注释中明确标注"实时快照，非历史数据"，避免误导

---

## 7. 附录

### 7.1 测试代码

```python
import akshare as ak

# 腾讯日线
df = ak.stock_zh_a_hist_tx(symbol='sh600000', start_date='20240101', end_date='20240110', adjust='qfq')
print(df.columns.tolist())  # ['date', 'open', 'close', 'high', 'low', 'amount']

# 腾讯日线增强版
df = ak.stock_zh_a_daily(symbol='sh600000', start_date='20240101', end_date='20240110')
print(df.columns.tolist())  # ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'outstanding_share', 'turnover']

# 雪球
df = ak.stock_individual_basic_info_xq(symbol='SH600000')
print(df)  # pe_after_issuing: 26.3
```

### 7.2 修改历史

| 日期 | 修改内容 |
|------|---------|
| 2026-03-25 | 初始文档创建 |

---

**文档信息**
- 创建日期: 2026-03-25
- 调研人: Claude Code AI
- 项目: A股股票数据爬虫系统
