# ClickHouse 磁盘存储迁移实施方案

## 1. 概述

本文档描述将 ClickHouse 数据存储从根分区迁移至 `/data` 磁盘的具体操作步骤。

**前置条件**：
- 新磁盘已挂载于 `/data`
- ClickHouse 已安装并正常运行
- 当前数据量 < 1GB

**预计停机时间**：5-10分钟

---

## 2. 迁移前准备

### 2.1 记录当前状态

```bash
# 记录数据量和记录数
clickhouse-client --query "SELECT database, table, formatReadableSize(total_bytes) as size FROM system.tables WHERE database IN ('default', 'stock_scraper') ORDER BY total_bytes DESC"
```

**预期输出**：
```
database         table           size
stock_scraper    stock_daily     3.64 MiB
stock_scraper    stock_info      154.62 KiB
```

```bash
# 记录关键记录数
clickhouse-client --query "SELECT 'stock_daily' as tbl, count() as cnt FROM stock_scraper.stock_daily"
clickhouse-client --query "SELECT 'stock_info' as cnt, count() as cnt FROM stock_scraper.stock_info"
```

**预期输出**：
```
stock_daily    108716
stock_info     10984
```

### 2.2 检查磁盘空间

```bash
# 检查当前磁盘使用情况
df -h

# 预期输出：
# Filesystem                         Size  Used Avail Use% Mounted on
# /dev/mapper/ubuntu--vg-ubuntu--lv  9.8G  7.9G  1.4G  86% /
# /dev/sdb1                           20G  1.7M   19G   1% /data
```

### 2.3 检查服务状态

```bash
# 确认 ClickHouse 服务正常运行
sudo systemctl status clickhouse-server --no-pager
```

**预期输出**：
```
● clickhouse-server.service - ClickHouse Server (analytic DBMS for big data)
     Loaded: loaded (/usr/lib/systemd/system/clickhouse-server.service)
     Active: active (running)
```

---

## 3. 迁移步骤

### 步骤 1：停止 ClickHouse 服务

```bash
sudo systemctl stop clickhouse-server
```

**验证**：
```bash
sudo systemctl status clickhouse-server --no-pager
# 确认状态为 inactive (dead)
```

### 步骤 2：创建目标目录

```bash
sudo mkdir -p /data/clickhouse/data
sudo chown -R clickhouse:clickhouse /data/clickhouse
```

**验证**：
```bash
ls -la /data/clickhouse/
# 预期输出：
# drwxr-x--- 2 clickhouse clickhouse 4096 Mar 25 01:17 .
# drwxr-xr-x  3 root root   4096 Mar 25 01:17 ..
# drwxr-x--- 2 clickhouse clickhouse 4096 Mar 25 01:17 data
```

### 步骤 3：迁移数据

使用 `rsync` 复制数据，保留权限和属性：

```bash
rsync -av /var/lib/clickhouse/store/ /data/clickhouse/data/
```

**参数说明**：
- `-a`：归档模式，保留权限、时间戳等
- `-v`：详细输出

**验证**：
```bash
# 检查复制后的数据量
du -sh /data/clickhouse/data/

# 预期输出：
# 440M    /data/clickhouse/data/

# 确认目录结构
ls -la /data/clickhouse/data/ | head -10
```

### 步骤 4：备份原数据

```bash
sudo mv /var/lib/clickhouse/store /var/lib/clickhouse/store.bak
```

**验证**：
```bash
ls -la /var/lib/clickhouse/ | grep store
# 预期输出：
# drwx------ 12 clickhouse clickhouse  4096 Mar 24 08:46 store.bak
```

### 步骤 5：创建软链接

```bash
sudo ln -s /data/clickhouse/data /var/lib/clickhouse/store
```

**验证**：
```bash
ls -la /var/lib/clickhouse/store
# 预期输出：
# lrwxrwxrwx 1 root root 21 Mar 25 01:17 /var/lib/clickhouse/store -> /data/clickhouse/data

# 确认软链接指向正确
readlink -f /var/lib/clickhouse/store
# 预期输出：
# /data/clickhouse/data
```

### 步骤 6：启动 ClickHouse 服务

```bash
sudo systemctl start clickhouse-server
```

**验证**：
```bash
sudo systemctl status clickhouse-server --no-pager
# 确认状态为 active (running)
```

---

## 4. 迁移后验证

### 4.1 服务状态验证

```bash
# 检查服务状态
sudo systemctl status clickhouse-server --no-pager

# 检查 ClickHouse 进程
ps aux | grep clickhouse | grep -v grep
```

### 4.2 数据完整性验证

