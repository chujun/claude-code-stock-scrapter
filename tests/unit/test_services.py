# tests/unit/test_services.py
"""业务服务层单元测试"""

import pytest
from datetime import date
import sys
sys.path.insert(0, '/root/ai/claudecode/first/stock-scraper')

from services.exceptions import (
    BusinessError,
    ValidationError,
    QualityError,
)
from services.quality_service import QualityService
from models.stock_daily import StockDaily


class TestServiceExceptions:
    """业务服务异常类测试"""

    def test_business_error_is_retryable(self):
        """测试BusinessError不可重试"""
        error = BusinessError("股票已退市")
        assert error.error_type == "business"
        assert error.retryable is False

    def test_validation_error_is_retryable(self):
        """测试ValidationError不可重试"""
        error = ValidationError("字段验证失败")
        assert error.error_type == "validation"
        assert error.retryable is False

    def test_quality_error_is_retryable(self):
        """测试QualityError不可重试"""
        error = QualityError("数据质量问题")
        assert error.error_type == "quality"
        assert error.retryable is False

    def test_error_has_error_code(self):
        """测试错误有error_code"""
        error = ValidationError("invalid", error_code="INVALID_VALUE")
        assert error.error_code == "INVALID_VALUE"

    def test_exceptions_can_be_imported(self):
        """测试异常类可导入"""
        from services.exceptions import BusinessError, ValidationError, QualityError
        assert BusinessError is not None
        assert ValidationError is not None
        assert QualityError is not None


class TestQualityService:
    """QualityService测试"""

    @pytest.mark.asyncio
    async def test_check_change_pct_normal(self):
        """测试正常涨跌幅校验"""
        service = QualityService()
        record = StockDaily(
            stock_code='600000',
            trade_date=date(2024, 1, 2),
            close=10.0,
            change_pct=5.0,
            data_source='test',
            adjust_type='qfq',
            is_adjusted=True
        )
        result = await service.check_change_pct(record)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_change_pct_exceeded(self):
        """测试超限涨跌幅校验"""
        service = QualityService()
        record = StockDaily(
            stock_code='600000',
            trade_date=date(2024, 1, 3),
            close=11.0,
            change_pct=15.0,
            data_source='test',
            adjust_type='qfq',
            is_adjusted=True
        )
        result = await service.check_change_pct(record)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_change_pct_st股票(self):
        """测试ST股票涨跌幅校验"""
        service = QualityService()
        record = StockDaily(
            stock_code='*ST001',
            trade_date=date(2024, 1, 4),
            close=5.0,
            change_pct=18.0,
            data_source='test',
            adjust_type='qfq',
            is_adjusted=True
        )
        result = await service.check_change_pct(record)
        assert result is True  # ST股票允许±20%

    @pytest.mark.asyncio
    async def test_check_ohlc_relation_normal(self):
        """测试正常OHLC关系"""
        service = QualityService()
        record = StockDaily(
            stock_code='600000',
            trade_date=date(2024, 1, 2),
            open=10.0,
            high=11.0,
            low=9.5,
            close=10.5,
            data_source='test',
            adjust_type='qfq',
            is_adjusted=True
        )
        result = await service.check_ohlc_relation(record)
        assert result is True

    @pytest.mark.asyncio
    async def test_fix_ohlc_relation(self):
        """测试OHLC关系修正"""
        service = QualityService()
        record = StockDaily(
            stock_code='600000',
            trade_date=date(2024, 1, 3),
            open=10.0,
            high=10.5,  # 错误：应该更高
            low=10.8,    # 错误：应该更低
            close=10.6,
            data_source='test',
            adjust_type='qfq',
            is_adjusted=True
        )
        needs_fix, fixed_record = await service.fix_ohlc_relation(record)
        assert needs_fix is True  # 需要修正
        assert fixed_record.high >= 10.6  # high应该被修正
        assert fixed_record.low <= 10.0  # low应该被修正
        # 原记录不应被修改
        assert record.high == 10.5
        assert record.low == 10.8

    @pytest.mark.asyncio
    async def test_check_completeness_full(self):
        """测试完整字段"""
        service = QualityService()
        record = StockDaily(
            stock_code='600000',
            trade_date=date(2024, 1, 2),
            open=10.0,
            high=11.0,
            low=9.5,
            close=10.5,
            volume=1000000,
            data_source='test',
            adjust_type='qfq',
            is_adjusted=True
        )
        result = await service.check_completeness(record)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_completeness_missing_required(self):
        """测试缺失必填字段"""
        service = QualityService()
        # 使用 model_construct 绕过验证来测试不完整数据
        record = StockDaily.model_construct(
            stock_code='600000',
            trade_date=date(2024, 1, 4),
            # close 缺失
            data_source='test',
            adjust_type='qfq',
            is_adjusted=True
        )
        result = await service.check_completeness(record)
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_record(self):
        """测试综合校验"""
        service = QualityService()
        record = StockDaily(
            stock_code='600000',
            trade_date=date(2024, 1, 2),
            open=10.0,
            high=11.0,
            low=9.5,
            close=10.5,
            change_pct=5.0,
            data_source='test',
            adjust_type='qfq',
            is_adjusted=True
        )
        is_valid, errors, fixed_record = await service.validate_record(record)
        assert is_valid is True
        assert len(errors) == 0
        assert fixed_record is not None

    @pytest.mark.asyncio
    async def test_batch_validate(self):
        """测试批量校验"""
        service = QualityService()
        records = [
            StockDaily(
                stock_code='600000',
                trade_date=date(2024, 1, 2),
                close=10.0,
                change_pct=5.0,
                data_source='test',
                adjust_type='qfq',
                is_adjusted=True
            ),
            StockDaily(
                stock_code='600001',
                trade_date=date(2024, 1, 3),
                close=11.0,
                change_pct=15.0,  # 超限
                data_source='test',
                adjust_type='qfq',
                is_adjusted=True
            ),
        ]
        result = await service.batch_validate(records)
        assert result['total'] == 2
        assert result['passed'] == 1
        assert result['failed'] == 1
        assert 'quality_flags' in result
        assert result['quality_flags'][0] == 'good'
        assert result['quality_flags'][1] == 'error'
