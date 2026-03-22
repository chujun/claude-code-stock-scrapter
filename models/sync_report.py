# models/sync_report.py
"""同步报告模型"""

from datetime import datetime
from typing import Optional

from pydantic import Field, ConfigDict

from models.base import BaseModel


class SyncReport(BaseModel):
    """同步报告"""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(
        None,
        description="自增主键"
    )
    sync_type: str = Field(
        ...,
        description="同步类型，full/daily/init"
    )
    trigger_type: str = Field(
        ...,
        description="触发方式，manual/scheduled/on_demand"
    )
    started_at: datetime = Field(
        ...,
        description="开始时间"
    )
    finished_at: Optional[datetime] = Field(
        None,
        description="结束时间"
    )
    duration_seconds: Optional[int] = Field(
        None,
        description="持续时长（秒）"
    )
    total_stocks: int = Field(
        ...,
        description="处理股票总数"
    )
    success_count: int = Field(
        ...,
        description="成功数量"
    )
    failed_count: int = Field(
        ...,
        description="失败数量"
    )
    network_error_count: int = Field(
        0,
        description="网络异常数量"
    )
    data_error_count: int = Field(
        0,
        description="数据异常数量"
    )
    business_error_count: int = Field(
        0,
        description="业务异常数量"
    )
    new_records: int = Field(
        0,
        description="新增记录数"
    )
    updated_records: int = Field(
        0,
        description="更新记录数"
    )
    data_completeness: Optional[float] = Field(
        None,
        description="数据完整率（%）"
    )
    quality_pass_rate: Optional[float] = Field(
        None,
        description="质量校验通过率（%）"
    )
    avg_duration_per_stock: Optional[float] = Field(
        None,
        description="平均单只耗时（秒）"
    )
    api_call_count: int = Field(
        0,
        description="API调用次数"
    )
    status: str = Field(
        ...,
        description="状态，running/success/partial/failed"
    )
    report_summary: Optional[str] = Field(
        None,
        description="报告摘要"
    )
