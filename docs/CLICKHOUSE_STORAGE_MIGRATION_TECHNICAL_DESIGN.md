# ClickHouse 磁盘存储迁移技术方案

## 1. 背景与问题

### 1.1 问题描述

当前 ClickHouse 数据库存储在根分区 `/var/lib/clickhouse/`，随着数据量增长，根分区使用率持续攀升，存在磁盘空间不足风险。

### 1.2 当前状态

| 项目 | 现状 |
|------|------|
| 数据路径 | `/var/lib/clickhouse/` |
| 根分区容量 | 9.8G |
| 根分区已用 | 7.9G (86%) |
| 根分区可用 | 1.4G |
| ClickHouse数据量 | ~4MB (stock_daily: 3.64MiB, stock_info: 154.62KiB) |

### 1.3 目标

将 ClickHouse 数据存储迁移至新挂载的 `/data` 磁盘（20G），释放根分区空间。

---

## 2. 存储架构分析

### 2.1 ClickHouse 存储结构

```
/var/lib/clickhouse/
├── access/          # 用户权限数据
├── data/            # 数据存储（符号链接目标）
├── flags/           # 运行标记
├── format_schemas/  # 格式化模式
├── metadata/        # 表结构定义
├── metadata_dropped/# 已删除表元数据
├── preprocessed_configs/
├── store/           # 主数据存储目录
├── tmp/             # 临时文件
├── user_files/      # 用户文件
├── uuid
└── status
```

### 2.2 现有磁盘布局

| 挂载点 | 设备 | 容量 | 已用 | 可用 | 用途 |
|--------|------|------|------|------|------|
| `/` | /dev/mapper/ubuntu--vg-ubuntu--lv | 9.8G | 7.9G | 1.4G | 系统、ClickHouse数据 |
| `/data` | /dev/sdb1 | 20G | 1.7M | 19G | 新增数据盘 |

### 2.3 ClickHouse 日志配置

日志已单独配置在 `/data/logs/clickhouse/`：

```xml
<!-- /etc/clickhouse-server/config.d/custom-log.xml -->
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

---

## 3. 迁移方案对比

### 3.1 方案对比表

| 方案 | 描述 | 优点 | 缺点 | 适用场景 |
|------|------|------|------|----------|
| **软链接方式** | 将数据复制到新路径，原目录作为软链接 | 改动最小、回滚简单、迁移快速 | 需要保证软链接路径稳定 | **推荐：数据量小(<100GB)** |
| 修改存储路径 | 直接修改 ClickHouse 配置中的 `path` 参数 | 完全符合官方推荐 | 需要修改多个配置文件、回滚复杂 | 需要彻底迁移的场景 |
| 硬链接方式 | 使用 `ln` 创建硬链接 | 无需停机、可回滚 | 仅限同一文件系统、不适合跨盘迁移 | 不推荐 |
| LVM快照 | 使用LVM快照零停机迁移 | 停机时间最短 | 配置复杂、需要预留LVM空间 | 企业级、大数据量场景 |

### 3.2 方案选择

**推荐采用软链接方式**，原因如下：

1. **数据量小**：当前仅~4MB，迁移时间短
2. **风险可控**：回滚只需删除软链接
3. **改动最小**：无需修改 ClickHouse 核心配置
4. **验证充分**：该方案在 ClickHouse 社区广泛使用

---

## 4. 技术方案设计

### 4.1 迁移路径规划

```
源路径: /var/lib/clickhouse/store/
目标路径: /data/clickhouse/data/
链接路径: /var/lib/clickhouse/store -> /data/clickhouse/data
```

### 4.2 迁移后存储布局

```
迁移后结构:

/data/
└── clickhouse/
    └── data/                    # 主数据存储 (软链接目标)
        ├── 05f/
        ├── 099/
        ├── 18d/
        └── ... (原有数据目录)

