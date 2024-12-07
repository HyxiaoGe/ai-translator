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
        # 设置段落识别参数
        self.params = {
            'line_spacing_threshold': 2.0,  # 行间距阈值
            'indent_threshold': 10.0,  # 缩进阈值
            'font_size_diff_threshold': 0.5,  # 字体大小差异阈值
            'min_paragraph_length': 20,  # 最小段落长度
            'max_vertical_gap': 15.0  # 最大垂直间距
        }
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

    def to_html(self, parsed_content: Optional[List[Dict[str, Any]]] = None) -> str:
        if parsed_content is None:
            parsed_content = self.parse()

        if not parsed_content:
            self.logger.warning("No content blocks found")
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
                      .text-span {
                          display: inline;
                      }
                      .error {
                          color: red;
                          text-align: center;
                          padding: 20px;
                      }
                      ''',
                      '</style></head><body>']

        # 修改排序逻辑，添加安全检查
        def safe_sort_key(x):
            if isinstance(x, dict):
                page_num = x.get('page_number', 0)
                bbox = x.get('bbox', {})
                y0 = bbox.get('y0', 0) if isinstance(bbox, dict) else 0
                return (page_num, y0)
            return (0, 0)  # 对于非字典类型的元素，返回默认值

        try:
            sorted_content = sorted(parsed_content, key=safe_sort_key)
        except Exception as e:
            self.logger.error(f"Sorting failed: {str(e)}")
            sorted_content = parsed_content  # 如果排序失败，使用原始顺序

        current_page = None
        for block in sorted_content:
            if not isinstance(block, dict):
                self.logger.warning(f"Skipping non-dict block: {block}")
                continue

            if block['page_number'] != current_page:
                if current_page is not None:
                    html_parts.append('</div>')
                html_parts.append(f'<div class="page" id="page-{block["page_number"]}">')
                current_page = block['page_number']

            if block['type'] == 'paragraph':
                style = f"font-size: {block['spans'][0]['style']['size']}px;"
                html_parts.append(f'<div class="paragraph" style="{style}">')
                html_parts.append(block['spans'][0]['content'])
                html_parts.append('</div>')

        if current_page is not None:
            html_parts.append('</div>')

        html_parts.append('</body></html>')

        html = '\n'.join(html_parts)
        self.logger.debug(f"Generated HTML length: {len(html)}")
        return html

    def _should_merge_blocks(self, block1: Dict[str, Any], block2: Dict[str, Any]) -> bool:
        """
        判断两个文本块是否应该合并

        参数:
        block1: 第一个文本块
        block2: 第二个文本块

        返回:
        bool: 是否应该合并
        """
        try:
            # 获取两个块的边界框
            bbox1 = block1["bbox"]
            bbox2 = block2["bbox"]

            # 计算垂直间距
            vertical_distance = bbox2[1] - bbox1[3]  # y0 of block2 - y1 of block1

            # 计算水平重叠
            horizontal_overlap = (
                                         min(bbox1[2], bbox2[2]) - max(bbox1[0], bbox2[0])
                                 ) > 0

            # 获取第一个块的字体信息
            font1 = block1["lines"][0]["spans"][0]["font"]
            font2 = block2["lines"][0]["spans"][0]["font"]

            # 判断合并条件：
            # 1. 垂直间距在阈值内
            # 2. 存在水平重叠
            # 3. 使用相同字体
            return (
                    vertical_distance <= self.line_spacing_threshold
                    and horizontal_overlap
                    and font1 == font2
            )
        except (KeyError, IndexError) as e:
            self.logger.warning(f"Error checking blocks for merge: {str(e)}")
            return False

    def _merge_text_blocks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并应该属于同一段落的文本块

        参数:
        blocks: 原始文本块列表

        返回:
        List[Dict[str, Any]]: 合并后的文本块列表
        """
        if not blocks:
            return blocks

        merged_blocks = [blocks[0]]

        for current_block in blocks[1:]:
            previous_block = merged_blocks[-1]

            if self._should_merge_blocks(previous_block, current_block):
                # 合并文本内容
                text1 = " ".join(
                    span["text"] for line in previous_block["lines"]
                    for span in line["spans"]
                )
                text2 = " ".join(
                    span["text"] for line in current_block["lines"]
                    for span in line["spans"]
                )

                # 更新边界框
                previous_block["bbox"] = (
                    min(previous_block["bbox"][0], current_block["bbox"][0]),  # x0
                    previous_block["bbox"][1],  # y0
                    max(previous_block["bbox"][2], current_block["bbox"][2]),  # x1
                    current_block["bbox"][3]  # y1
                )

                # 合并行信息
                combined_text = f"{text1} {text2}"
                previous_block["lines"] = [{
                    "spans": [{
                        "text": combined_text,
                        "font": previous_block["lines"][0]["spans"][0]["font"],
                        "size": previous_block["lines"][0]["spans"][0]["size"]
                    }]
                }]
            else:
                merged_blocks.append(current_block)

        return merged_blocks

    def parse(self) -> List[Dict[str, Any]]:
        content_blocks = []

        try:
            for page_num, page in enumerate(self.doc, 1):
                text = page.get_text()
                if not text.strip():
                    self.logger.warning(f"Page {page_num} appears to be empty")
                    continue

                # 获取页面的文本块
                blocks = page.get_text("dict")["blocks"]

                # 过滤有效的文本块
                text_blocks = [
                    block for block in blocks
                    if "lines" in block and any(
                        span["text"].strip()
                        for line in block["lines"]
                        for span in line["spans"]
                    )
                ]

                # 合并文本块
                merged_blocks = self._merge_text_blocks(text_blocks)

                # 处理合并后的块
                for block in merged_blocks:
                    text = " ".join(
                        span["text"] for line in block["lines"]
                        for span in line["spans"]
                    ).strip()

                    if not text:
                        continue

                    try:
                        block_props = self._get_block_properties(block)
                        block_type = self._classify_block(block_props)

                        translated_text = self.translator.translate(text)
                        first_span = block["lines"][0]["spans"][0]

                        # 根据块类型设置不同的样式
                        style = {
                            'font': first_span['font'],
                            'size': (
                                18 if block_type == 'title'
                                else 14 if block_type == 'subtitle'
                                else 10 if block_type == 'footnote'
                                else 12  # 默认正文大小
                            ),
                            'color': first_span.get('color', '#000000')
                        }

                        content_blocks.append({
                            'type': 'paragraph',
                            'page_number': page_num,
                            'block_type': block_type,
                            'spans': [{
                                'type': 'text',
                                'content': translated_text,
                                'style': style
                            }],
                            'bbox': block["bbox"]
                        })
                    except Exception as e:
                        self.logger.error(f"Translation failed: {str(e)}")

            self.logger.info(f"Extracted {len(content_blocks)} content blocks")
            return content_blocks

        except Exception as e:
            self.logger.error(f"PDF parsing failed: {str(e)}")
            return []

    def _get_block_properties(self, block: Dict) -> Dict:
        """获取文本块的关键属性"""
        try:
            first_span = block["lines"][0]["spans"][0]
            return {
                'font': first_span.get('font', ''),
                'size': first_span.get('size', 0),
                'flags': first_span.get('flags', 0),
                'text': " ".join(span["text"] for line in block["lines"]
                                 for span in line["spans"]).strip(),
                'bbox': block["bbox"],
                'indent': block["bbox"][0],  # 左侧缩进位置
                'is_title': first_span.get('size', 0) > 12  # 简单的标题判断
            }
        except (KeyError, IndexError) as e:
            self.logger.warning(f"Error getting block properties: {str(e)}")
            return {}

    def _is_continuation(self, prev_props: Dict, curr_props: Dict) -> bool:
        """判断当前块是否是前一个块的延续"""
        if not (prev_props and curr_props):
            return False

        # 检查字体一致性
        font_consistent = (
                abs(prev_props['size'] - curr_props['size']) <= self.params['font_size_diff_threshold']
                and prev_props['font'] == curr_props['font']
        )

        # 检查垂直间距
        vertical_gap = curr_props['bbox'][1] - prev_props['bbox'][3]
        valid_gap = 0 <= vertical_gap <= self.params['max_vertical_gap']

        # 检查是否是新段落的开始（通过缩进判断）
        indent_diff = abs(curr_props['indent'] - prev_props['indent'])
        is_new_paragraph = indent_diff > self.params['indent_threshold']

        # 内容连续性检查（检查上一段是否以完整的句子结束）
        prev_text_complete = prev_props['text'].strip().endswith(('.', '!', '?', '。', '！', '？'))

        return (
                font_consistent
                and valid_gap
                and not is_new_paragraph
                and not (prev_text_complete and curr_props['text'][0].isupper())
        )

    def _classify_block(self, block_props: Dict) -> str:
        """对文本块进行分类"""
        if not block_props:
            return 'unknown'

        text = block_props['text']

        # 标题检测
        if block_props['is_title']:
            return 'title'

        # 脚注检测 (简单实现，可以根据需要扩展)
        if text.startswith(('*', '1.', '[1]', '注：', 'Note:')):
            return 'footnote'

        # 正文检测
        if len(text) >= self.params['min_paragraph_length']:
            return 'body'

        return 'other'

    def _merge_text_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """使用增强的规则合并文本块"""
        if not blocks:
            return []

        merged_blocks = []
        current_block = blocks[0].copy()
        current_props = self._get_block_properties(current_block)

        for next_block in blocks[1:]:
            next_props = self._get_block_properties(next_block)

            # 获取块的类型
            current_type = self._classify_block(current_props)
            next_type = self._classify_block(next_props)

            # 如果当前块和下一个块都是正文，且满足连续性条件
            if (current_type == 'body' and next_type == 'body' and
                    self._is_continuation(current_props, next_props)):
                # 合并文本内容
                current_text = current_props['text']
                next_text = next_props['text']

                # 添加适当的空格
                if not current_text.endswith(('-', ' ')):
                    current_text += ' '

                # 更新当前块的内容和边界框
                current_block["lines"][0]["spans"][0]["text"] = current_text + next_text
                current_block["bbox"] = (
                    min(current_block["bbox"][0], next_block["bbox"][0]),
                    current_block["bbox"][1],
                    max(current_block["bbox"][2], next_block["bbox"][2]),
                    next_block["bbox"][3]
                )
                # 更新属性
                current_props = self._get_block_properties(current_block)
            else:
                # 如果不能合并，保存当前块并开始新的块
                merged_blocks.append(current_block)
                current_block = next_block.copy()
                current_props = next_props

        # 添加最后一个块
        merged_blocks.append(current_block)
        return merged_blocks

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.info("Closing PDF file")
        self.doc.close()
        super().__exit__(exc_type, exc_val, exc_tb)