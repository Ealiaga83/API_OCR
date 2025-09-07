from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
import io
import unicodedata
import re
import os
from utils.logger_config import logger
import cv2
import numpy as np
import pdfplumber
import json

# Configura Tesseract para Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_pdfplumber(pdf_bytes):
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        texto = []
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                texto.append(page_text)
        return "\n--- Página PDF ---\n" + "\n".join(texto)

def preprocess_image(image):
    img = np.array(image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(thresh)

def limpiar_texto(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    lineas = texto.splitlines()
    lineas_limpias = [line.strip() for line in lineas if line.strip()]
    return "\n".join(lineas_limpias)

def guardar_texto_ocr(texto: str, nombre_archivo: str = "ocr_output.txt"):
    carpeta = "output"
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre_archivo)
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)
        logger.info(f"Texto OCR guardado en: {ruta}")
    except Exception as e:
        logger.error(f" Error al guardar el archivo OCR: {e}")

def ocr_pdf(pdf_bytes, poppler_path, nombre_archivo_txt="ocr_output.txt"):
    images = convert_from_bytes(pdf_bytes, dpi=300, poppler_path=poppler_path)
    text_pages = []
    for i, image in enumerate(images):
        preprocessed = preprocess_image(image)
        raw_text = pytesseract.image_to_string(preprocessed, config="--psm 11")
        texto_limpio = limpiar_texto(raw_text)
        text_pages.append(f"\n--- Página {i+1} ---\n{texto_limpio}")
    texto_final = "\n".join(text_pages)
    guardar_texto_ocr(texto_final, nombre_archivo=nombre_archivo_txt)
    return texto_final

def extraer_detalles(texto):
    detalles = []
    patron = (
        r"(\d+)\s+"                  # Cod. Principal
        r"(\d+\.\d{2})\s+"           # Cod. Auxiliar
        r"([A-ZÑ\s]+?)\s+"           # Descripción
        r"(\d+\.\d{4})\s+"           # Precio Unitario
        r"(\d+\.\d{2})\s+"           # Subsidio
        r"(\d+\.\d{2})\s+"           # Precio sin Subsidio
        r"(\d+\.\d{2})\s+"           # Descuento
        r"(\d+\.\d{2})"              # Precio Total
    )
    for match in re.finditer(patron, texto):
        (
            cod_principal, cod_auxiliar, descripcion,
            precio_unitario, subsidio, precio_sin_subsidio,
            descuento, precio_total
        ) = match.groups()
        detalles.append({
            "codigo_principal": cod_principal,
            "codigo_auxiliar": cod_auxiliar,
            "cantidad": "1",
            "descripcion": descripcion.strip(),
            "precio_unitario": float(precio_unitario),
            "subsidio": float(subsidio),
            "precio_sin_subsidio": float(precio_sin_subsidio),
            "descuento": float(descuento),
            "precio_total": float(precio_total)
        })
    return detalles

def extraer_formas_pago(texto, valor_total):
    formas = []
    if "SIN UTILIZACION DEL SISTEMA FINANCIERO" in texto.upper():
        formas.append({
            "codigo_pago": "01",
            "descripcion_pago": "Efectivo",
            "valor": float(valor_total) if valor_total else 0.00
        })
    return formas

