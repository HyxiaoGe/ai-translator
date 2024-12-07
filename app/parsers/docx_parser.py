import asyncio
from io import BytesIO
from docx import Document
from typing import List, Optional, Union
from dataclasses import dataclass

from tqdm import tqdm

from app.core.translator import Translator, TranslationPreferences
from app.core.progress import ProgressTracker

@dataclass
class DocParserConfig:
    skip_headers: bool = True
    skip_footers: bool = True
    skip_tables: bool = False

class DocParser:
    def __init__(self,
                 translator: Translator,
                 config: Optional[DocParserConfig] = None,
                 progress_tracker: Optional[ProgressTracker] = None):
        self.translator = translator
        self.config = config or DocParserConfig()
        self.progress_tracker = progress_tracker

    def _count_total_runs(self, doc: Document) -> int:
        """统计文档中需要处理的总runs数"""
        total = 0

        # 统计段落
        for para in doc.paragraphs:
            total += len([run for run in para.runs if run.text.strip()])

        if not self.config.skip_tables:
            # 统计表格
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            total += len([run for run in para.runs if run.text.strip()])

        if not self.config.skip_headers:
            # 统计页眉
            for section in doc.sections:
                for para in section.header.paragraphs:
                    total += len([run for run in para.runs if run.text.strip()])

        if not self.config.skip_footers:
            # 统计页脚
            for section in doc.sections:
                for para in section.footer.paragraphs:
                    total += len([run for run in para.runs if run.text.strip()])

        return total

    async def translate_document(self,
                         doc_source: Union[str, BytesIO],
                         filename: Optional[str] = None,
                         output_path: Optional[str] = None,
                         preferences: Optional[TranslationPreferences] = None) -> BytesIO:
        """
        在文档上直接进行翻译

        Args:
            doc_source: Word文档路径或BytesIO对象
            filename: 文件名（用于显示）
            output_path: 输出文件路径（可选）
            preferences: 翻译偏好设置

        Returns:
            BytesIO: 包含翻译后文档的BytesIO对象
        """
        # 打开文档
        if isinstance(doc_source, str):
            doc = Document(doc_source)
        else:
            doc = Document(doc_source)

        # 获取总运行数并设置进度追踪器
        total_runs = self._count_total_runs(doc)
        if self.progress_tracker:
            self.progress_tracker.set_total(total_runs)

        with tqdm(total=total_runs, desc=f"正在翻译: {filename}") as pbar:
        # 处理正文段落
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():  # 跳过空段落
                    for run in paragraph.runs:
                        if run.text.strip():  # 跳过空文本
                            # 翻译文本
                            translated_text = await self.translator.translate(run.text, preferences)
                            # 保持原有格式，只替换文本
                            run.text = translated_text
                            pbar.update(1)
                            if self.progress_tracker:
                                self.progress_tracker.update(1)
                            # 每次翻译后让出控制权
                            await asyncio.sleep(0)

            # 处理表格（如果需要）
            if not self.config.skip_tables:
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            for paragraph in cell.paragraphs:
                                if paragraph.text.strip():
                                    for run in paragraph.runs:
                                        if run.text.strip():
                                            translated_text = await self.translator.translate(run.text, preferences)
                                            run.text = translated_text
                                            pbar.update(1)
                                            if self.progress_tracker:
                                                self.progress_tracker.update(1)

            # 处理页眉（如果需要）
            if not self.config.skip_headers:
                for section in doc.sections:
                    for paragraph in section.header.paragraphs:
                        if paragraph.text.strip():
                            for run in paragraph.runs:
                                if run.text.strip():
                                    translated_text = await self.translator.translate(run.text, preferences)
                                    run.text = translated_text
                                    pbar.update(1)
                                    if self.progress_tracker:
                                        self.progress_tracker.update(1)

            # 处理页脚（如果需要）
            if not self.config.skip_footers:
                for section in doc.sections:
                    for paragraph in section.footer.paragraphs:
                        if paragraph.text.strip():
                            for run in paragraph.runs:
                                if run.text.strip():
                                    translated_text = await self.translator.translate(run.text, preferences)
                                    run.text = translated_text
                                    pbar.update(1)
                                    if self.progress_tracker:
                                        self.progress_tracker.update(1)

        # 保存文档
        output_buffer = BytesIO()
        doc.save(output_buffer)
        output_buffer.seek(0)

        # 如果指定了输出路径，同时保存到文件
        if output_path:
            doc.save(output_path)

        return output_buffer