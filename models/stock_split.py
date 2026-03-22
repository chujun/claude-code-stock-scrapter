# models/stock_split.py
"""分红送股记录模型"""

from datetime import date
from typing import Optional

from pydantic import Field, ConfigDict

from models.base import BaseModel


class StockSplit(BaseModel):
    """分红送股记录"""

    model_config = ConfigDict(from_attributes=True)

    stock_code: str = Field(
        ...,
        description="股票代码"
    )
    event_date: date = Field(
        ...,
        description="事件日期"
    )
    event_type: str = Field(
        ...,
        description="事件类型，split/dividend/allot/issue"
    )
    bonus_ratio: Optional[float] = Field(
        None,
        description="送股比例"
    )
    dividend_ratio: Optional[float] = Field(
        None,
        description="分红比例"
    )
    price_adjust: Optional[float] = Field(
        None,
        description="价格调整因子"
    )
    data_source: str = Field(
        ...,
        description="数据来源标识"
    )
