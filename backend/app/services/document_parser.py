from io import BytesIO
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader


def extract_text(file_path: Path, filename: str) -> str:
    """
    根据文件类型提取文本。
    支持 PDF、TXT、DOCX。
    """
    extension = Path(filename).suffix.lower()

    if not file_path.exists():
        raise FileNotFoundError("Document file not found")

    file_bytes = file_path.read_bytes()

    if extension == ".pdf":
        reader = PdfReader(BytesIO(file_bytes))

        if reader.is_encrypted:
            raise ValueError("Encrypted PDF files are not supported")

        pages = []

        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text)

        text = "\n\n".join(pages)

    elif extension == ".txt":
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as e:
            raise ValueError(
                "TXT file must use UTF-8 encoding"
            ) from e

    elif extension == ".docx":
        doc = DocxDocument(BytesIO(file_bytes))

        paragraphs = [
            paragraph.text
            for paragraph in doc.paragraphs
            if paragraph.text.strip()
        ]

        table_rows = []

        for table in doc.tables:
            for row in table.rows:
                cells = [
                    cell.text.strip()
                    for cell in row.cells
                    if cell.text.strip()
                ]

                if cells:
                    table_rows.append(" | ".join(cells))

        text = "\n".join(paragraphs + table_rows)

    else:
        raise ValueError("Unsupported document format")

    text = text.strip()

    if not text:
        raise ValueError(
            "No readable text found in the document"
        )

    return text