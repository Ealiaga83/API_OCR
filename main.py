from fastapi import FastAPI, File, UploadFile
from pathlib import Path
from ocr.processor import ocr_pdf, extraer_datos_factura, guardar_texto_ocr, extract_text_pdfplumber
from utils.logger_config import logger
from utils.endpointExterno import enviar_registro
import json

app = FastAPI()
POPPLER_PATH = r"C:\poppler\bin"

@app.post("/factura/")
async def procesar_factura(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    content = await file.read()

    if ext != ".pdf":
        logger.warning(f"Formato no soportado: {ext}")
        return {"error": f"Formato {ext} no soportado."}

    # OCR del PDF y guardado del texto en output/
    nombre_txt = file.filename.replace(".pdf", ".txt")
    texto = extract_text_pdfplumber(content)
    guardar_texto_ocr(texto, nombre_archivo=nombre_txt)

    logger.info(f"\nTexto extraído del PDF:\n{'-'*40}\n{texto}\n{'-'*40}")

    # Extracción de datos desde el texto OCR
    datos = extraer_datos_factura(texto)

    # Validación de campos faltantes
    campos_faltantes = [k for k, v in datos.items() if v in [None, [], {}, ""] and k not in ["formasPago", "jsonFactura"]]
    if campos_faltantes:
        logger.warning(f"⚠️ Campos faltantes en OCR: {campos_faltantes}")

    # Valores clave con respaldo
    factura_id = datos.get("numeroFactura") or "FAC-XXXX-0000"
    cliente = datos.get("clienteNombre") or "Cliente Desconocido"
    total = float(datos.get("totales", {}).get("valor_total") or 0.00)

    # Construcción del payload (sin json.dumps en objetos)
    payload = {
        "empresaNombreComercial": datos.get("empresaNombreComercial") or "No encontrado",
        "empresaRazonSocial": datos.get("empresaRazonSocial") or "No encontrado",
        "empresaRuc": datos.get("empresaRuc") or "No encontrado",
        "empresaContribuyenteEspecial": datos.get("empresaContribuyenteEspecial") or "No encontrado",
        "empresaObligadoContabilidad": True,
        "empresaDireccionMatriz": datos.get("empresaDireccionMatriz") or "No encontrado",
        "empresaDireccionSucursal": datos.get("empresaDireccionSucursal") or "No encontrado",
        "clienteNombre": cliente,
        "clienteIdentificacion": datos.get("clienteIdentificacion") or "No encontrado",
        "clienteCorreo": datos.get("clienteCorreo") or "No encontrado",
        "numeroFactura": factura_id,
        "numeroAutorizacion": datos.get("numeroAutorizacion") or "No encontrado",
        "claveAcceso": datos.get("claveAcceso") or "No encontrado",
        "fechaEmision": datos.get("fechaEmision") or "No encontrado",
        "horaAutorizacion": datos.get("horaAutorizacion") or "No encontrado",
        "ambiente": datos.get("ambiente") or "No encontrado",
        "emision": datos.get("emision") or "No encontrado",
        "placaMatricula": datos.get("placaMatricula") or "No encontrado",
        "factura": factura_id,
        "detalles": datos.get("detalles", []),
        "totales": datos.get("totales", {}),
        "formasPago": datos.get("formasPago", []),
        "jsonFactura": datos.get("jsonFactura", {
            "factura": factura_id,
            "cliente": cliente,
            "total": total
        })
    }

    logger.info(f"\n📦 Payload construido:\n{json.dumps(payload, indent=2)}")

    # Envío al endpoint externo
    resultado_registro = enviar_registro(payload)

    return {
        "filename": file.filename,
        "payload": payload,
        "registro": resultado_registro
    }