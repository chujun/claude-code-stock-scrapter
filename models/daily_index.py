# models/daily_index.py
"""大盘指数日线模型"""

from datetime import date
from typing import Optional

from pydantic import Field, ConfigDict

from models.base import BaseModel


class DailyIndex(BaseModel):
    """大盘指数日线"""

    model_config = ConfigDict(from_attributes=True)

    index_code: str = Field(
        ...,
        description="指数代码，000001/399001/399006"
    )
    index_name: str = Field(
        ...,
        description="指数名称"
    )
    trade_date: date = Field(
        ...,
        description="交易日期"
    )
    open: Optional[float] = Field(
        None,
        description="开盘点位"
    )
    high: Optional[float] = Field(
        None,
        description="最高点位"
    )
    low: Optional[float] = Field(
        None,
        description="最低点位"
    )
    close: float = Field(
        ...,
        description="收盘点位"
    )
    volume: Optional[int] = Field(
        None,
        description="成交量（手）"
    )
    turnover: Optional[float] = Field(
        None,
        description="成交额（亿元）"
    )
    change_pct: Optional[float] = Field(
        None,
        description="涨跌幅（%）"
    )
    data_source: str = Field(
        ...,
        description="数据来源标识"
    )
