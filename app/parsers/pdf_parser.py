import fitz  # PyMuPDF
import base64
from typing import List, Dict, Any, Optional
from .base import BaseParser
from ..core.translator import Translator, TranslationPreferences


class PDFParser(BaseParser):
    def __init__(self, file_path: str, translator: Optional[Translator] = None):
        super().__init__(file_path)
        self.logger.info("Opening PDF file...")
        self.doc = fitz.open(self.file_path)
        self.translator = translator or Translator()
        self.translation_preferences = TranslationPreferences(
            source_lang='en',
            target_lang='zh',
            formality_level='正式',
            domain='技术'
        )
        self.logger.info(f"PDF opened successfully. Total pages: {len(self.doc)}")

    def _extract_images(self, page: fitz.Page) -> List[Dict[str, Any]]:
        """Extract images from a page and convert to base64"""
        images = []
        image_list = page.get_images(full=True)

        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                base_image = self.doc.extract_image(xref)
                image_data = base_image["image"]
                image_b64 = base64.b64encode(image_data).decode()

                # Get image position on page
                image_rect = page.get_image_bbox(img)

                # Convert coordinates to points
                images.append({
                    'type': 'image',
                    'data': f"data:image/{base_image['ext']};base64,{image_b64}",
                    'bbox': {
                        'x0': image_rect.x0,
                        'y0': image_rect.y0,
                        'x1': image_rect.x1,
                        'y1': image_rect.y1,
                        'width': image_rect.width,
                        'height': image_rect.height
                    }
                })
                self.logger.info(f"Extracted image {img_index + 1} from page")
            except Exception as e:
                self.logger.error(f"Error extracting image: {str(e)}")

        return images

    def parse(self) -> List[Dict[str, Any]]:
        content_blocks = []

        for page_num, page in enumerate(self.doc, 1):
            self.logger.info(f"Processing page {page_num}/{len(self.doc)}")

            page_rect = page.rect
            page_info = {
                'width': page_rect.width,
                'height': page_rect.height
            }

            # Extract images
            images = self._extract_images(page)
            content_blocks.extend([{
                'page_number': page_num,
                'page_info': page_info,
                **img
            } for img in images])

            # Extract and translate text blocks
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        line_spans = []
                        original_text = ""

                        # 收集该行的所有文本
                        for span in line["spans"]:
                            original_text += span['text']

                        # 如果有文本内容则进行翻译
                        if original_text.strip():
                            try:
                                translated_text = self.translator.translate(
                                    original_text,
                                    self.translation_preferences
                                )
                                self.logger.info(f"Translated text: {original_text} -> {translated_text}")
                            except Exception as e:
                                self.logger.error(f"Translation failed: {str(e)}")
                                translated_text = original_text

                            # 创建翻译后的 span
                            for span in line["spans"]:
                                # 原始文本 span
                                line_spans.append({
                                    'type': 'text',
                                    'content': span['text'],
                                    'page_number': page_num,
                                    'page_info': page_info,
                                    'style': {
                                        'font': span['font'],
                                        'size': span['size'],
                                        'color': span.get('color', '#000000'),
                                        'flags': span.get('flags', 0),
                                        'bbox': {
                                            'x0': span['bbox'][0],
                                            'y0': span['bbox'][1],
                                            'x1': span['bbox'][2],
                                            'y1': span['bbox'][3]
                                        }
                                    }
                                })

                                # 翻译文本 span (在原文下方)
                                translated_span = {
                                    'type': 'text',
                                    'content': translated_text,
                                    'page_number': page_num,
                                    'page_info': page_info,
                                    'style': {
                                        'font': span['font'],
                                        'size': span['size'],
                                        'color': '#0066cc',  # 使用不同颜色区分翻译
                                        'flags': span.get('flags', 0),
                                        'bbox': {
                                            'x0': span['bbox'][0],
                                            'y0': span['bbox'][1] + span['size'] + 2,  # 向下偏移
                                            'x1': span['bbox'][2],
                                            'y1': span['bbox'][3] + span['size'] + 2
                                        }
                                    }
                                }
                                line_spans.append(translated_span)

                        # 合并同一行的 spans
                        if line_spans:
                            content_blocks.append({
                                'type': 'line',
                                'spans': line_spans,
                                'page_number': page_num,
                                'page_info': page_info,
                                'bbox': {
                                    'x0': min(span['style']['bbox']['x0'] for span in line_spans),
                                    'y0': min(span['style']['bbox']['y0'] for span in line_spans),
                                    'x1': max(span['style']['bbox']['x1'] for span in line_spans),
                                    'y1': max(span['style']['bbox']['y1'] for span in line_spans)
                                }
                            })

            self.logger.info(f"Completed page {page_num}")

        return content_blocks

    def to_html(self, parsed_content: Optional[List[Dict[str, Any]]] = None) -> str:
        if parsed_content is None:
            parsed_content = self.parse()

        # 提取第一页的尺寸作为基准
        first_page = next((block for block in parsed_content if 'page_info' in block), None)
        page_width = first_page['page_info']['width'] if first_page else 595
        page_height = first_page['page_info']['height'] if first_page else 842

        html_parts = ['<!DOCTYPE html><html><head>',
                      '<meta charset="UTF-8">',
                      '<style>',
                      f'''
                     body {{ margin: 0; padding: 20px; }}
                     .page {{ 
                         position: relative;
                         width: 1000px;
                         height: {page_height}px;
                         margin: 20px auto;
                         background: white;
                         box-shadow: 0 0 10px rgba(0,0,0,0.1);
                         overflow: hidden;
                     }}
                     .line {{ 
                         position: absolute;
                         white-space: nowrap;
                         transform-origin: left top;
                     }}
                     .text-span {{
                         display: inline-block;
                         white-space: pre;
                     }}
                     .image-block {{
                         position: absolute;
                         object-fit: contain;
                     }}
                     ''',
                      '</style>',
                      '</head><body>']

        current_page = 0
        for block in sorted(parsed_content, key=lambda x: (x['page_number'], x.get('bbox', {}).get('y0', 0))):
            if block['page_number'] != current_page:
                if current_page != 0:
                    html_parts.append('</div>')
                html_parts.append(f'<div class="page" id="page-{block["page_number"]}">')
                current_page = block['page_number']

            if block['type'] == 'line':
                line_style = f'''
                    left: {block['bbox']['x0']}px;
                    top: {block['bbox']['y0']}px;
                '''
                html_parts.append(f'<div class="line" style="{line_style}">')

                for span in block['spans']:
                    span_style = f'''
                        font-family: "{span['style']['font']}";
                        font-size: {span['style']['size']}px;
                        color: {span['style']['color']};
                    '''
                    if span['style']['flags'] & 2 ** 0:  # superscript
                        span_style += 'vertical-align: super;'
                    if span['style']['flags'] & 2 ** 1:  # italic
                        span_style += 'font-style: italic;'
                    if span['style']['flags'] & 2 ** 2:  # serifed
                        span_style += 'font-family: serif;'

                    html_parts.append(
                        f'<span class="text-span" style="{span_style}">{span["content"]}</span>'
                    )

                html_parts.append('</div>')

            elif block['type'] == 'image':
                style = f'''
                    left: {block['bbox']['x0']}px;
                    top: {block['bbox']['y0']}px;
                    width: {block['bbox']['width']}px;
                    height: {block['bbox']['height']}px;
                '''
                html_parts.append(
                    f'<img class="image-block" style="{style}" src="{block["data"]}" />'
                )

        if current_page != 0:
            html_parts.append('</div>')

        html_parts.append('</body></html>')
        return '\n'.join(html_parts)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.info("Closing PDF file")
        self.doc.close()
        super().__exit__(exc_type, exc_val, exc_tb)