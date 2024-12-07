from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTTextContainer, LTChar, LTTextBox
from pdfminer.pdfpage import PDFPage
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re
from .base import BaseParser
from ..core.translator import Translator, TranslationPreferences


@dataclass
class ParsedBlock:
    text: str
    font_name: str
    font_size: float
    bbox: tuple
    page_number: int
    block_type: str = 'paragraph'
    is_complete: bool = True
    indent_level: float = 0.0  # 缩进级别
    is_continuation: bool = False  # 是否是段落的延续


class PDFMinerParser(BaseParser):
    def __init__(self, file_path: str, translator: Optional[Translator] = None):
        super().__init__(file_path)
        self.translator = translator or Translator()
        self.translation_preferences = TranslationPreferences(
            source_lang='en',
            target_lang='zh',
            formality_level='正式',
            domain='技术'
        )
        self.laparams = LAParams(
            line_margin=0.5,
            word_margin=0.1,
            char_margin=2.0,
            boxes_flow=0.5,
            detect_vertical=True,
            all_texts=False
        )
        # 段落识别模式
        self.paragraph_patterns = {
            'ordered': re.compile(r'^(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)[,.]'),
            'bullet': re.compile(r'^\s*[•\-*]\s+'),
            'numeric': re.compile(r'^\s*\d+\.\s+'),
            'sentence_end': re.compile(r'[.!?。！？…]$'),
            'capital_start': re.compile(r'^[A-Z]'),
        }
        self.logger.info("PDFMiner parser initialized with enhanced paragraph recognition")

    def _get_font_info(self, text_element: LTTextContainer) -> tuple:
        """获取字体信息"""
        for char in text_element:
            if isinstance(char, LTChar):
                return char.fontname, char.size
        return ('default', 12)

    def _is_new_paragraph_start(self, text: str) -> bool:
        """判断是否是新段落的开始"""
        text = text.strip()
        if not text:
            return False

        # 检查是否是有序段落标记
        if self.paragraph_patterns['ordered'].match(text):
            return True

        # 检查是否是项目符号
        if self.paragraph_patterns['bullet'].match(text):
            return True

        # 检查是否是数字编号
        if self.paragraph_patterns['numeric'].match(text):
            return True

        # 检查是否以大写字母开头且上一句是完整句子
        return bool(self.paragraph_patterns['capital_start'].match(text))

    def _should_merge_blocks(self, block1: ParsedBlock, block2: ParsedBlock) -> bool:
        """判断两个块是否应该合并"""
        # 如果是跨页的情况
        if block1.page_number != block2.page_number:
            return (
                    block1.font_name == block2.font_name and
                    abs(block1.font_size - block2.font_size) < 0.1 and
                    not self.paragraph_patterns['sentence_end'].search(block1.text.strip()) and
                    block2.page_number == block1.page_number + 1
            )

        # 检查字体一致性
        font_consistent = (
                block1.font_name == block2.font_name and
                abs(block1.font_size - block2.font_size) < 0.1
        )

        # 检查垂直位置
        vertical_gap = block2.bbox[1] - block1.bbox[3]
        reasonable_gap = vertical_gap < 20  # 合理的行间距

        # 检查缩进级别
        indent_consistent = abs(block1.indent_level - block2.indent_level) < 10

        # 检查是否是新段落开始
        is_new_paragraph = self._is_new_paragraph_start(block2.text)

        # 综合判断
        return (
                font_consistent and
                reasonable_gap and
                indent_consistent and
                not is_new_paragraph
        )

    def _merge_blocks(self, block1: ParsedBlock, block2: ParsedBlock) -> ParsedBlock:
        """合并两个文本块"""
        # 处理文本合并的逻辑
        text1 = block1.text.strip()
        text2 = block2.text.strip()

        # 根据不同情况添加适当的空格
        if text1.endswith('-'):
            merged_text = text1[:-1] + text2
        else:
            merged_text = text1 + (' ' if not text1.endswith(' ') else '') + text2

        return ParsedBlock(
            text=merged_text,
            font_name=block1.font_name,
            font_size=block1.font_size,
            bbox=(
                min(block1.bbox[0], block2.bbox[0]),
                min(block1.bbox[1], block2.bbox[1]),
                max(block1.bbox[2], block2.bbox[2]),
                max(block1.bbox[3], block2.bbox[3])
            ),
            page_number=block1.page_number,
            block_type=block1.block_type,
            indent_level=block1.indent_level,
            is_continuation=True
        )

    def _extract_page_blocks(self, page_layout, page_num: int) -> List[ParsedBlock]:
        """提取页面中的文本块"""
        page_blocks = []

        for element in page_layout:
            if isinstance(element, LTTextBox):
                text = element.get_text().strip()
                if text:
                    font_name, font_size = self._get_font_info(element)

                    # 计算缩进级别
                    indent_level = element.bbox[0]

                    # 判断是否是段落开始
                    is_new_paragraph = self._is_new_paragraph_start(text)

                    block = ParsedBlock(
                        text=text,
                        font_name=font_name,
                        font_size=font_size,
                        bbox=element.bbox,
                        page_number=page_num,
                        indent_level=indent_level,
                        is_continuation=not is_new_paragraph
                    )
                    page_blocks.append(block)

        return page_blocks

    def _process_blocks(self, blocks: List[ParsedBlock]) -> List[ParsedBlock]:
        """处理所有文本块，包括跨页合并"""
        if not blocks:
            return []

        processed_blocks = []
        current_block = blocks[0]

        for next_block in blocks[1:]:
            if self._should_merge_blocks(current_block, next_block):
                current_block = self._merge_blocks(current_block, next_block)
            else:
                if current_block.text.strip():  # 确保不添加空块
                    processed_blocks.append(current_block)
                current_block = next_block

        if current_block.text.strip():
            processed_blocks.append(current_block)

        return processed_blocks

    def parse(self) -> List[Dict[str, Any]]:
        """解析PDF文件并返回结构化内容"""
        try:
            # 收集所有页面的块
            all_blocks = []
            with open(self.file_path, 'rb') as file:
                for page_num, page_layout in enumerate(extract_pages(
                        file, laparams=self.laparams), 1):
                    page_blocks = self._extract_page_blocks(page_layout, page_num)
                    all_blocks.extend(page_blocks)

            # 处理所有文本块（包括跨页合并）
            processed_blocks = self._process_blocks(all_blocks)

            # 转换为最终输出格式
            result_blocks = []
            for block in processed_blocks:
                try:
                    translated_text = self.translator.translate(
                        block.text,
                        self.translation_preferences
                    )

                    result_blocks.append({
                        'type': 'paragraph',
                        'page_number': block.page_number,
                        'block_type': block.block_type,
                        'spans': [{
                            'type': 'text',
                            'content': translated_text,
                            'style': {
                                'font': block.font_name,
                                'size': block.font_size
                            }
                        }],
                        'bbox': block.bbox,
                        'indent_level': block.indent_level
                    })
                except Exception as e:
                    self.logger.error(f"Translation failed for block: {str(e)}")

            self.logger.info(f"Successfully parsed {len(result_blocks)} blocks")
            return result_blocks

        except Exception as e:
            self.logger.error(f"PDF parsing failed: {str(e)}")
            return []

    def to_html(self, parsed_content: Optional[List[Dict[str, Any]]] = None) -> str:
        """将解析后的内容转换为HTML"""
        if parsed_content is None:
            parsed_content = self.parse()

        if not parsed_content:
            return '<div class="error">No content found in PDF</div>'

        html_parts = ['<!DOCTYPE html><html><head>',
                      '<meta charset="UTF-8">',
                      '<style>',
                      '''
                      body { 
                          margin: 0; 
                          padding: 20px;
                          font-family: Arial, sans-serif;
                      }
                      .page { 
                          position: relative;
                          width: 800px;
                          margin: 20px auto;
                          padding: 40px;
                          background: white;
                          box-shadow: 0 0 10px rgba(0,0,0,0.1);
                          min-height: 500px;
                      }
                      .paragraph { 
                          margin-bottom: 1.5em;
                          line-height: 1.6;
                      }
                      ''',
                      '</style></head><body>']

        current_page = None
        for block in parsed_content:
            if block['page_number'] != current_page:
                if current_page is not None:
                    html_parts.append('</div>')
                html_parts.append(f'<div class="page" id="page-{block["page_number"]}">')
                current_page = block['page_number']

            style = [
                f"font-size: {block['spans'][0]['style']['size']}px",
                f"margin-left: {block['indent_level']}px"
            ]
            style_str = '; '.join(style)

            html_parts.append(f'<div class="paragraph" style="{style_str}">')
            html_parts.append(block['spans'][0]['content'])
            html_parts.append('</div>')

        if current_page is not None:
            html_parts.append('</div>')

        html_parts.append('</body></html>')
        return '\n'.join(html_parts)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.info("Closing PDF parser")
        super().__exit__(exc_type, exc_val, exc_tb)