# Usa una imagen base de Python
FROM python:3.10-slim

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    gcc \
    krb5-config \
    libkrb5-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && apt-get clean

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el contenido de tu proyecto
COPY . .

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto de la app (si es necesario)
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
