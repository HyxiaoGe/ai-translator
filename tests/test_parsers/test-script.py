from pathlib import Path
from app.parsers.pdf_parser import PDFMinerParser
from app.parsers.docx_parser import DocxParser
from app.utils.logger import setup_logger


def test_parse_and_preview(file_path: str):
    """Test function to parse a document and save HTML preview"""
    logger = setup_logger('test_script')
    logger.info(f"Starting document processing for: {file_path}")

    file_path = Path(file_path)
    output_path = file_path.with_suffix('.html')

    logger.info(f"Output will be saved to: {output_path}")

    try:
        if file_path.suffix.lower() == '.pdf':
            logger.info("Detected PDF file")
            parser = PDFMinerParser(str(file_path))
        elif file_path.suffix.lower() in ('.docx', '.doc'):
            logger.info("Detected Word document")
            parser = DocxParser(str(file_path))
        else:
            logger.error(f"Unsupported file type: {file_path.suffix}")
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

        with parser:
            logger.info("Starting parsing and HTML generation")
            html_content = parser.to_html()

            logger.info("Saving HTML output")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"Preview generated successfully: {output_path}")

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    test_parse_and_preview(r"E:\Documents\DocDemo\book2.pdf")