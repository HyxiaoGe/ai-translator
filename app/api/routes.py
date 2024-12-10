import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.core import task_manager
from app.core.file_downloader import FileDownloader
from app.core.progress import ProgressTracker
from app.core.task_manager import TaskManager
from app.core.translator import Translator, TranslationPreferences
from app.parsers.docx_parser import DocParser

app = FastAPI()

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,  # type: ignore
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 创建临时文件目录（使用绝对路径）
TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# 全局任务管理器
task_manager = TaskManager()


@app.get("/api/translate")
async def translate_file(
        background_tasks: BackgroundTasks,
        file_url: str = Query(..., description="文件链接"),
        file_name: str = Query(..., description="文件名"),
        source_lang: str = Query(..., description="源语言"),
        target_lang: str = Query(..., description="目标语言"),
):
    """创建翻译任务"""
    try:
        # 创建新任务，并检查缓存
        task_id, is_cached = task_manager.create_task(file_url, file_name, source_lang, target_lang)
        print(f"Created/Retrieved task with ID: {task_id}, cached: {is_cached}")

        if is_cached:
            # 如果是缓存的任务，直接返回任务信息
            task = task_manager.get_task(task_id)
            return {
                "task_id": task_id,
                "status": task.status,
                "message": "找到缓存的翻译结果"
            }

        # 添加后台任务
        background_tasks.add_task(
            process_translation,
            task_id,
            file_url,
            file_name,
            source_lang,
            target_lang
        )

        return {
            "task_id": task_id,
            "status": "pending",
            "message": "任务已创建，正在处理中..."
        }

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks")
async def get_task_status(
    task_id: str = Query(..., description="任务ID")
):
    """获取任务状态"""
    print(f"Checking task ID: {task_id}")
    task = task_manager.get_task(task_id)
    print(f"Task found: {task is not None}")
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    response = {
        "status": task.status,
        "progress": task.progress,
        "message": ""
    }

    if task.status == 'completed':
        response["download_url"] = f"/api/download/{task_id}/{os.path.basename(task.result_file_path)}"
    elif task.status == 'failed':
        response["error_message"] = task.error_message

    return response


@app.get("/api/download")
async def download_file(
    task_id: str = Query(..., description="任务ID"),
    doc_type: str = Query('docx', description="文件类型，目前只支持 docx 和 pdf")
):
    """下载翻译后的文件"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != 'completed':
        raise HTTPException(status_code=400, detail="任务尚未完成")

    if doc_type.lower() not in ['docx', 'pdf']:
        # 如果不是支持的类型，使用默认的docx
        doc_type = 'docx'

    # 获取基础文件名（不含扩展名）
    base_file_path = os.path.splitext(task.result_file_path)[0]
    base_file_name = os.path.splitext(task.file_name)[0]

    print(f"Downloading file: {task.result_file_path}")
    print(f"Base file name: {base_file_name}")

    # 根据doc_type构建完整的文件路径和文件名
    file_path = f"{base_file_path}.{doc_type.lower()}"
    file_name = f"{base_file_name}.{doc_type.lower()}"

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        file_path,
        filename=file_name,
        media_type='application/octet-stream'
    )


async def process_translation(
        task_id: str,
        file_url: str,
        file_name: str,
        source_lang: str,
        target_lang: str,
):
    """异步处理翻译任务"""
    try:
        # 更新任务状态为处理中
        task_manager.update_task_status(task_id, 'processing')

        # 创建下载器实例
        downloader = FileDownloader()

        # 下载文件
        file_content, file_name = await downloader.download_file(file_url, file_name)

        # 创建翻译器和解析器实例
        translator = Translator()

        # 创建进度追踪器
        progress_tracker = ProgressTracker(100, task_id, task_manager)

        doc_parser = DocParser(translator, progress_tracker=progress_tracker)

        # 设置翻译偏好
        preferences = TranslationPreferences(
            source_lang=source_lang,
            target_lang=target_lang
        )

        # 生成输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{source_lang}-{target_lang}-{file_name}"
        output_path = os.path.join(TEMP_DIR, output_filename)

        # 翻译文档
        await doc_parser.translate_document(
            doc_source=file_content,
            filename=file_name,
            output_path=output_path,
            preferences=preferences
        )

        # 验证文件是否已保存
        if not os.path.exists(output_path):
            raise Exception("文件保存失败")

        # 更新任务状态为完成
        task_manager.update_task_status(task_id, 'completed')
        task_manager.set_result_file(task_id, output_path, output_filename)

    except Exception as e:
        # 更新任务状态为失败
        task_manager.update_task_status(task_id, 'failed', str(e))
        raise
