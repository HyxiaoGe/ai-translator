# app/core/progress.py

from tqdm import tqdm


class ProgressTracker:
    def __init__(self, total: int, task_id: str, task_manager):
        self.total = total
        self.current = 0
        self.task_id = task_id
        self.task_manager = task_manager

    def update(self, n: int = 1):
        """更新进度并通知任务管理器"""
        self.current += n
        progress = (self.current / self.total) * 100 if self.total > 0 else 0
        self.task_manager.update_task_progress(self.task_id, progress)

    def close(self):
        """完成进度追踪"""
        pass


class CustomTQDM(tqdm):
    """自定义的tqdm，将进度同步到任务管理器"""

    def __init__(self, *args, task_id: str, task_manager, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_id = task_id
        self.task_manager = task_manager

    def update(self, n: int = 1):
        super().update(n)
        # 计算百分比进度
        progress = (self.n / self.total) * 100 if self.total > 0 else 0
        self.task_manager.update_task_progress(self.task_id, progress)