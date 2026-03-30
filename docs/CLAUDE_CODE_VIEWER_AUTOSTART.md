# Claude Code Viewer 服务自启动配置方案

## 概述

本文档描述了如何将 Claude Code Viewer 配置为 systemd 用户服务，实现开机自启动并允许宿主机访问。

## 环境信息

- 操作系统：Linux (Ubuntu)
- 用户：root
- Node.js 版本：v24.14.0
- Claude Code Viewer 版本：0.6.0
- 服务端口：3400

## 服务配置

### systemd 用户服务文件

路径：`/root/.config/systemd/user/claude-code-viewer.service`

```ini
[Unit]
Description=Claude Code Viewer
After=network.target

[Service]
ExecStart=/root/.nvm/versions/node/v24.14.0/bin/claude-code-viewer -p 3400 -h 0.0.0.0
Restart=on-failure
RestartSec=5
Environment="PATH=/root/.nvm/versions/node/v24.14.0/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
Environment=HOME=/root

[Install]
WantedBy=default.target
```

### 关键配置说明

| 配置项 | 说明 |
|--------|------|
| `ExecStart` | 使用 nvm 管理的 Node.js 路径 |
| `-h 0.0.0.0` | 绑定所有网络接口，允许多宿主机访问 |
| `Restart=on-failure` | 进程异常退出时自动重启 |
| `Environment` | 设置 PATH 和 HOME 环境变量 |

## 实施步骤

### 1. 创建服务目录

```bash
mkdir -p /root/.config/systemd/user
```

### 2. 创建服务文件

将上述配置写入 `/root/.config/systemd/user/claude-code-viewer.service`

### 3. 重新加载 systemd

```bash
systemctl --user daemon-reload
```

### 4. 启用服务（开机自启动）

```bash
systemctl --user enable claude-code-viewer
```

### 5. 启动服务

```bash
systemctl --user start claude-code-viewer
```

### 6. 启用 linger（关键步骤）

对于 root 用户的 systemd 用户服务，必须启用 linger 才能实现开机自启动：

```bash
loginctl enable-linger root
```

### 7. 验证服务状态

```bash
# 查看服务状态
systemctl --user status claude-code-viewer

# 查看端口监听
ss -tlnp | grep 3400

# 查看实时日志
journalctl --user -u claude-code-viewer -f
```

## 验证结果

- 服务状态：`active (running)`
- 监听地址：`0.0.0.0:3400`（宿主机可访问）
- Linger 状态：`yes`

## 常用命令

```bash
# 查看状态
systemctl --user status claude-code-viewer

# 启动服务
systemctl --user start claude-code-viewer

# 停止服务
systemctl --user stop claude-code-viewer

# 重启服务
systemctl --user restart claude-code-viewer

# 查看日志
journalctl --user -u claude-code-viewer -f

# 禁用开机自启动
systemctl --user disable claude-code-viewer
```

## 访问方式

在宿主机浏览器中访问：`http://<服务器IP>:3400`
