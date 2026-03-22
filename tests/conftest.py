# tests/conftest.py
"""pytest配置文件"""

import sys
from pathlib import Path

import pytest
import pytest_asyncio

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture
def sample_stock_info():
    """示例股票信息"""
    return {
        "stock_code": "600000",
        "stock_name": "浦发银行",
        "market": "SSE",
        "industry": "银行业",
        "is_st": False,
        "is_new": False,
    }


@pytest.fixture
def sample_stock_daily():
    """示例股票日线数据"""
    return {
        "stock_code": "600000",
        "trade_date": "2024-01-02",
        "open": 10.0,
        "high": 10.8,
        "low": 9.9,
        "close": 10.5,
        "volume": 1000000,
        "turnover": 10500000.0,
        "change_pct": 5.0,
        "data_source": "akshare",
        "adjust_type": "qfq",
        "is_adjusted": True,
    }


@pytest.fixture
def sample_sync_report():
    """示例同步报告"""
    return {
        "sync_type": "full",
        "trigger_type": "manual",
        "total_stocks": 100,
        "success_count": 95,
        "failed_count": 5,
        "status": "partial",
    }