def extraer_datos_factura(texto):
    def buscar(patron):
        resultado = re.search(patron, texto, re.IGNORECASE)
        return resultado.group(1).strip() if resultado else None

    def convertir_a_float(valor, campo):
        try:
            return float(valor)
        except:
            logger.warning(f"[WARN] Valor inválido en '{campo}': {valor}. Se asigna 0.00")
            return 0.00

    totales = {
        "subtotal_tarifa_especial": convertir_a_float(buscar(r"SUBTOTAL TARIFA ESPECIAL\s*[:\$]?\s*(\d+\.\d{2})"), "subtotal_tarifa_especial"),
        "subtotal_no_objeto_iva": convertir_a_float(buscar(r"SUBTOTAL NO OBJETO DE IVA\s*[:\$]?\s*(\d+\.\d{2})"), "subtotal_no_objeto_iva"),
        "subtotal_exento_iva": convertir_a_float(buscar(r"SUBTOTAL EXENTO DE IVA\s*[:\$]?\s*(\d+\.\d{2})"), "subtotal_exento_iva"),
        "subtotal_sin_impuestos": convertir_a_float(buscar(r"SUBTOTAL SIN IMPUESTOS\s*[:\$]?\s*(\d+\.\d{2})"), "subtotal_sin_impuestos"),
        "total_descuento": convertir_a_float(buscar(r"(TOTAL\s*DESCUENTO|froralbescuento)[^\d]*(\d+\.\d{2})"), "total_descuento"),
        "ice": convertir_a_float(buscar(r"ICE\s*[:\$]?\s*(\d+\.\d{2})"), "ice"),
        "iva_tarifa_especial": convertir_a_float(buscar(r"IVA TARIFA ESPECIAL\s*[:\$]?\s*(\d+\.\d{2})"), "iva_tarifa_especial"),
        "irbpnr": convertir_a_float(buscar(r"IRBPNR\s*[:\$]?\s*(\d+\.\d{2})"), "irbpnr"),
        "propina": convertir_a_float(buscar(r"(PROPINA|propma)[^\d]*(\d+\.\d{2})"), "propina"),
        "valor_total": convertir_a_float(buscar(r"VALOR TOTAL\s*[:\$]?\s*(\d+\.\d{2})"), "valor_total"),
        "valor_total_sin_subsidio": convertir_a_float(buscar(r"VALOR TOTAL SIN SUBSIDIO\s*[:\$]?\s*(\d+\.\d{2})"), "valor_total_sin_subsidio"),
        "ahorro_subsidio": convertir_a_float(buscar(r"AHORRO POR SUBSIDIO\s*[:\$]?\s*(\d+\.\d{2})"), "ahorro_subsidio")
    }

    formas_pago = extraer_formas_pago(texto, totales["valor_total"])

    json_factura = {
        "factura": buscar(r"No\.\s*(\d{3}-\d{3}-\d+)") or "FAC-XXXX-0000",
        "cliente": buscar(r"Razen Social.*?:\s*(.+)") or "Cliente Desconocido",
        "total": totales["valor_total"]
    }

    campos = {
        "empresaNombreComercial": buscar(r"\|\s*(\w+)"),
        "empresaRazonSocial": buscar(r"(DELI INTERNACIONAL S\.A\.)"),
        "empresaRuc": buscar(r"R\.U\.C\.\s*:\s*(\d{13})"),
        "empresaContribuyenteEspecial": buscar(r"Contribuyente Especial\s*(\d+)"),
        "empresaObligadoContabilidad": True,
        "empresaDireccionMatriz": buscar(r"Matriz:\s*(.+)"),
        "empresaDireccionSucursal": buscar(r"Sucursal:\s*(.+)"),
        "clienteNombre": json_factura["cliente"],
        "clienteIdentificacion": buscar(r"Identificacien\s*(\d+)"),
        "clienteCorreo": buscar(r"CORREO 1:\s*([\w\.-]+@[\w\.-]+)"),
        "numeroFactura": json_factura["factura"],
        "numeroAutorizacion": buscar(r"NUMERO DE AUTORIZACION\s*\n\s*(\d+)"),
        "claveAcceso": buscar(r"Sucursal:\s*CLAVE DE ACCESO\s*\n\s*(\d+)"),
        "fechaEmision": buscar(r"Fecha\s*(\d{2}/\d{2}/\d{4})"),
        "horaAutorizacion": buscar(r"AUTORIZACION:\s*(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})"),
        "ambiente": buscar(r"AMBIENTE:\s*(\w+)") or "PRODUCCION",
        "emision": buscar(r"EMISION:\s*(\w+)") or "NORMAL",
        "placaMatricula": buscar(r"Placa\s*/\s*Matricula:\s*(.+)"),
        "detalles": extraer_detalles(texto),
        "totales": totales,
        "formasPago": formas_pago,
        "jsonFactura": json_factura
    }

    logger.info("Campos extraídos desde OCR:")
    for k, v in campos.items():
        logger.info(f"{k}: {v}")

    return campos