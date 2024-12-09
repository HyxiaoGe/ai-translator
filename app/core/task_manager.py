from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid
from app.utils.logger import setup_logger

@dataclass
class TranslationTask:
    task_id: str
    file_url: str
    file_name: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    progress: float  # 0 to 100
    result_file_path: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, TranslationTask] = {}
        self.logger = setup_logger(self.__class__.__name__)

    def create_task(self, file_url: str) -> str:
        task_id = str(uuid.uuid4())
        task = TranslationTask(
            task_id=task_id,
            file_name="",
            file_url=file_url,
            status='pending',
            progress=0.0,
            result_file_path=None,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.tasks[task_id] = task
        return task_id

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