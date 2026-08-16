import pymupdf as fitz
from pathlib import Path
import logging

logger = logging.getLogger("ragx.document_parser")

class DocumentParser:
    @staticmethod
    def parse_pdf(file_path: Path) -> dict:
        """
        Extracts text from a PDF file page by page using PyMuPDF.
        Returns metadata and list of page dictionaries with page numbers.
        """
        doc = fitz.open(file_path)
        total_pages = len(doc)
        pages_content = []
        full_text_list = []

        for page_num in range(total_pages):
            page = doc.load_page(page_num)
            page_text = page.get_text("text").strip()
            
            pages_content.append({
                "page_number": page_num + 1,
                "text": page_text
            })
            if page_text:
                full_text_list.append(page_text)

        doc.close()


        total_characters = sum(len(p["text"]) for p in pages_content)
        
        return {
            "file_name": file_path.name,
            "total_pages": total_pages,
            "extracted_pages": len(pages_content),
            "total_characters": total_characters,
            "pages": pages_content,
            "full_text": "\n\n".join(full_text_list)
        }

    @staticmethod
    def parse_txt(file_path: Path) -> dict:
        """
        Extracts text from plain TXT files.
        """
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().strip()

        return {
            "file_name": file_path.name,
            "total_pages": 1,
            "extracted_pages": 1,
            "total_characters": len(content),
            "pages": [{"page_number": 1, "text": content}],
            "full_text": content
        }

    @classmethod
    def parse_document(cls, file_path: Path) -> dict:
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            return cls.parse_pdf(file_path)
        elif ext in [".txt", ".md"]:
            return cls.parse_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