```bash
# 验证数据量
clickhouse-client --query "SELECT database, table, formatReadableSize(total_bytes) as size FROM system.tables WHERE database IN ('default', 'stock_scraper') ORDER BY total_bytes DESC"
```

**预期输出**（与迁移前一致）：
```
database         table           size
stock_scraper    stock_daily     3.64 MiB
stock_scraper    stock_info      154.62 KiB
```

### 4.3 记录数验证

```bash
# 验证 stock_daily 记录数
clickhouse-client --query "SELECT count() FROM stock_scraper.stock_daily"
# 预期输出：108716

# 验证 stock_info 记录数
clickhouse-client --query "SELECT count() FROM stock_scraper.stock_info"
# 预期输出：10984
```

### 4.4 新写入验证

```bash
# 测试新数据写入
clickhouse-client --query "
INSERT INTO stock_scraper.stock_info
(stock_code, stock_name, market, industry, list_date, stock_type, status)
VALUES
('TEST001', '测试股票', 'SSE', '测试行业', '20200101', 'common', 'active')
"

# 验证写入成功
clickhouse-client --query "
SELECT stock_code, stock_name FROM stock_scraper.stock_info
WHERE stock_code = 'TEST001'
"

# 清理测试数据
clickhouse-client --query "
ALTER TABLE stock_scraper.stock_info
DELETE WHERE stock_code = 'TEST001'
"
```

### 4.5 存储路径验证

```bash
# 确认数据实际存储在新路径
ls -la /data/clickhouse/data/ | head -10

# 确认根目录无数据（只有软链接）
du -sh /var/lib/clickhouse/store
# 预期输出（软链接大小）：
# 4 /var/lib/clickhouse/store
```

### 4.6 磁盘空间验证

```bash
# 检查磁盘使用情况
df -h

# 预期输出：
# /dev/mapper/ubuntu--vg-ubuntu--lv  9.8G  7.9G  1.4G  86% /      # 根分区未变化
# /dev/sdb1                           20G  441M   19G   3% /data   # 新路径有数据
```

---

## 5. 清理

### 5.1 确认迁移成功

执行以下检查确认迁移完全成功：

- [ ] ClickHouse 服务正常运行
- [ ] 数据记录数与迁移前一致
- [ ] 新数据可以正常写入
- [ ] `/data` 磁盘有数据存储

### 5.2 删除备份

确认所有功能正常后，删除备份目录：

```bash
sudo rm -rf /var/lib/clickhouse/store.bak
```

**警告**：只有在完全确认迁移成功后才能执行此操作。

---

## 6. 回滚操作

### 6.1 回滚条件

如果迁移后出现以下问题，执行回滚：

- ClickHouse 服务无法启动
- 数据丢失或损坏
- 查询报错

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
# 预期输出：108716
```

---

## 7. 验证检查清单

### 迁移前检查

- [ ] 记录当前数据量
- [ ] 记录关键表记录数
- [ ] 确认服务正常运行
- [ ] 确认 /data 磁盘可写

### 迁移后检查

- [ ] ClickHouse 服务启动成功
- [ ] 服务状态为 active (running)
- [ ] 数据量与迁移前一致
- [ ] stock_daily 记录数：108716
- [ ] stock_info 记录数：10984
- [ ] 新数据写入正常
- [ ] /data 磁盘有数据存储
- [ ] 根分区空间未减少

### 最终确认

- [ ] 删除备份目录
- [ ] 监控脚本配置完成
- [ ] 文档更新完成

---

## 8. 实际操作记录

以下为本次迁移的实际操作记录：

```
# 迁移时间：2026-03-25 01:17 UTC

# 1. 停止服务
$ sudo systemctl stop clickhouse-server

# 2. 创建目标目录
$ sudo mkdir -p /data/clickhouse/data
$ sudo chown -R clickhouse:clickhouse /data/clickhouse

# 3. 迁移数据
$ rsync -av /var/lib/clickhouse/store/ /data/clickhouse/data/
# 传输了 440M 数据

# 4. 备份原数据
$ sudo mv /var/lib/clickhouse/store /var/lib/clickhouse/store.bak

# 5. 创建软链接
$ sudo ln -s /data/clickhouse/data /var/lib/clickhouse/store

# 6. 启动服务
$ sudo systemctl start clickhouse-server

# 验证结果：
# - 服务状态：active (running)
# - stock_daily: 108716 条记录
# - stock_info: 10984 条记录
# - /data 磁盘使用：441M
```

---

## 9. 文档信息

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|----------|
| 1.0 | 2026-03-25 | Claude | 初始版本 |
