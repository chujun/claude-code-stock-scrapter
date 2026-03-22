# models/stock_daily.py
"""股票日线行情模型"""

from datetime import date
from typing import Optional

from pydantic import Field, ConfigDict

from models.base import BaseModel


class StockDaily(BaseModel):
    """股票日线行情"""

    model_config = ConfigDict(from_attributes=True)

    stock_code: str = Field(
        ...,
        description="股票代码"
    )
    trade_date: date = Field(
        ...,
        description="交易日期"
    )
    open: Optional[float] = Field(
        None,
        description="前复权开盘价"
    )
    high: Optional[float] = Field(
        None,
        description="前复权最高价"
    )
    low: Optional[float] = Field(
        None,
        description="前复权最低价"
    )
    close: float = Field(
        ...,
        description="前复权收盘价"
    )
    volume: Optional[int] = Field(
        None,
        description="成交量（手）"
    )
    turnover: Optional[float] = Field(
        None,
        description="成交额（元）"
    )
    change_pct: Optional[float] = Field(
        None,
        description="涨跌幅（%）"
    )
    pre_close: Optional[float] = Field(
        None,
        description="前复权前收盘价"
    )
    amplitude_pct: Optional[float] = Field(
        None,
        description="振幅（%）"
    )
    turnover_rate: Optional[float] = Field(
        None,
        description="换手率（%）"
    )
    total_market_cap: Optional[float] = Field(
        None,
        description="总市值（元）"
    )
    float_market_cap: Optional[float] = Field(
        None,
        description="流通市值（元）"
    )
    pe_ratio: Optional[float] = Field(
        None,
        description="市盈率（动态）"
    )
    static_pe: Optional[float] = Field(
        None,
        description="静态市盈率"
    )
    dynamic_pe: Optional[float] = Field(
        None,
        description="动态市盈率"
    )
    pb_ratio: Optional[float] = Field(
        None,
        description="市净率"
    )
    is_adjusted: bool = Field(
        True,
        description="是否复权数据"
    )
    adjust_type: str = Field(
        "qfq",
        description="复权类型，qfq/hfq/none"
    )
    data_source: str = Field(
        ...,
        description="数据来源标识"
    )
    quality_flag: str = Field(
        "good",
        description="数据质量标记，good=正常，warn=可疑，error=异常"
    )
