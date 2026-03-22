# services/quality_service.py
"""数据质量服务"""

from datetime import date
from typing import Any, Dict, List, Optional, Tuple
from copy import deepcopy

from models.stock_daily import StockDaily
from services.exceptions import QualityError


class QualityService:
    """数据质量校验服务

    提供涨跌幅、OHLC关系、字段完整性等校验功能
    """

    # 涨跌幅阈值配置
    NORMAL_CHANGE_LIMIT = 10.0  # 正常股票涨跌幅限制 ±10%
    ST_CHANGE_LIMIT = 20.0      # ST股票涨跌幅限制 ±20%

    def __init__(self, settings=None):
        """初始化质量服务

        Args:
            settings: 配置对象
        """
        self.settings = settings

    async def check_change_pct(self, record: StockDaily) -> bool:
        """校验涨跌幅是否合理

        Args:
            record: 股票日线数据

        Returns:
            bool: True 表示涨跌幅在合理范围内
        """
        if record.change_pct is None:
            # 没有涨跌幅数据，跳过校验
            return True

        change_pct = abs(record.change_pct)

        # 判断是否为ST股票（代码以*ST开头）
        is_st = record.stock_code.startswith('*ST') if record.stock_code else False

        limit = self.ST_CHANGE_LIMIT if is_st else self.NORMAL_CHANGE_LIMIT

        return change_pct <= limit

    async def fix_ohlc_relation(self, record: StockDaily) -> Tuple[bool, StockDaily]:
        """校验OHLC关系并返回修正后的记录（不修改原记录）

        OHLC关系规则：
        - high 应该是 OHLC 中的最高价
        - low 应该是 OHLC 中的最低价

        Args:
            record: 股票日线数据

        Returns:
            Tuple[bool, StockDaily]: (是否需要修正, 修正后的记录副本)
        """
        # 创建副本避免修改原记录
        fixed_record = deepcopy(record)

        if fixed_record.high is None or fixed_record.low is None:
            return True, fixed_record

        # 收集所有价格
        prices = []
        if fixed_record.open is not None:
            prices.append(fixed_record.open)
        if fixed_record.close is not None:
            prices.append(fixed_record.close)
        if fixed_record.high is not None:
            prices.append(fixed_record.high)
        if fixed_record.low is not None:
            prices.append(fixed_record.low)

        if not prices:
            return True, fixed_record

        max_price = max(prices)
        min_price = min(prices)

        needs_fix = False

        # 检查并修正 high
        if fixed_record.high < max_price:
            fixed_record.high = max_price
            needs_fix = True

        # 检查并修正 low
        if fixed_record.low > min_price:
            fixed_record.low = min_price
            needs_fix = True

        return needs_fix, fixed_record

    async def check_ohlc_relation(self, record: StockDaily) -> bool:
        """校验OHLC关系（不修改原记录）

        Args:
            record: 股票日线数据

        Returns:
            bool: True 表示OHLC关系正确
        """
        needs_fix, _ = await self.fix_ohlc_relation(record)
        return not needs_fix

    async def check_completeness(self, record: StockDaily) -> bool:
        """校验字段完整性

        必填字段：stock_code, trade_date, close, data_source
        可选字段：其他所有字段

        Args:
            record: 股票日线数据

        Returns:
            bool: True 表示必填字段完整
        """
        # 检查必填字段
        if not getattr(record, 'stock_code', None):
            return False
        if not getattr(record, 'trade_date', None):
            return False
        if getattr(record, 'close', None) is None:
            return False
        if not getattr(record, 'data_source', None):
            return False

        return True

    async def validate_record(self, record: StockDaily) -> Tuple[bool, List[str], StockDaily]:
        """综合校验单条记录（不修改原记录）

        Args:
            record: 股票日线数据

        Returns:
            Tuple[bool, List[str], StockDaily]: (是否通过, 错误信息列表, 修正后的记录副本)
        """
        errors = []
        fixed_record = deepcopy(record)

        # 涨跌幅校验
        if not await self.check_change_pct(fixed_record):
            errors.append(f"涨跌幅超限: {fixed_record.change_pct}%")

        # OHLC关系校验
        _, fixed_record = await self.fix_ohlc_relation(fixed_record)
        if fixed_record.high != record.high or fixed_record.low != record.low:
            errors.append("OHLC关系已修正")

        # 完整性校验
        if not await self.check_completeness(fixed_record):
            errors.append("必填字段缺失")

        return (len(errors) == 0, errors, fixed_record)

    async def batch_validate(
        self,
        records: List[StockDaily]
    ) -> Dict[str, Any]:
        """批量校验记录

        Args:
            records: 股票日线数据列表

        Returns:
            Dict: 校验结果统计（不修改原记录）
        """
        total = len(records)
        passed = 0
        failed = 0
        error_details = []
        quality_flags = []

        for record in records:
            is_valid, errors, _ = await self.validate_record(record)
            if is_valid:
                passed += 1
                quality_flags.append("good")
            else:
                failed += 1
                quality_flags.append("error")
                error_details.append({
                    "stock_code": record.stock_code,
                    "trade_date": str(record.trade_date),
                    "errors": errors
                })

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "quality_flags": quality_flags,
            "error_details": error_details
        }
