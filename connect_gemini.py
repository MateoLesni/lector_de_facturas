from google.generativeai import configure, GenerativeModel

# Configurar API Key de Gemini
configure(api_key="AIzaSyD2Lb7u_x68AVNMskV_rrqjXl5mEwX1uH0")

# Modelo a utilizar
model = GenerativeModel("models/gemini-1.5-flash-latest")

# Función para estructurar con OCRIA
def estructurar_con_prompt_especifico(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error en estructurar_con_prompt_especifico(ocria): {e}")
        return ""

# Función para estructurar con IMGIA (imagen directa)
def estructurar_con_prompt_imgia(prompt, image):
    try:
        response = model.generate_content([prompt, image])
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error al generar contenido con Gemini: {e}")
        return None
    

def limpiar_csv_de_respuesta(texto):
    """
    Limpia delimitadores tipo ```csv y ``` de la respuesta de Gemini.
    Devuelve solo el contenido CSV limpio.
    """
    # Eliminar delimitadores de bloque de código si existen
    texto = texto.strip()
    if texto.startswith("```csv"):
        texto = texto[6:].lstrip()
    if texto.startswith("```"):
        texto = texto[3:].lstrip()
    if texto.endswith("```"):
        texto = texto[:-3].rstrip()
    return texto


import pandas as pd
from io import StringIO
import csv

def cargar_csv_imgia_en_linea(texto_csv_raw):
    """
    Convierte una cadena CSV sin saltos de línea (plana) en un DataFrame
    Espera que cada fila tenga exactamente 5 columnas.
    """
    # Eliminar delimitadores de bloque
    texto_csv_raw = texto_csv_raw.strip().replace("```csv", "").replace("```", "").strip()

    # Parsear todo el CSV en una lista plana
    reader = csv.reader([texto_csv_raw], delimiter=',', quotechar='"')
    datos_planos = next(reader)

    # Agrupar cada 5 columnas en una fila
    if len(datos_planos) % 5 != 0:
        raise ValueError(f"❌ Número de columnas inesperado: {len(datos_planos)}. Esperadas múltiplos de 5.")

    filas = [datos_planos[i:i+5] for i in range(0, len(datos_planos), 5)]

    df = pd.DataFrame(filas, columns=["Código Gem", "Producto Gem", "Cantidad Gem", "Precio Gem", "Total Gem"])
    return df



