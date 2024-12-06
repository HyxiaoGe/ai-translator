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

    def parse(self) -> List[Dict[str, Any]]:
        content_blocks = []
        
        try:
            for page_num, page in enumerate(self.doc, 1):
                text = page.get_text()
                if not text.strip():
                    self.logger.warning(f"Page {page_num} appears to be empty")
                    continue
                    
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if "lines" not in block:
                        continue
                        
                    text = " ".join(span["text"] for line in block["lines"] 
                                  for span in line["spans"]).strip()
                    if not text:
                        continue
                        
                    try:
                        translated_text = self.translator.translate(text)
                        first_span = block["lines"][0]["spans"][0]
                        
                        content_blocks.append({
                            'type': 'paragraph',
                            'page_number': page_num,
                            'spans': [{
                                'type': 'text',
                                'content': translated_text,
                                'style': {
                                    'font': first_span['font'],
                                    'size': first_span['size'],
                                    'color': first_span.get('color', '#000000')
                                }
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

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.info("Closing PDF file")
        self.doc.close()
        super().__exit__(exc_type, exc_val, exc_tb)