from docx import Document
from typing import List, Optional
from dataclasses import dataclass
from app.core.translator import Translator, TranslationPreferences


@dataclass
class DocParserConfig:
    skip_headers: bool = True
    skip_footers: bool = True
    skip_tables: bool = False

class DocParser:
    def __init__(self, translator: Translator, config: Optional[DocParserConfig] = None):
        self.translator = translator
        self.config = config or DocParserConfig()

    def translate_document(self, doc_path: str, preferences: Optional[TranslationPreferences] = None):
        """
        在原文档上直接进行翻译

        Args:
            doc_path: Word文档路径
            preferences: 翻译偏好设置
        """
        # 打开文档
        doc = Document(doc_path)

        # 处理正文段落
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():  # 跳过空段落
                # 获取段落中的所有runs（格式一致的文本块）
                for run in paragraph.runs:
                    if run.text.strip():  # 跳过空文本
                        # 翻译文本
                        translated_text = self.translator.translate(run.text, preferences)
                        # 保持原有格式，只替换文本
                        run.text = translated_text

        # 处理表格（如果需要）
        if not self.config.skip_tables:
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            if paragraph.text.strip():
                                for run in paragraph.runs:
                                    if run.text.strip():
                                        translated_text = self.translator.translate(run.text, preferences)
                                        run.text = translated_text

        # 处理页眉（如果需要）
        if not self.config.skip_headers:
            for section in doc.sections:
                header = section.header
                for paragraph in header.paragraphs:
                    if paragraph.text.strip():
                        for run in paragraph.runs:
                            if run.text.strip():
                                translated_text = self.translator.translate(run.text, preferences)
                                run.text = translated_text

        # 处理页脚（如果需要）
        if not self.config.skip_footers:
            for section in doc.sections:
                footer = section.footer
                for paragraph in footer.paragraphs:
                    if paragraph.text.strip():
                        for run in paragraph.runs:
                            if run.text.strip():
                                translated_text = self.translator.translate(run.text, preferences)
                                run.text = translated_text

        # 直接保存到原文件
        doc.save(doc_path)