/var/lib/clickhouse/
├── access/
├── data/ -> /data/clickhouse/data  (软链接)
├── flags/
├── format_schemas/
├── metadata/
├── metadata_dropped/
├── preprocessed_configs/
├── store -> /data/clickhouse/data  (软链接)
├── tmp/
├── user_files/
├── uuid
└── status
```

### 4.3 关键配置参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `clickhouse.path` | `/var/lib/clickhouse/` | 主数据路径(包含store子目录) |
| `clickhouse.store` | 自动解析为软链接目标 | 数据实际存储位置 |
| `logger.log` | `/data/logs/clickhouse/clickhouse-server.log` | 日志路径(已配置) |

### 4.4 权限要求

```bash
# 数据目录所有者
chown -R clickhouse:clickhouse /data/clickhouse

# 权限要求
drwxr-x---  clickhouse:clickhouse  /data/clickhouse
drwxr-x---  clickhouse:clickhouse  /data/clickhouse/data
```

---

## 5. 数据完整性保障

### 5.1 迁移前校验

```sql
-- 记录数据量
SELECT database, table, formatReadableSize(total_bytes) as size
FROM system.tables
WHERE database IN ('default', 'stock_scraper');

-- 记录记录数
SELECT 'stock_daily' as tbl, count() as cnt FROM stock_scraper.stock_daily;
SELECT 'stock_info' as tbl, count() as cnt FROM stock_scraper.stock_info;
```

### 5.2 迁移后验证

```sql
-- 验证数据一致性
SELECT database, table, formatReadableSize(total_bytes) as size
FROM system.tables
WHERE database IN ('default', 'stock_scraper');

-- 验证记录数一致
SELECT 'stock_daily' as tbl, count() as cnt FROM stock_scraper.stock_daily;
SELECT 'stock_info' as tbl, count() as cnt FROM stock_scraper.stock_info;

-- 验证新数据写入正常
INSERT INTO stock_scraper.stock_info (...) VALUES (...);
```

### 5.3 迁移过程数据一致性保证

1. **停止服务**：确保迁移期间无写入
2. **原子操作**：软链接创建为原子操作
3. **备份原目录**：保留原目录作为备份
4. **增量验证**：每步操作后验证

---

## 6. 回滚方案

### 6.1 回滚触发条件

- ClickHouse 无法启动
- 数据丢失或损坏
- 查询报错频发

### 6.2 回滚步骤

```bash
# 1. 停止服务
sudo systemctl stop clickhouse-server

# 2. 移除软链接
sudo rm /var/lib/clickhouse/store

# 3. 恢复原数据
sudo mv /var/lib/clickhouse/store.bak /var/lib/clickhouse/store

# 4. 重启服务
sudo systemctl start clickhouse-server

# 5. 验证
clickhouse-client --query "SELECT count() FROM stock_scraper.stock_daily"
```

### 6.3 回滚检查清单

- [ ] 服务启动成功
- [ ] 数据记录数与迁移前一致
- [ ] 可以正常查询
- [ ] 无错误日志

---

## 7. 监控与告警

### 7.1 监控指标

| 指标 | 阈值 | 告警级别 |
|------|------|----------|
| `/` 根分区使用率 | >90% | 严重 |
| `/data` 使用率 | >90% | 严重 |
| ClickHouse 服务状态 | down | 严重 |

### 7.2 监控脚本示例

```bash
#!/bin/bash
# disk_monitor.sh

ROOT_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
DATA_USAGE=$(df /data | awk 'NR==2 {print $5}' | sed 's/%//')

if [ "$ROOT_USAGE" -gt 90 ]; then
    echo "ALERT: Root partition usage is ${ROOT_USAGE}%"
    # 发送告警通知
fi

if [ "$DATA_USAGE" -gt 90 ]; then
    echo "ALERT: /data partition usage is ${DATA_USAGE}%"
    # 发送告警通知
fi
```

---

## 8. 风险评估与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| 迁移失败 | 低 | 高 | 回滚方案、备份原目录 |
| 数据丢失 | 极低 | 极高 | rsync校验、迁移后验证 |
| 服务启动失败 | 低 | 中 | 检查日志、权限配置 |
| 软链接断裂 | 低 | 高 | 确保/data路径稳定、不被删除 |

---

## 9. 文档维护

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|----------|
| 1.0 | 2026-03-25 | Claude | 初始版本 |

---

## 10. 参考资料

- [ClickHouse Official Documentation - Data Storage](https://clickhouse.com/docs)
- [ClickHouse Symbolic Link Support](https://clickhouse.com/docs/en/operations/storage)
