import os
import aiofiles
import httpx
from pathlib import Path
from datetime import datetime
import uuid
from io import BytesIO


class FileHandler:
    def __init__(self, temp_dir: str = "temp"):
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)

    async def download_file(self, url: str) -> BytesIO:
        """下载文件到内存"""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return BytesIO(response.content)

    async def save_file(self, file_content: BytesIO, original_filename: str) -> str:
        """保存文件并返回文件路径"""
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        extension = Path(original_filename).suffix
        filename = f"translated_{timestamp}_{unique_id}{extension}"

        file_path = os.path.join(self.temp_dir, filename)

        # 保存文件
        file_content.seek(0)
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content.read())

        return file_path

    def get_download_url(self, file_path: str) -> str:
        """生成文件下载URL"""
        filename = os.path.basename(file_path)
        # 这里需要根据你的实际部署环境配置正确的URL
        return f"/download/{filename}"

    async def cleanup_old_files(self, max_age_hours: int = 24):
        """清理旧文件"""
        current_time = datetime.now()
        for file_path in Path(self.temp_dir).glob("*"):
            if file_path.is_file():
                file_age = datetime.fromtimestamp(file_path.stat().st_mtime)
                if (current_time - file_age).total_seconds() > max_age_hours * 3600:
                    os.remove(file_path)