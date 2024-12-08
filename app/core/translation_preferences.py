from dataclasses import dataclass
from typing import Dict, Optional


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