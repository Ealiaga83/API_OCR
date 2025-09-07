from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
import io

# Ruta a Tesseract en Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
#POPPLER_PATH = "/usr/bin"  # En Docker, poppler-utils se instala aquí
def extract_text_from_image(image_bytes):
    image = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(image)

def extract_text_from_pdf(pdf_bytes, poppler_path):
    images = convert_from_bytes(pdf_bytes, dpi=300, poppler_path=poppler_path)
    text_pages = []
    for i, image in enumerate(images):
        text = pytesseract.image_to_string(image)
        text_pages.append(f"\n--- Página {i+1} ---\n{text}")
    return "\n".join(text_pages)