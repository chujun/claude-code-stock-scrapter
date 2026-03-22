# services/report_service.py
"""报告服务"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from models.sync_report import SyncReport


class ReportService:
    """同步报告服务

    负责生成和保存同步报告为JSON格式
    """

    def __init__(self, output_dir: Optional[str] = None):
        """初始化报告服务

        Args:
            output_dir: 报告输出目录，默认使用 reports/
        """
        if output_dir is None:
            # 默认使用项目根目录下的 reports 文件夹
            self.output_dir = Path(__file__).parent.parent / "reports"
        else:
            self.output_dir = Path(output_dir)

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report_filename(self, sync_type: str) -> str:
        """生成报告文件名

        Args:
            sync_type: 同步类型 (full/daily/init)

        Returns:
            str: 报告文件名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"sync_report_{sync_type}_{timestamp}.json"

    def generate_summary(self, report: SyncReport) -> str:
        """生成报告摘要文本

        Args:
            report: 同步报告

        Returns:
            str: 报告摘要
        """
        success_rate = (report.success_count / report.total_stocks * 100) if report.total_stocks > 0 else 0
        summary = (
            f"同步类型: {report.sync_type}\n"
            f"触发方式: {report.trigger_type}\n"
            f"处理股票数: {report.total_stocks}\n"
            f"成功: {report.success_count} ({success_rate:.1f}%)\n"
            f"失败: {report.failed_count}\n"
            f"状态: {report.status}"
        )
        return summary

    async def save_report(self, report: SyncReport) -> Path:
        """保存报告到JSON文件

        Args:
            report: 同步报告

        Returns:
            Path: 保存的文件路径
        """
        filename = self.generate_report_filename(report.sync_type)
        filepath = self.output_dir / filename

        # 转换为字典并保存
        report_dict = report.model_dump(mode='json')

        # 序列化 datetime 为字符串
        def serialize_value(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2, default=serialize_value)

        return filepath

    async def load_report(self, filepath: Path) -> SyncReport:
        """从JSON文件加载报告

        Args:
            filepath: 报告文件路径

        Returns:
            SyncReport: 同步报告对象
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            report_dict = json.load(f)

        return SyncReport.model_validate(report_dict)

    async def list_reports(self) -> list[Path]:
        """列出所有报告文件

        Returns:
            list[Path]: 报告文件路径列表
        """
        return sorted(self.output_dir.glob("sync_report_*.json"), reverse=True)
