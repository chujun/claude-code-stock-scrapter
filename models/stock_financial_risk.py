# models/stock_financial_risk.py
"""股票财务风险模型"""

from datetime import date
from typing import Optional

from pydantic import Field, ConfigDict, field_validator, model_validator

from models.base import BaseModel


class StockFinancialRisk(BaseModel):
    """股票财务风险数据

    存储同花顺网站的财务风险评估数据
    """

    model_config = ConfigDict(from_attributes=True)

    stock_code: str = Field(
        ...,
        description="股票代码"
    )
    trade_date: date = Field(
        ...,
        description="交易日期"
    )
    total_risk: int = Field(
        ...,
        ge=0,
        description="总风险数量"
    )
    no_risk: int = Field(
        ...,
        ge=0,
        description="无风险数量"
    )
    low_risk: int = Field(
        ...,
        ge=0,
        description="低风险数量"
    )
    medium_risk: int = Field(
        ...,
        ge=0,
        description="中等风险数量"
    )
    high_risk: int = Field(
        ...,
        ge=0,
        description="高风险数量"
    )
    data_source: str = Field(
        default="ths",
        description="数据来源，同花顺=ths"
    )

    @field_validator("total_risk")
    @classmethod
    def validate_total_risk(cls, v: int) -> int:
        """验证总风险数非负"""
        if v < 0:
            raise ValueError("total_risk must be non-negative")
        return v

    @field_validator("no_risk", "low_risk", "medium_risk", "high_risk")
    @classmethod
    def validate_risk_counts(cls, v: int) -> int:
        """验证各风险等级数量非负"""
        if v < 0:
            raise ValueError("Risk counts must be non-negative")
        return v

    @model_validator(mode="after")
    def validate_risk_sum(self) -> "StockFinancialRisk":
        """验证风险总数一致性"""
        total = self.no_risk + self.low_risk + self.medium_risk + self.high_risk
        if total != self.total_risk:
            raise ValueError(
                f"Risk sum ({total}) does not match total_risk ({self.total_risk})"
            )
        return self
