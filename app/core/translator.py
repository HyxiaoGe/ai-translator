import asyncio
import os
import time
from typing import List, Optional

import dashscope
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.exception.exceptions import DashScopeAPIError, TranslationError
from app.utils.logger import setup_logger
from .translation_preferences import TranslationPreferences

load_dotenv()


class Translator:
    def __init__(self):
        """
        初始化翻译器
        
        参数:
            api_key: DashScope API密钥
        """
        self.api_key = os.getenv('API_KEY')
        # self.rate_limiter = RateLimiter(max_requests=60)
        # 使用信号量限制并发请求数
        self.semaphore = asyncio.Semaphore(20)  # 同时最多10个请求
        self.last_request_time = time.time()
        self.request_interval = 1.0  # 每个请求之间的最小间隔（秒）
        self.logger = setup_logger(self.__class__.__name__)
        self.logger.info("正在初始化翻译器...")
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY 不存在，请检查之后重试！！！")

    def _create_system_prompt(self, preferences: TranslationPreferences) -> str:
        """
        创建系统提示信息
        
        参数:
            preferences: 翻译偏好设置
            
        返回:
            str: 格式化的系统提示信息
        """
        terminology_str = "无" if not preferences.terminology_mapping else \
            "\n".join([f"- {k} => {v}" for k, v in preferences.terminology_mapping.items()])

        prompt = f"""我希望你能担任专业翻译员的角色。我会给你{preferences.source_lang}的文本内容，请你将其准确地翻译成{preferences.target_lang}。

要求如下：
1. 严格保持原文的格式，包括：
   - 表格的布局和对齐方式
   - 列表的缩进和编号格式
   - 段落间的空行
   - 特殊标记和符号
2. 翻译要自然流畅，符合{preferences.target_lang}表达习惯
3. 不要添加解释性注释，除非原文中包含
4. 数字、版本号等保持原样不翻译
5. 翻译的语言级别: {preferences.formality_level}
6. 特定领域：{preferences.domain}

专业术语对照表：
{terminology_str}

偏好设置：
- 是否保留原文专有名词：{'是' if preferences.keep_original_terms else '否'}
- 是否需要提供多个翻译方案：{'是' if preferences.provide_alternatives else '否'}
- 是否需要逐段翻译：{'是' if preferences.translate_by_paragraph else '否'}
- 是否保留原文格式：{'是' if preferences.keep_formatting else '否'}

请直接提供翻译结果，不要包含任何额外的解释或注释。
"""

        return prompt

    @retry(
        stop=stop_after_attempt(3),  # 最多重试3次
        wait=wait_exponential(multiplier=1, min=4, max=10),  # 指数退避，等待时间在4-10秒之间
        retry=retry_if_exception_type((ConnectionError, TimeoutError, DashScopeAPIError)),
        reraise=True
    )
    async def _make_api_call(self, text: str, system_prompt: str) -> str:
        """
        执行API调用
        
        参数:
            text: 待翻译文本
            system_prompt: 系统提示信息
            
        返回:
            str: 翻译结果
            
        异常:
            TranslationError: 翻译过程中的错误
            RateLimitExceededError: 超过速率限制
        """
        async with self.semaphore:  # 使用信号量控制并发
            try:
                # 确保请求间隔
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                if time_since_last < self.request_interval:
                    await asyncio.sleep(self.request_interval - time_since_last)

                self.last_request_time = time.time()

                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: dashscope.Generation.call(
                        api_key=self.api_key,
                        model='qwen-max',
                        messages=[
                            {'role': 'system', 'content': system_prompt},
                            {'role': 'user', 'content': text}
                        ],
                        result_format='message',
                        stream=False,
                        timeout=30
                    )
                )

                if response.status_code == 200:
                    return response.output.choices[0]['message']['content']
                else:
                    raise DashScopeAPIError(f"API调用失败: {response.status_code} - {response.message}")

            except Exception as e:
                self.logger.error(f"API调用错误: {str(e)}")
                raise

    async def translate(self, text: str, preferences: Optional[TranslationPreferences] = None) -> str:
        """
        翻译单个文本
        
        参数:
            text: 待翻译文本
            preferences: 翻译偏好设置（可选）
            
        返回:
            str: 翻译结果
        """
        if not text.strip():
            return text

        try:
            system_prompt = self._create_system_prompt(preferences or TranslationPreferences())
            return await self._make_api_call(text, system_prompt)

        except Exception as e:
            self.logger.error(f"翻译失败（重试后）: {str(e)}")
            raise TranslationError(f"翻译失败: {str(e)}")

    async def batch_translate(self,
                              texts: List[str],
                              preferences: Optional[TranslationPreferences] = None,
                              chunk_size: int = 10) -> List[str]:
        self.logger.info("开始批量翻译...")
        async def process_chunk(chunk: List[str]) -> List[str]:
            tasks = [self.translate(text, preferences) for text in chunk]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.warning(f"翻译失败: {str(result)}")
                    try:
                        result = await self.translate(chunk[i], preferences)
                        processed_results.append(result)
                    except Exception as e:
                        self.logger.error(f"重试翻译失败: {str(e)}")
                        processed_results.append(chunk[i])  # 失败时返回原文
                else:
                    processed_results.append(result)

            return processed_results

        results = []
        for i in range(0, len(texts), chunk_size):
            chunk = texts[i:i + chunk_size]
            chunk_results = await process_chunk(chunk)
            results.extend(chunk_results)

        return results