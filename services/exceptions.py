# services/exceptions.py
"""业务服务层异常定义"""


class BusinessError(Exception):
    """业务相关异常 - 不重试"""
    error_type: str = "business"
    retryable: bool = False
    error_code: str = None

    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        if error_code:
            self.error_code = error_code


class ValidationError(BusinessError):
    """数据验证错误"""
    error_type: str = "validation"
    error_code: str = "validation_error"


class QualityError(BusinessError):
    """数据质量错误"""
    error_type: str = "quality"
    error_code: str = "quality_error"
