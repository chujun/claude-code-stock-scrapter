# models/sync_status.py
"""同步状态记录模型"""

from datetime import date, datetime
from typing import Optional

from pydantic import Field, ConfigDict

from models.base import BaseModel


class SyncStatus(BaseModel):
    """同步状态记录"""

    model_config = ConfigDict(from_attributes=True)

    stock_code: Optional[str] = Field(
        None,
        description="股票代码，null表示全量任务"
    )
    sync_type: str = Field(
        ...,
        description="同步类型，full/daily/init"
    )
    last_sync_date: Optional[date] = Field(
        None,
        description="最后同步日期"
    )
    status: str = Field(
        ...,
        description="状态，running/success/failed/partial"
    )
    record_count: Optional[int] = Field(
        0,
        description="本次同步记录数"
    )
    error_msg: Optional[str] = Field(
        None,
        description="错误信息"
    )
    started_at: Optional[datetime] = Field(
        None,
        description="任务开始时间"
    )
    finished_at: Optional[datetime] = Field(
        None,
        description="任务结束时间"
    )
