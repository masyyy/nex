"""
Functions for parsing and chunking documents.
"""
import logging
import fitz  # PyMuPDF
from typing import List

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> List[str]:
    """Extract text from a PDF file as a list of pages.

    Args:
        file_path: Path to the PDF file.

    Returns:
        List of text chunks, one per page.
    """
    try:
        doc = fitz.open(file_path)
        pages = [page.get_text() for page in doc]
        log.info(f"Extracted {len(pages)} pages from PDF")
        return pages
    except Exception as e:
        log.error(f"Failed to extract text from PDF: {e}")
        raise


def extract_text_from_txt(file_path: str) -> List[str]:
    """Extract text from a text file.

    Args:
        file_path: Path to the text file.

    Returns:
        List with a single string (whole file content).
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return [content]
    except Exception as e:
        log.error(f"Failed to extract text from text file: {e}")
        raise