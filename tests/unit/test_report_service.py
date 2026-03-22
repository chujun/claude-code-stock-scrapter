# tests/unit/test_report_service.py
"""ReportService单元测试"""

import pytest
from datetime import datetime
import sys
sys.path.insert(0, '/root/ai/claudecode/first/stock-scraper')

from services.report_service import ReportService
from models.sync_report import SyncReport


class TestReportService:
    """ReportService测试"""

    def test_initialization(self):
        """测试初始化"""
        service = ReportService()
        assert service.output_dir is not None
        assert service.output_dir.name == 'reports'

    def test_generate_report_filename(self):
        """测试生成报告文件名"""
        service = ReportService()
        filename = service.generate_report_filename('full')
        assert 'full' in filename
        assert filename.endswith('.json')

    @pytest.mark.asyncio
    async def test_save_report(self, tmp_path):
        """测试保存报告"""
        service = ReportService(output_dir=str(tmp_path))
        report = SyncReport(
            sync_type='full',
            trigger_type='manual',
            started_at=datetime.now(),
            total_stocks=100,
            success_count=95,
            failed_count=5,
            status='partial'
        )
        path = await service.save_report(report)
        assert path.exists()
        assert path.suffix == '.json'

    @pytest.mark.asyncio
    async def test_generate_summary(self):
        """测试生成摘要"""
        service = ReportService()
        report = SyncReport(
            sync_type='full',
            trigger_type='manual',
            started_at=datetime.now(),
            total_stocks=100,
            success_count=95,
            failed_count=5,
            status='partial'
        )
        summary = service.generate_summary(report)
        assert 'full' in summary
        assert '95' in summary or '95%' in summary
