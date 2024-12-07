import urllib.parse
from io import BytesIO
from pathlib import Path

import httpx
from fastapi import FastAPI, Query, HTTPException

from app.core.file_downloader import FileDownloader

app = FastAPI()


async def download_file(url: str) -> tuple[BytesIO, str]:
    """
    下载文件到内存并返回 BytesIO 对象和文件扩展名

    Args:
        url: 文件下载链接

    Returns:
        tuple: (BytesIO对象, 文件扩展名)
    """
    try:
        async with httpx.AsyncClient() as client:
            # http://192.168.0.196/group1/M00/00/1E/wKgAxGdJe56ABeewAAAyYB35Ydc60.docx?token=260a64b4359502d2b5f62b29f94057cb&ts=1733557138&fn=%E7%99%BE%E7%82%BC%E7%B3%BB%E5%88%97%E6%89%8B%E6%9C%BA%E4%BA%A7%E5%93%81%E4%BB%8B%E7%BB%8D.docx&cv=4.12.0&ct=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjk4LCJ0aW1lIjoxNzMzNTU3MTAzLCJrZXkiOiIxMjM0NTY3NC4xIiwiaXAiOiIxOTIuMTY4LjI1MC4xMTgiLCJkZXZpY2UiOiJ3ZWIiLCJpYXQiOjE3MzM1NTcxMDN9.iyQJq7b1rqMrFeNnqnZLy9nP9Gt_6tFosC9yz36He2Y
            down_url = ""
            response = await client.get(down_url)
            response.raise_for_status()

            # 获取文件扩展名
            # 先尝试从URL路径获取
            file_extension = Path(urllib.parse.urlparse(url).path).suffix.lower()

            # 如果URL中没有扩展名，尝试从Content-Type获取
            if not file_extension:
                content_type = response.headers.get('content-type', '')
                if 'text/plain' in content_type:
                    file_extension = '.txt'
                elif 'application/pdf' in content_type:
                    file_extension = '.pdf'
                elif 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
                    file_extension = '.docx'
                # 可以添加更多类型的判断

            # 创建 BytesIO 对象
            file_content = BytesIO(response.content)
            return file_content, file_extension

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件下载失败: {str(e)}")


async def read_file_content(file_content: BytesIO, file_extension: str) -> str:
    """
    从内存中读取文件内容

    Args:
        file_content: BytesIO对象，包含文件内容
        file_extension: 文件扩展名

    Returns:
        str: 文件的文本内容
    """
    try:
        if file_extension == '.docx':
            from docx import Document
            file_content.seek(0)
            doc = Document(file_content)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])

        else:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_extension}")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件读取失败: {str(e)}")


@app.get("/translate")
async def translate_file(
        file_url: str = Query(..., description="文件链接"),
        source_lang: str = Query(..., description="源语言"),
        target_lang: str = Query(..., description="目标语言"),
):
    try:
        # 创建下载器实例
        downloader = FileDownloader()

        # 下载文件
        file_content, file_name = await downloader.download_file(file_url)


        # TODO: 接下来可以调用DocParser进行处理
        # ...

        return {
            "message": "文件下载成功",
            "file_name": file_name,
            "size": len(file_content.getvalue())
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
