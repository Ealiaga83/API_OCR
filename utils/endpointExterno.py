from fastapi import APIRouter, Request
import httpx
import json
import os
from dotenv import load_dotenv
from utils.logger_config import logger

# Cargar variables de entorno desde .env
load_dotenv()

router = APIRouter()

# Variables de entorno
AUTH_URL = os.getenv("AUTH_URL")
REGISTRO_URL = os.getenv("REGISTRO_URL")
USUARIO = os.getenv("USUARIO")
CLAVE = os.getenv("CLAVE")

def obtener_token():
    payload = {
        "usuario": USUARIO,
        "clave": CLAVE
    }

    try:
        response = httpx.post(AUTH_URL, json=payload)
        response.raise_for_status()
        token = response.json().get("token")
        logger.info(f"🔐 Token obtenido correctamente: {token}")
        return token
    except Exception as e:
        logger.error(f"[ERROR] No se pudo obtener el token: {e}")
        return None

def enviar_registro(payload: dict):
    token = obtener_token()
    if not token:
        return {"error": "No se pudo obtener token"}

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 🔁 Conversión controlada de campos a string JSON
    payload_convertido = payload.copy()
    for campo in ["detalles", "totales", "formasPago", "jsonFactura"]:
        valor = payload_convertido.get(campo)
        if isinstance(valor, (dict, list)):
            payload_convertido[campo] = json.dumps(valor, ensure_ascii=False)
        elif isinstance(valor, str):
            try:
                json.loads(valor)
            except json.JSONDecodeError:
                logger.warning(f"[WARN] El campo '{campo}' parece ser string pero no es JSON válido. Se asigna '{{}}' por seguridad.")
                payload_convertido[campo] = json.dumps({}, ensure_ascii=False) if campo != "detalles" else json.dumps([], ensure_ascii=False)

    try:
        response = httpx.post(REGISTRO_URL, json=payload_convertido, headers=headers)
        response.raise_for_status()
        contenido = response.text.strip()

        if contenido:
            try:
                resultado = json.loads(contenido)
                logger.info(f"✅ Registro insertado correctamente: {resultado}")
                return resultado
            except json.JSONDecodeError:
                logger.warning(f"⚠️ El servidor respondió con texto no JSON:\n{contenido}")
                return {"mensaje": "Registro exitoso pero la respuesta no es JSON", "respuesta": contenido}
        else:
            logger.warning("⚠️ El servidor respondió sin contenido.")
            return {"mensaje": "Registro exitoso pero sin respuesta JSON"}
    except httpx.HTTPStatusError as e:
        logger.error(f"[ERROR] Falló la inserción del registro: {e.response.text}")
        return {"error": e.response.text}
    except Exception as e:
        logger.error(f"[ERROR] Error inesperado: {e}")
        return {"error": str(e)}

@router.post("/registrar/")
async def registrar(request: Request):
    try:
        payload = await request.json()
        logger.info(f"📨 Payload recibido para registro:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
    except Exception as e:
        logger.error(f"[ERROR] No se pudo leer el payload: {e}")
        return {"error": "Payload inválido"}

    return enviar_registro(payload)