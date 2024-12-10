import httpx
from urllib.parse import urlparse, parse_qs, quote, unquote
from typing import Tuple
from io import BytesIO
from app.utils.logger import setup_logger

class FileDownloader:
    def __init__(self, base_url: str = "http://192.168.250.217"):
        self.base_url = base_url
        self.logger = setup_logger(self.__class__.__name__)

    async def _extract_params(self, url: str) -> Tuple[str, str, str]:
        """从URL中提取fc和fi参数"""
        decoded_url = unquote(url)
        parsed_url = urlparse(decoded_url)
        params = parse_qs(parsed_url.query)

        self.logger.info(f"提取到的参数: {params}")

        fc = params.get('fc', [''])[0]
        fi = params.get('fi', [''])[0]
        ct = params.get('ct', [''])[0]

        if not fc or not fi or not ct:
            raise ValueError("URL必须包含fc, fi, ct参数")

        return fc, fi, ct

    async def _get_file_info(self, fc: str, fi: str, ct: str) -> Tuple[str, str]:
        self.logger.info("开始获取文件信息....")
        """获取文件的URI和文件名"""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/apps/file/down"
            params = {'fc': fc, 'fi': fi}

            headers = {'ct': ct}

            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()
            if data.get('status') != 'ok':
                raise ValueError(f"获取文件信息失败: {data.get('message', '未知错误')}")

            file_uri = data.get('data', {}).get('fileUri')
            file_name = data.get('data', {}).get('fileName')

            if not file_uri or not file_name:
                raise ValueError("无法获取文件URI或文件名")

            return file_uri, file_name

    async def download_file(self, file_url: str, file_name: str) -> Tuple[BytesIO, str]:
        self.logger.info("开始下载文件....")
        """完整的文件下载流程"""
        try:
            # 4. 下载实际文件
            async with httpx.AsyncClient() as client:
                self.logger.info(f"文件下载中...., {file_url}")
                # 清理URL中的换行符和空白字符
                cleaned_url = file_url.strip()
                decoded_url = unquote(cleaned_url)
                self.logger.info(f"编码, {decoded_url}")
                response = await client.get(decoded_url)
                response.raise_for_status()

                self.logger.info(f"文件下载成功...")

                # 返回文件内容和文件名
                return BytesIO(response.content), file_name

        except httpx.HTTPError as e:
            raise ValueError(f"文件下载失败: {str(e)}")
        except Exception as e:
            raise ValueError(f"处理过程出错: {str(e)}")