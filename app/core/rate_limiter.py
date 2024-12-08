import asyncio
import time
from collections import deque
from dataclasses import dataclass

@dataclass
class RateLimiter:
    """使用滑动窗口实现的速率限制器"""
    max_requests: int  # 每分钟最大请求数
    window_size: int = 60  # 窗口大小（秒）

    def __init__(self, max_requests: int, window_size: int = 60):
        self.max_requests = max_requests
        self.window_size = window_size
        self.requests = deque()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """获取发送请求的许可"""
        async with self._lock:
            now = time.time()
            
            # 移除超出窗口时间的请求记录
            while self.requests and now - self.requests[0] > self.window_size:
                self.requests.popleft()
            
            # 如果达到限制，等待直到最早的请求过期
            if len(self.requests) >= self.max_requests:
                wait_time = self.window_size - (now - self.requests[0])
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            # 添加当前请求记录
            self.requests.append(now)