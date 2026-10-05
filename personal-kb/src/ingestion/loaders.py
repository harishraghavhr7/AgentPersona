import logging
import os
from pathlib import Path
import re
from typing import List, Optional
from llama_index.core import SimpleDirectoryReader
from llama_index.core.schema import Document

from config.settings import get_settings
from models.metadata import SourceType

logger = logging.getLogger(__name__)


def get_supported_extensions() -> List[str]:
    return [
        ".md", ".markdown",
        ".txt",
        ".pdf",
        ".html", ".htm",
        ".eml", ".msg",
        ".docx", ".doc",
    ]


def extract_text_from_docx(file_path: Path) -> str:
    """Extract plain text paragraphs from a .docx file using standard library zipfile + XML."""
    import zipfile
    import xml.etree.ElementTree as ET
    try:
        with zipfile.ZipFile(file_path) as docx:
            tree = ET.fromstring(docx.read("word/document.xml"))
            namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs = []
            for p in tree.iterfind(".//w:p", namespaces):
                texts = [node.text for node in p.iterfind(".//w:t", namespaces) if node.text]
                if texts:
                    paragraphs.append("".join(texts))
            return "\n\n".join(paragraphs)
    except Exception as e:
        logger.warning(f"Error reading docx XML from {file_path}: {e}. Trying binary extraction.")
        return extract_text_from_binary_doc(file_path)


def extract_text_from_binary_doc(file_path: Path) -> str:
    """Extract printable strings from legacy .doc or binary files."""
    try:
        content = file_path.read_bytes()
        # Find sequences of printable ASCII/Latin-1 characters
        text_pieces = re.findall(b"[\x20-\x7E\r\n\t]{4,}", content)
        decoded = [p.decode("latin1", errors="ignore").strip() for p in text_pieces]
        # Filter out common binary markup/xml artifacts
        clean_lines = [
            line for line in decoded
            if len(line) > 3 and not line.startswith(("<?xml", "word/", "[Content_Types]", "urn:", "http:"))
        ]
        return "\n\n".join(clean_lines)
    except Exception as e:
        logger.error(f"Error extracting text from binary doc {file_path}: {e}")
        return ""


def extract_text_from_file(file_path: Path) -> str:
    """Extract clean text content from any supported file format."""
    suffix = file_path.suffix.lower()

    if suffix == ".docx":
        return extract_text_from_docx(file_path)
    elif suffix == ".doc":
        # Check if it's actually an OpenXML docx with .doc extension or binary .doc
        try:
            return extract_text_from_docx(file_path)
        except Exception:
            return extract_text_from_binary_doc(file_path)
    elif suffix in [".md", ".markdown", ".txt", ".html", ".htm"]:
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return file_path.read_text(encoding="latin1", errors="ignore")
    elif suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(file_path))
            pages_text = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages_text)
        except Exception as e:
            logger.warning(f"pypdf extraction failed for {file_path}: {e}")
            return ""
    else:
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return extract_text_from_binary_doc(file_path)


def load_from_directory(
    directory_path: Optional[str] = None,
    recursive: bool = True,
) -> List[Document]:
    """
    Load all supported personal knowledge documents from directory.
    Uses custom extractors for doc/docx and SimpleDirectoryReader for others.
    """
    settings = get_settings()
    target_dir = Path(directory_path or settings.data_dir)

    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)
        return []

    docs: List[Document] = []
    supported_exts = set(get_supported_extensions())

    # Walk directory to pick up all files
    pattern = "**/*" if recursive else "*"
    for item in target_dir.glob(pattern):
        if item.is_file() and item.suffix.lower() in supported_exts:
            try:
                single_docs = load_single_file(str(item))
                docs.extend(single_docs)
            except Exception as e:
                logger.error(f"Error loading {item}: {e}")

    return docs


def load_single_file(file_path: str) -> List[Document]:
    """Load a single file into LlamaIndex Document(s)."""
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = p.suffix.lower()

    # Use specialized high-fidelity extractors for office docs and markdown
    if suffix in [".docx", ".doc"]:
        text = extract_text_from_docx(p) if suffix == ".docx" else extract_text_from_file(p)
        return [
            Document(
                text=text,
                metadata={
                    "file_path": str(p),
                    "file_name": p.name,
                    "source": str(p),
                },
            )
        ]
    elif suffix in [".md", ".markdown", ".txt"]:
        text = extract_text_from_file(p)
        return [
            Document(
                text=text,
                metadata={
                    "file_path": str(p),
                    "file_name": p.name,
                    "source": str(p),
                },
            )
        ]

    # SimpleDirectoryReader fallback for pdfs, html, etc.
    try:
        reader = SimpleDirectoryReader(
            input_files=[str(p)],
            filename_as_id=True,
        )
        return reader.load_data()
    except Exception as e:
        logger.warning(f"SimpleDirectoryReader failed for {p}: {e}. Using raw text extractor.")
        text = extract_text_from_file(p)
        return [
            Document(
                text=text,
                metadata={"file_path": str(p), "file_name": p.name, "source": str(p)},
            )
        ]
