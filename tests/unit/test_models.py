# tests/unit/test_models.py
"""数据模型单元测试"""

import pytest
from datetime import date, datetime
from pydantic import ValidationError

import sys
sys.path.insert(0, '/root/ai/claudecode/first/stock-scraper')

from models.base import BaseModel
from models.stock_info import StockInfo
from models.stock_daily import StockDaily
from models.sync_status import SyncStatus
from models.sync_error import SyncError
from models.sync_report import SyncReport
from models.daily_index import DailyIndex
from models.stock_split import StockSplit


class TestBaseModel:
    """BaseModel基础模型测试"""

    def test_auto_created_at(self):
        """测试自动填充created_at"""
        class TestModel(BaseModel):
            name: str

        model = TestModel(name="test")
        assert model.created_at is not None
        assert isinstance(model.created_at, datetime)

    def test_auto_updated_at(self):
        """测试自动填充updated_at"""
        class TestModel(BaseModel):
            name: str

        model = TestModel(name="test")
        assert model.updated_at is not None
        assert isinstance(model.updated_at, datetime)

    def test_config_from_attributes(self):
        """测试Config配置"""
        class TestModel(BaseModel):
            name: str

        model = TestModel(name="test")
        assert hasattr(model, 'model_dump')  # Pydantic v2


class TestStockInfo:
    """StockInfo股票信息模型测试"""

    def test_required_fields(self):
        """测试必填字段"""
        info = StockInfo(
            stock_code='600000',
            stock_name='浦发银行',
            market='SSE'
        )
        assert info.stock_code == '600000'
        assert info.stock_name == '浦发银行'
        assert info.market == 'SSE'

    def test_optional_fields(self):
        """测试可选字段"""
        info = StockInfo(
            stock_code='600000',
            stock_name='浦发银行',
            market='SSE',
            industry='银行业',
            is_st=False,
            is_new=False
        )
        assert info.industry == '银行业'
        assert info.is_st is False
        assert info.is_new is False

    def test_stock_code_type(self):
        """测试股票代码类型"""
        info = StockInfo(
            stock_code='600000',
            stock_name='test',
            market='SSE'
        )
        assert isinstance(info.stock_code, str)

    def test_market_values(self):
        """测试market字段枚举值"""
        # SSE = 上海交易所
        info1 = StockInfo(stock_code='600000', stock_name='test', market='SSE')
        assert info1.market == 'SSE'

        # SZSE = 深圳交易所
        info2 = StockInfo(stock_code='000001', stock_name='test', market='SZSE')
        assert info2.market == 'SZSE'


class TestStockDaily:
    """StockDaily股票日线模型测试"""

    def test_required_fields(self):
        """测试必填字段"""
        daily = StockDaily(
            stock_code='600000',
            trade_date=date(2024, 1, 2),
            close=10.5,
            data_source='akshare',
            adjust_type='qfq',
            is_adjusted=True
        )
        assert daily.stock_code == '600000'
        assert daily.trade_date == date(2024, 1, 2)
        assert daily.close == 10.5
        assert daily.data_source == 'akshare'

    def test_optional_fields(self):
        """测试可选字段"""
        daily = StockDaily(
            stock_code='600000',
            trade_date=date(2024, 1, 2),
            close=10.5,
            data_source='akshare',
            adjust_type='qfq',
            is_adjusted=True,
            open=10.0,
            high=10.8,
            low=9.9,
            volume=1000000,
            turnover=10500000.0,
            change_pct=5.0,
            pre_close=10.0,
            amplitude_pct=9.0,
            turnover_rate=2.5,
            total_market_cap=300000000000.0,
            float_market_cap=280000000000.0,
            pe_ratio=6.5,
            static_pe=6.2,
            dynamic_pe=6.8,
            pb_ratio=0.8
        )
        assert daily.open == 10.0
        assert daily.high == 10.8
        assert daily.low == 9.9
        assert daily.volume == 1000000

    def test_quality_flag_default(self):
        """测试quality_flag默认值"""
        daily = StockDaily(
            stock_code='600000',
            trade_date=date(2024, 1, 2),
            close=10.5,
            data_source='akshare',
            adjust_type='qfq',
            is_adjusted=True
        )
        assert daily.quality_flag == 'good'

    def test_adjust_type_values(self):
        """测试adjust_type字段枚举值"""
        # 前复权
        daily1 = StockDaily(
            stock_code='600000',
            trade_date=date(2024, 1, 2),
            close=10.5,
            data_source='akshare',
            adjust_type='qfq',
            is_adjusted=True
        )
        assert daily1.adjust_type == 'qfq'

    def test_ohlc_relationship(self):
        """测试OHLC关系正确的数据"""
        daily = StockDaily(
            stock_code='600000',
            trade_date=date(2024, 1, 2),
            open=10.0,
            high=10.8,
            low=9.9,
            close=10.5,
            data_source='akshare',
            adjust_type='qfq',
            is_adjusted=True
        )
        # 验证OHLC关系：low <= open,close <= high
        assert daily.low <= daily.open
        assert daily.close <= daily.high


