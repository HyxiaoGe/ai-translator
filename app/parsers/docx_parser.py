from docx import Document
from typing import List, Dict, Any, Optional
from .base import BaseParser


class DocxParser(BaseParser):
    def __init__(self, file_path: str):
        super().__init__(file_path)
        self.doc = Document(self.file_path)

    def parse(self) -> List[Dict[str, Any]]:
        content_blocks = []

        for paragraph in self.doc.paragraphs:
            # 跳过空白段落
            if not paragraph.text.strip():
                continue

            # 获取样式信息
            style = {
                'name': paragraph.style.name,
                'font_size': 12,  # Default size
                'is_bold': any(run.bold for run in paragraph.runs),
                'is_italic': any(run.italic for run in paragraph.runs)
            }

            # 根据样式确定块类型
            block_type = 'heading' if 'Heading' in paragraph.style.name else 'paragraph'

            content_blocks.append({
                'content': paragraph.text,
                'page_number': 1,
                'block_type': block_type,
                'style': style
            })

        return content_blocks

    def to_html(self, parsed_content: Optional[List[Dict[str, Any]]] = None) -> str:
        if parsed_content is None:
            parsed_content = self.parse()

        html_parts = ['<!DOCTYPE html><html><head>',
                      '<meta charset="UTF-8">',
                      '<style>',
                      '.document { margin: 20px auto; padding: 20px; max-width: 800px; }',
                      '.block { margin: 10px 0; }',
                      '.heading { font-weight: bold; font-size: 1.2em; }',
                      '</style>',
                      '</head><body>',
                      '<div class="document">']

        for block in parsed_content:
            style = []
            if block['style']['is_bold']:
                style.append('font-weight: bold')
            if block['style']['is_italic']:
                style.append('font-style: italic')

            class_name = 'block ' + block['block_type']
            style_str = '; '.join(style)

            html_parts.append(
                f'<div class="{class_name}" style="{style_str}">{block["content"]}</div>'
            )

        html_parts.extend(['</div>', '</body></html>'])
        return '\n'.join(html_parts)