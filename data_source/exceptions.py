# data_source/exceptions.py
"""数据源异常定义"""


class NetworkError(Exception):
    """网络相关异常 - 可重试"""
    error_type: str = "network"
    retryable: bool = True
    error_code: str = None

    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        if error_code:
            self.error_code = error_code


class TimeoutError(NetworkError):
    """请求超时"""
    error_code: str = "timeout"


class RateLimitError(NetworkError):
    """API限流"""
    error_code: str = "429"


class ServerError(NetworkError):
    """服务器错误"""
    error_code: str = "5xx"


class ConnectionError(NetworkError):
    """连接错误"""
    error_code: str = "connection_error"


class DataError(Exception):
    """数据相关异常 - 部分可修复"""
    error_type: str = "data"
    retryable: bool = False
    error_code: str = None

    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        if error_code:
            self.error_code = error_code


class FieldMissingError(DataError):
    """字段缺失"""
    error_code: str = "field_missing"


class IntegrityError(DataError):
    """数据完整性错误"""
    error_code: str = "integrity"


class BusinessError(Exception):
    """业务相关异常 - 不重试"""
    error_type: str = "business"
    retryable: bool = False
    error_code: str = None

    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        if error_code:
            self.error_code = error_code


class DelistedError(BusinessError):
    """股票已退市"""
    error_code: str = "delisted"


class NoDataError(BusinessError):
    """无数据"""
    error_code: str = "no_data"


class InvalidDateRangeError(BusinessError):
    """无效日期范围"""
    error_code: str = "invalid_range"
