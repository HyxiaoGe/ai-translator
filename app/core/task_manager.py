from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import uuid
from app.utils.logger import setup_logger

@dataclass
class TranslationTask:
    task_id: str
    file_url: str
    file_name: str
    source_lang: str
    target_lang: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    progress: float  # 0 to 100
    result_file_path: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, TranslationTask] = {}
        self.file_cache: Dict[str, str] = {}
        self.logger = setup_logger(self.__class__.__name__)

    def _get_cache_key(self, file_name: str, source_lang: str, target_lang: str) -> str:
        """生成缓存键"""
        return f"{file_name}_{source_lang}_{target_lang}"

    def create_task(self, file_url: str, file_name: str, source_lang: str, target_lang: str) -> Tuple[str, bool]:
        """
           创建任务或返回现有任务
           返回值: (task_id, is_cached)，其中is_cached表示是否命中缓存
        """

        cache_key = self._get_cache_key(file_name, source_lang, target_lang)
        cached_task_id = self.file_cache.get(cache_key)

        if cached_task_id:
            task = self.tasks.get(cached_task_id)
            if task and task.status == 'completed':
                self.logger.info(f"Cache hit for file: {file_name}")
                return cached_task_id, True

        task_id = str(uuid.uuid4())
        task = TranslationTask(
            task_id=task_id,
            file_name=file_name,
            file_url=file_url,
            source_lang=source_lang,
            target_lang=target_lang,
            status='pending',
            progress=0.0,
            result_file_path=None,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.tasks[task_id] = task

        # 缓存任务ID
        self.file_cache[cache_key] = task_id
        return task_id, False

    def update_task_progress(self, task_id: str, progress: float):
        if task_id in self.tasks:
            self.tasks[task_id].progress = progress
            self.tasks[task_id].updated_at = datetime.now()

    def update_task_status(self, task_id: str, status: str, error_message: Optional[str] = None):
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            if error_message:
                self.tasks[task_id].error_message = error_message
            self.tasks[task_id].updated_at = datetime.now()

    def set_result_file(self, task_id: str, file_path: str, file_name: str):
        if task_id in self.tasks:
            self.tasks[task_id].result_file_path = file_path
            self.tasks[task_id].file_name = file_name
            self.tasks[task_id].updated_at = datetime.now()

    def get_task(self, task_id: str) -> Optional[TranslationTask]:
        return self.tasks.get(task_id)

    def clear_cache(self, max_age_hours: int = 30 * 24):
        """清理超过指定时间的缓存"""
        pass
        # current_time = datetime.now()
        # expired_keys = []
        #
        # for cache_key, task_id in self.file_cache.items():
        #     task = self.tasks.get(task_id)
        #     if task:
        #         age = (current_time - task.updated_at).total_seconds() / 3600
        #         if age > max_age_hours:
        #             expired_keys.append(cache_key)
        #
        # for key in expired_keys:
        #     del self.file_cache[key]