import os
from dataclasses import dataclass
from typing import List, Dict, Optional
from dotenv import load_dotenv
import dashscope

from app.utils.logger import setup_logger

load_dotenv()

@dataclass
class TranslationPreferences:
    source_lang: str = 'en'
    target_lang: str = 'zh'
    formality_level: str = '正式'  # 正式/普通/口语化
    domain: str = '技术'  # 文学/技术/商务/医疗/法律等
    keep_original_terms: bool = True
    provide_alternatives: bool = False
    translate_by_paragraph: bool = True
    keep_formatting: bool = True
    terminology_mapping: Dict[str, str] = None


class Translator:
    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
        self.api_key = os.getenv('API_KEY')
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY environment variable not set")

    def _create_system_prompt(self, preferences: TranslationPreferences) -> str:
        terminology_str = "无" if not preferences.terminology_mapping else \
            "\n".join([f"- {k} => {v}" for k, v in preferences.terminology_mapping.items()])

        prompt = f"""我希望你能担任专业翻译员的角色。我会给你{preferences.source_lang}的文本内容，请你将其准确地翻译成{preferences.target_lang}。

要求如下：
1. 保持原文的语气和风格
2. 翻译要自然流畅，符合{preferences.target_lang}表达习惯
3. 专业术语要准确
4. 如果遇到难以直译的文化特定用语，请在翻译后用括号做简要解释
5. 翻译的语言级别: {preferences.formality_level}
6. 特定领域：{preferences.domain}

专业术语对照表：
{terminology_str}

偏好设置：
- 是否保留原文专有名词：{'是' if preferences.keep_original_terms else '否'}
- 是否需要提供多个翻译方案：{'是' if preferences.provide_alternatives else '否'}
- 是否需要逐段翻译：{'是' if preferences.translate_by_paragraph else '否'}
- 是否保留原文格式：{'是' if preferences.keep_formatting else '否'}

请按照以下格式回复：
[翻译内容]
"""

        return prompt

    def translate(self, text: str, preferences: Optional[TranslationPreferences] = None) -> str:
        """
        Translate text using specified preferences.

        Args:
            text: Text to translate
            preferences: Translation preferences

        Returns:
            Translated text
        """
        if preferences is None:
            preferences = TranslationPreferences()

        try:
            system_prompt = self._create_system_prompt(preferences)

            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': text}
            ]

            response = dashscope.Generation.call(
                api_key=self.api_key,
                model="qwen-max",
                messages=messages,
                result_format='message',
                stream=False
            )

            # 处理流式响应
            # full_response = []
            # for chunk in response:
            if response.status_code == 200:
                # 获取当前片段的内容
                # chunk_content = chunk.output.choices[0]['message']['content']
                # full_response.append(chunk_content)
                translated_text = response.output.choices[0]['message']['content']
                # 可以在这里添加实时处理逻辑，比如打印或回调
                # self.logger.info(f"Translation successful: {len(text)} chars")
                return translated_text
            else:
                self.logger.error(f"Translation chunk failed: {response.code} - {response.message}")
                raise Exception(f"Translation chunk failed: {response.message}")

        # translated_text = ''.join(full_response)

        except Exception as e:
            self.logger.error(f"Error during translation: {str(e)}")
        raise


    def batch_translate(self, texts: List[str], preferences: Optional[TranslationPreferences] = None) -> List[str]:
        """
        Translate a batch of texts using specified preferences.

        Args:
            texts: List of texts to translate
            preferences: Translation preferences

        Returns:
            List of translated texts
        """
        translated_texts = []
        for text in texts:
            translated = self.translate(text, preferences)
            translated_texts.append(translated)
        return translated_texts
