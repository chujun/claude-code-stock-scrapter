# 技术调研报告：股票日线数据批量获取

**调研日期**: 2026-03-25
**调研人**: Claude Code
**调研目的**:
1. 测试单只股票近20年日线数据获取方式（分页 vs 一次性）
2. 调研是否存在按指定日期批量获取多只股票的接口

---

## 一、调研结论

### 1.1 单只股票近20年日线数据获取

| 时间范围 | 记录数 | 内部分页数 | 耗时 |
|---------|--------|-----------|------|
| 1年 | 242条 | 2页 | 1.5秒 |
| 5年 | 1,210条 | 6页 | 3.0秒 |
| 10年 | 2,427条 | 11页 | 4.8秒 |
| 20年 | 4,773条 | 21页 | 8.9秒 |
| 全量(1990-) | 6,270条 | 28页 | 11.5秒 |

**结论**:

- **支持一次性获取** - 腾讯接口(`stock_zh_a_hist_tx`)内部自动完成分页
- **调用方式简单** - 只需传入`start_date`和`end_date`参数，接口自动处理分页请求
- **无分页限制** - 可以直接请求全量历史数据，无需开发者分批获取
- **建议** - 对于全量同步场景，可直接请求`19900101`到当前日期，一次性获取所有历史数据

### 1.2 按指定日期批量获取多只股票

**结论: 不支持**

- akshare **没有** 提供按指定日期批量获取多只股票日线数据的接口
- 只能通过`stock_zh_a_spot_em`获取**今日实时行情**（约5493条），但该接口当前被代理屏蔽
- 必须逐只股票调用`stock_zh_a_hist_tx`接口获取历史数据

**可用接口一览**:

| 接口 | 功能 | 状态 |
|------|------|------|
| `stock_zh_a_hist_tx` | 单只股票日线数据 | ✅ 正常 |
| `stock_zh_a_spot_em` | 所有A股今日实时行情 | ❌ 被屏蔽 |
| `stock_info_a_code_name` | 获取所有股票列表 | ✅ 正常 |

---

## 二、测试详情

### 2.1 测试环境

- **测试股票**: 浦发银行 (600000)
- **接口**: `akshare.stock_zh_a_hist_tx`
- **复权类型**: 前复权 (qfq)
- **网络环境**: 受代理限制，部分接口不可用

### 2.2 分页机制分析

腾讯接口内部自动分页，分页逻辑由接口控制：

```
请求: start_date=20050101, end_date=20260325
内部:
  - 第1次请求: 获取第1页数据
  - 第2次请求: 获取第2页数据
  - ... (共21次内部请求)
  - 合并返回所有数据
输出: DataFrame (5050条记录)
```

**分页粒度**: 约每250条记录为1页

### 2.3 批量接口测试

```python
# 测试1: 腾讯接口多只股票 (传入列表)
ak.stock_zh_a_hist_tx(symbol=['sh600000', 'sz000001'], ...)
# 结果: TypeError - 不支持列表

# 测试2: 东方财富接口
ak.stock_zh_a_hist(symbol='000001', ...)
# 结果: Connection aborted - 被代理屏蔽

# 测试3: 雪球接口
ak.stock_individual_basic_info_xq(symbol='sh600000')
# 结果: 可用，但只返回实时快照，无历史数据
```

---

## 三、优化建议

### 3.1 全量同步优化

**现状**: 当前按5天/次同步，每次请求只获取少量数据

**优化方案**:

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| 方案A | 直接请求全量历史数据 | 减少API调用次数 | 单次耗时较长(11秒) |
| 方案B | 按年分段请求 | 平衡单次耗时 | 增加API调用 |
| 方案C | 保持现状 | 实现简单 | 调用次数多 |

**推荐**: 方案A - 全量同步场景下，直接请求20年数据，减少API调用次数

### 3.2 北交所股票优化

**现状**: 同步时会尝试获取北交所股票(8开头)，但返回"北交所股票暂不支持"

**优化**: 在代码中直接跳过北交所股票

```python
# 当前实现
if stock_code.startswith("920"):
    return []  # 920开头才跳过

# 建议修改为
if stock_code.startswith("9"):  # 所有9开头都跳过
    return []
```

**节省时间**: 约5分钟 (309只北交所股票 × 1秒)

### 3.3 并行同步

由于必须逐只获取，可以考虑并发：

```python
# 伪代码示例
async def parallel_sync(stock_codes: List[str], concurrency: int = 10):
    semaphore = asyncio.Semaphore(concurrency)

    async def sync_one(code):
        async with semaphore:
            return await client.get_daily(code, start_date, end_date)

    tasks = [sync_one(code) for code in stock_codes]
    return await asyncio.gather(*tasks)
```

**注意**: 需要评估并发对防爬机制的影响

---

## 四、相关代码

### 4.1 当前获取日线数据实现

```python
# data_source/akshare_client.py

async def get_daily(
    self,
    stock_code: str,
    start_date: date,
    end_date: date,
    adjust_type: str = "qfq"
) -> List[StockDaily]:
    # 北交所股票跳过
    if stock_code.startswith("920"):
        return []

    symbol_with_prefix = f"sh{stock_code}" if stock_code.startswith(("6", "9")) else f"sz{stock_code}"

    df = await self._run_sync(
        ak.stock_zh_a_hist_tx,
        symbol=symbol_with_prefix,
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
        adjust=adjust_map[adjust_type]
    )
    # ... 转换逻辑
```

### 4.2 批量获取股票列表

```python
# 获取所有股票列表 (约10秒)
df = await self._run_sync(ak.stock_info_a_code_name)
# 返回: 5493条记录 ['code', 'name']
```

---

## 五、后续行动

- [ ] 评估全量同步优化方案的可行性
- [ ] 修改北交所股票跳过逻辑(支持所有9开头)
- [ ] 测试并行同步对防爬的影响
- [ ] 更新同步策略文档

---

## 六、参考资料

- [AKShare文档](https://www.akshare.xyz/)
- 腾讯财经日线接口内部实现
- 项目现有代码: `data_source/akshare_client.py`
