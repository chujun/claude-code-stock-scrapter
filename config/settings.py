# config/settings.py
"""系统配置管理"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class ClickHouseSettings(BaseSettings):
    """ClickHouse配置"""
    host: str = "localhost"
    port: int = 9000
    database: str = "stock_scraper"
    user: str = "default"
    password: str = ""
    batch_size: int = 1024
    connect_timeout: int = 10
    send_receive_timeout: int = 30


class RateLimitSettings(BaseSettings):
    """请求限流配置"""
    base_interval: float = 1.0  # 基础请求间隔(秒)
    max_interval: float = 10.0  # 最大间隔(秒)
    increase_factor: float = 1.5  # 失败后增加倍数
    full_sync_interval: float = 1.0  # 全量同步间隔(秒)
    incremental_sync_interval: float = 0.8  # 增量同步间隔(秒)


class DataSourceSettings(BaseSettings):
    """数据源配置"""
    name: str = "akshare"
    rate_limit: RateLimitSettings = RateLimitSettings()


class SyncSettings(BaseSettings):
    """同步配置"""
    batch_size: int = 1024
    max_retries: int = 3
    retry_base_delay: float = 2.0
    retry_max_delay: float = 60.0
    exponential_base: int = 2


class SchedulerSettings(BaseSettings):
    """调度器配置"""
    daily_sync_hour: int = 16
    daily_sync_minute: int = 0
    enabled: bool = True


class AlertThresholdSettings(BaseSettings):
    """告警阈值配置"""
    error_rate: float = 0.05
    consecutive_failures: int = 10


class ReportSettings(BaseSettings):
    """报告配置"""
    output_dir: str = "reports"
    alert_file: str = "/data/logs/alerts.log"
    alert_threshold: AlertThresholdSettings = AlertThresholdSettings()


class QualitySettings(BaseSettings):
    """质量校验配置"""
    change_pct_limit: float = 10.0
    st_change_pct_limit: float = 20.0
    new_stock_change_pct_limit: float = 20.0


class Settings(BaseSettings):
    """系统配置"""
    clickhouse: ClickHouseSettings = ClickHouseSettings()
    data_source: DataSourceSettings = DataSourceSettings()
    sync: SyncSettings = SyncSettings()
    scheduler: SchedulerSettings = SchedulerSettings()
    report: ReportSettings = ReportSettings()
    quality: QualitySettings = QualitySettings()

    @classmethod
    def from_yaml(cls, config_path: str = "config.yaml") -> "Settings":
        """从YAML文件加载配置"""
        path = Path(config_path)
        if path.exists():
            with open(path, "r") as f:
                config_data = yaml.safe_load(f)
            return cls(**config_data)
        return cls()

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量加载配置"""
        return cls()


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    config_path = os.environ.get("CONFIG_PATH", "config.yaml")
    if Path(config_path).exists():
        return Settings.from_yaml(config_path)
    return Settings.from_env()
