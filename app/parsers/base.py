from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.utils.logger import setup_logger


class BaseParser(ABC):
    """Base class for all document parsers"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Setup logger for this class
        self.logger = setup_logger(self.__class__.__name__)
        self.logger.info(f"Initializing parser for file: {self.file_path}")

    @abstractmethod
    def parse(self) -> List[Dict[str, Any]]:
        """Parse the document and return a list of content blocks"""
        pass

    @abstractmethod
    def to_html(self, parsed_content: Optional[List[Dict[str, Any]]] = None) -> str:
        """Convert parsed content to HTML format"""
        pass

    def __enter__(self):
        self.logger.info("Starting document processing")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.logger.error(f"Error during processing: {exc_val}")
        else:
            self.logger.info("Document processing completed successfully")