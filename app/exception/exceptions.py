class TranslationError(Exception):
    """翻译相关错误的基类"""
    pass

class DashScopeAPIError(TranslationError):
    """DashScope API 调用错误"""
    pass

class RateLimitExceededError(TranslationError):
    """超过速率限制错误"""
    pass