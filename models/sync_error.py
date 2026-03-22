# models/sync_error.py
"""同步异常记录模型"""

from datetime import date, datetime
from typing import Optional

from pydantic import Field, ConfigDict

from models.base import BaseModel


class SyncError(BaseModel):
    """同步异常记录"""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(
        None,
        description="自增主键"
    )
    stock_code: Optional[str] = Field(
        None,
        description="股票代码"
    )
    trade_date: Optional[date] = Field(
        None,
        description="交易日期"
    )
    sync_type: str = Field(
        ...,
        description="同步类型，full/daily"
    )
    error_type: str = Field(
        ...,
        description="错误类型，network/data/business"
    )
    error_code: Optional[str] = Field(
        None,
        description="错误码，如429、500、timeout"
    )
    error_msg: str = Field(
        ...,
        description="错误详情"
    )
    retry_count: int = Field(
        0,
        description="已重试次数"
    )
    status: str = Field(
        ...,
        description="状态，pending/retry/resolved/ignored"
    )
    resolved_at: Optional[datetime] = Field(
        None,
        description="解决时间"
    )
    resolution: Optional[str] = Field(
        None,
        description="解决方案描述"
    )
