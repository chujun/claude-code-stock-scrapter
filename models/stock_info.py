# models/stock_info.py
"""股票信息模型"""

from datetime import date
from typing import Optional

from pydantic import Field, ConfigDict

from models.base import BaseModel


class StockInfo(BaseModel):
    """股票基本信息"""

    model_config = ConfigDict(from_attributes=True)

    stock_code: str = Field(
        ...,
        description="股票代码，如600000、000001"
    )
    stock_name: str = Field(
        ...,
        description="股票名称"
    )
    market: str = Field(
        ...,
        description="交易所，SSE/SZSE"
    )
    industry: Optional[str] = Field(
        None,
        description="证监会行业分类"
    )
    sub_industry: Optional[str] = Field(
        None,
        description="证监会子行业分类"
    )
    list_date: Optional[date] = Field(
        None,
        description="上市日期"
    )
    delist_date: Optional[date] = Field(
        None,
        description="退市日期，null表示未退市"
    )
    stock_type: Optional[str] = Field(
        None,
        description="股票类型"
    )
    is_st: Optional[bool] = Field(
        None,
        description="是否ST股票"
    )
    is_new: Optional[bool] = Field(
        None,
        description="是否新股（上市未满一年）"
    )
    total_shares: Optional[float] = Field(
        None,
        description="总股本（万股）"
    )
    outstanding_shares: Optional[float] = Field(
        None,
        description="流通股本（万股）"
    )
    status: Optional[str] = Field(
        None,
        description="状态，active/delisted/suspended"
    )
    is_hs300: Optional[bool] = Field(
        None,
        description="是否沪深300成分"
    )
    is_zz500: Optional[bool] = Field(
        None,
        description="是否中证500成分"
    )