class TestSyncStatus:
    """SyncStatus同步状态模型测试"""

    def test_required_fields(self):
        """测试必填字段"""
        status = SyncStatus(
            sync_type='full',
            status='running'
        )
        assert status.sync_type == 'full'
        assert status.status == 'running'

    def test_sync_type_values(self):
        """测试sync_type枚举值"""
        status1 = SyncStatus(sync_type='full', status='running')
        assert status1.sync_type == 'full'

        status2 = SyncStatus(sync_type='daily', status='running')
        assert status2.sync_type == 'daily'

        status3 = SyncStatus(sync_type='init', status='running')
        assert status3.sync_type == 'init'

    def test_status_values(self):
        """测试status枚举值"""
        status1 = SyncStatus(sync_type='full', status='running')
        assert status1.status == 'running'

        status2 = SyncStatus(sync_type='full', status='success')
        assert status2.status == 'success'

        status3 = SyncStatus(sync_type='full', status='failed')
        assert status3.status == 'failed'

        status4 = SyncStatus(sync_type='full', status='partial')
        assert status4.status == 'partial'

    def test_stock_code_nullable(self):
        """测试stock_code可以为null（全量任务）"""
        status = SyncStatus(
            sync_type='full',
            status='running',
            stock_code=None
        )
        assert status.stock_code is None


class TestSyncError:
    """SyncError同步异常模型测试"""

    def test_required_fields(self):
        """测试必填字段"""
        error = SyncError(
            stock_code='600000',
            sync_type='full',
            error_type='network',
            error_msg='Connection timeout',
            status='pending'
        )
        assert error.stock_code == '600000'
        assert error.error_type == 'network'
        assert error.error_msg == 'Connection timeout'
        assert error.status == 'pending'

    def test_error_type_values(self):
        """测试error_type枚举值"""
        error1 = SyncError(
            stock_code='600000',
            sync_type='full',
            error_type='network',
            error_msg='test',
            status='pending'
        )
        assert error1.error_type == 'network'

        error2 = SyncError(
            stock_code='600000',
            sync_type='full',
            error_type='data',
            error_msg='test',
            status='pending'
        )
        assert error2.error_type == 'data'

        error3 = SyncError(
            stock_code='600000',
            sync_type='full',
            error_type='business',
            error_msg='test',
            status='pending'
        )
        assert error3.error_type == 'business'

    def test_retry_count_default(self):
        """测试retry_count默认值"""
        error = SyncError(
            stock_code='600000',
            sync_type='full',
            error_type='network',
            error_msg='test',
            status='pending'
        )
        assert error.retry_count == 0


