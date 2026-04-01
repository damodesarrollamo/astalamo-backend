import pdfplumber
import io

def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extrae texto de un PDF de carta natal de losarcanos.com"""
    text = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()
