"""
日志系统 - 显示处理的每一步
"""
import os
from datetime import datetime
from enum import Enum

class LogLevel(Enum):
    """日志级别"""
    DEBUG = "[DEBUG]"
    INFO = "[INFO]"
    SUCCESS = "[OK]"
    WARNING = "[WARN]"
    ERROR = "[ERR]"
    PROCESSING = "[>>]"

class Logger:
    """统一的日志系统"""

    def __init__(self, name="发票整理工具", verbose=True):
        self.name = name
        self.verbose = verbose
        self.log_file = None
        self.start_time = datetime.now()

    def set_log_file(self, file_path):
        """设置日志文件路径"""
        self.log_file = file_path

    def _format_message(self, level, message):
        """格式化日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}] {level.value} {message}"

    def _write_log(self, formatted_msg):
        """写入日志"""
        if self.verbose:
            print(formatted_msg)

        if self.log_file:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(formatted_msg + "\n")

    # 各级别日志方法
    def debug(self, message):
        """调试信息"""
        self._write_log(self._format_message(LogLevel.DEBUG, message))

    def info(self, message):
        """普通信息"""
        self._write_log(self._format_message(LogLevel.INFO, message))

    def success(self, message):
        """成功"""
        self._write_log(self._format_message(LogLevel.SUCCESS, message))

    def warning(self, message):
        """警告"""
        self._write_log(self._format_message(LogLevel.WARNING, message))

    def error(self, message):
        """错误"""
        self._write_log(self._format_message(LogLevel.ERROR, message))

    def processing(self, message):
        """处理中"""
        self._write_log(self._format_message(LogLevel.PROCESSING, message))

    # 高级日志方法
    def start_file(self, filename):
        """开始处理文件"""
        self._write_log(f"\n{'='*70}")
        self._write_log(f"[开始处理文件] {filename}")
        self._write_log(f"{'='*70}")

    def finish_file(self, filename, success=True, message=""):
        """完成处理文件"""
        status = "成功" if success else "失败"
        self._write_log(f"[完成处理] {filename} - {status}")
        if message:
            self._write_log(f"  信息: {message}")
        self._write_log("")

    def stage(self, stage_name, step=None):
        """显示处理阶段"""
        if step:
            self._write_log(f"\n  【阶段 {step}】 {stage_name}")
        else:
            self._write_log(f"\n  {stage_name}")

    def detail(self, key, value):
        """显示详细信息"""
        self._write_log(f"    {key}: {value}")

    def ocr_result(self, text, confidence=None):
        """OCR结果"""
        if confidence is not None:
            self._write_log(f"    [OCR] 识别文本 (置信度: {confidence:.1%})")
        else:
            self._write_log(f"    [OCR] 识别文本:")

        # 显示前500个字符
        text_preview = text[:500] if text else "(空)"
        if len(text) > 500:
            text_preview += f"... (还有{len(text)-500}字)"

        for line in text_preview.split('\n'):
            if line.strip():
                self._write_log(f"      {line}")

    def llm_analysis(self, category, amount, date, invoice_type):
        """LLM分析结果"""
        self._write_log(f"    [LLM] 分析结果:")
        self._write_log(f"      - 类型: {category}")
        self._write_log(f"      - 金额: {amount}")
        self._write_log(f"      - 日期: {date}")
        self._write_log(f"      - 发票类型: {invoice_type}")

    def validation_result(self, confidence, warnings=None):
        """验证结果"""
        if confidence >= 0.95:
            status = "高度可信 [✓✓✓]"
        elif confidence >= 0.85:
            status = "可信 [✓✓]"
        elif confidence >= 0.75:
            status = "中等 [✓]"
        else:
            status = "低置信度 [△]"

        self._write_log(f"    [验证] 置信度: {confidence:.1%} - {status}")

        if warnings:
            for warning in warnings:
                self._write_log(f"      ⚠️  {warning}")

    def file_output(self, filename):
        """输出文件"""
        self._write_log(f"    [输出] 已保存: {filename}")

    def summary(self, total, success, skip, failed):
        """处理统计"""
        self._write_log(f"\n{'='*70}")
        self._write_log(f"【处理完成统计】")
        self._write_log(f"  总计: {total} 个文件")
        self._write_log(f"  成功: {success} 个 ✓")
        self._write_log(f"  跳过: {skip} 个 ⏭")
        self._write_log(f"  失败: {failed} 个 ✗")

        if total > 0:
            success_rate = (success / (total - skip)) * 100 if (total - skip) > 0 else 0
            self._write_log(f"  成功率: {success_rate:.1f}%")

        elapsed = (datetime.now() - self.start_time).total_seconds()
        self._write_log(f"  耗时: {elapsed:.1f} 秒")
        self._write_log(f"{'='*70}\n")

# 全局日志实例
_logger_instance = None

def get_logger(name="发票整理工具", verbose=True):
    """获取日志实例（单例）"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = Logger(name, verbose)
    return _logger_instance

def reset_logger():
    """重置日志实例"""
    global _logger_instance
    _logger_instance = None