class TestSyncReport:
    """SyncReport同步报告模型测试"""

    def test_required_fields(self):
        """测试必填字段"""
        report = SyncReport(
            sync_type='full',
            trigger_type='manual',
            started_at=datetime.now(),
            total_stocks=100,
            success_count=95,
            failed_count=5,
            status='partial'
        )
        assert report.sync_type == 'full'
        assert report.trigger_type == 'manual'
        assert report.total_stocks == 100
        assert report.success_count == 95
        assert report.failed_count == 5

    def test_statistics_fields(self):
        """测试统计字段"""
        report = SyncReport(
            sync_type='full',
            trigger_type='manual',
            started_at=datetime.now(),
            total_stocks=100,
            success_count=95,
            failed_count=5,
            network_error_count=3,
            data_error_count=1,
            business_error_count=1,
            new_records=5000,
            updated_records=100,
            status='partial'
        )
        assert report.network_error_count == 3
        assert report.data_error_count == 1
        assert report.business_error_count == 1
        assert report.new_records == 5000
        assert report.updated_records == 100

    def test_quality_fields(self):
        """测试质量字段"""
        report = SyncReport(
            sync_type='full',
            trigger_type='manual',
            started_at=datetime.now(),
            total_stocks=100,
            success_count=95,
            failed_count=5,
            data_completeness=99.5,
            quality_pass_rate=99.0,
            avg_duration_per_stock=1.5,
            status='partial'
        )
        assert report.data_completeness == 99.5
        assert report.quality_pass_rate == 99.0
        assert report.avg_duration_per_stock == 1.5


class TestDailyIndex:
    """DailyIndex大盘指数模型测试"""

    def test_required_fields(self):
        """测试必填字段"""
        idx = DailyIndex(
            index_code='000001',
            index_name='上证指数',
            trade_date=date(2024, 1, 2),
            close=3000.0,
            data_source='akshare'
        )
        assert idx.index_code == '000001'
        assert idx.index_name == '上证指数'
        assert idx.close == 3000.0

    def test_optional_fields(self):
        """测试可选字段"""
        idx = DailyIndex(
            index_code='000001',
            index_name='上证指数',
            trade_date=date(2024, 1, 2),
            close=3000.0,
            data_source='akshare',
            open=2980.0,
            high=3010.0,
            low=2970.0,
            volume=300000000,
            turnover=400000000000.0,
            change_pct=1.2
        )
        assert idx.open == 2980.0
        assert idx.high == 3010.0
        assert idx.low == 2970.0


class TestStockSplit:
    """StockSplit分红送股模型测试"""

    def test_required_fields(self):
        """测试必填字段"""
        split = StockSplit(
            stock_code='600000',
            event_date=date(2024, 1, 15),
            event_type='dividend',
            data_source='akshare'
        )
        assert split.stock_code == '600000'
        assert split.event_date == date(2024, 1, 15)
        assert split.event_type == 'dividend'

    def test_event_type_values(self):
        """测试event_type枚举值"""
        split1 = StockSplit(
            stock_code='600000',
            event_date=date(2024, 1, 15),
            event_type='split',
            data_source='akshare'
        )
        assert split1.event_type == 'split'

        split2 = StockSplit(
            stock_code='600000',
            event_date=date(2024, 1, 15),
            event_type='dividend',
            data_source='akshare'
        )
        assert split2.event_type == 'dividend'

        split3 = StockSplit(
            stock_code='600000',
            event_date=date(2024, 1, 15),
            event_type='allot',
            data_source='akshare'
        )
        assert split3.event_type == 'allot'

    def test_ratio_fields(self):
        """测试比例字段"""
        split = StockSplit(
            stock_code='600000',
            event_date=date(2024, 1, 15),
            event_type='split',
            bonus_ratio=0.5,
            dividend_ratio=0.3,
            price_adjust=0.85,
            data_source='akshare'
        )
        assert split.bonus_ratio == 0.5
        assert split.dividend_ratio == 0.3
        assert split.price_adjust == 0.85
