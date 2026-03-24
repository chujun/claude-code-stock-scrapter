#!/bin/bash
# 磁盘空间自动清理脚本
# 定期清理日志、临时文件和旧数据

LOG_FILE="/var/log/disk_cleanup.log"
THRESHOLD=85  # 磁盘使用率阈值(%)

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG_FILE
}

check_disk() {
    df -h / | awk 'NR==2 {print $5}' | sed 's/%//'
}

cleanup_logs() {
    log "开始清理日志文件..."

    # 轮转 syslog
    /usr/sbin/logrotate -f /etc/logrotate.conf 2>/dev/null

    # 清理旧的压缩日志（超过7天）
    find /var/log -name "*.gz" -mtime +7 -delete 2>/dev/null

    # 清理 journal 日志（保留最近50M）
    journalctl --vacuum-size=50M 2>/dev/null

    # 清理项目日志（保留最近3个）
    for logfile in /root/ai/claudecode/first/stock-scraper/logs/*.log; do
        if [ -f "$logfile" ]; then
            # 只保留最近100行
            tail -n 100 "$logfile" > "${logfile}.tmp" 2>/dev/null
            mv "${logfile}.tmp" "$logfile"
        fi
    done

    log "日志清理完成"
}

cleanup_temp() {
    log "清理临时文件..."

    # 清理 pip 缓存
    pip cache purge 2>/dev/null

    # 清理旧报告（超过30天）
    find /root/ai/claudecode/first/stock-scraper/reports -name "*.json" -mtime +30 -delete 2>/dev/null

    # 清理会话文件
    find /root/ai/claudecode/first/stock-scraper -name "*-continued-*.txt" -mtime +7 -delete 2>/dev/null

    log "临时文件清理完成"
}

# 主流程
USAGE=$(check_disk)
log "磁盘清理开始 - 当前使用率: ${USAGE}%"

if [ "$USAGE" -gt "$THRESHOLD" ]; then
    log "磁盘使用率超过 ${THRESHOLD}%，执行清理..."
    cleanup_logs
    cleanup_temp
else
    log "磁盘使用率正常，跳过清理"
fi

# 清理后再次检查
AFTER=$(check_disk)
log "清理完成 - 当前使用率: ${AFTER}%"
