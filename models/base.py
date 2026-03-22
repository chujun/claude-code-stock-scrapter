# models/base.py
"""基础模型 - 所有数据模型的基类"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class BaseModel(BaseModel):
    """基础模型，所有数据模型的基类

    自动填充 created_at 和 updated_at 时间戳
    """

    model_config = ConfigDict(from_attributes=True)

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="修改时间"
    )
