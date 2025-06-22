import os
import importlib
import pandas as pd
from document_ai import traer_texto_png
from google.oauth2 import service_account
from googleapiclient.discovery import build
from openpyxl import load_workbook

SERVICE_ACCOUNT_FILE = 'credentials/credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

def listar_imagenes(folder_id):
    query = f"'{folder_id}' in parents and trashed = false"
    resultados = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    return [f for f in resultados.get('files', []) if f['mimeType'].startswith('image/')]

def escribir_en_bd_local(df_resultado):
    ruta_archivo = "C:/Users/gesti/Desktop/extractor_de_facturas_v6/BD extracciones.xlsx"
    
    try:
        libro = load_workbook(ruta_archivo)
        hoja = libro.active
        fila_inicial = hoja.max_row + 1

        for _, fila in df_resultado.iterrows():
            hoja.append(fila.tolist())

        libro.save(ruta_archivo)
        print(f"✅ Datos agregados correctamente en '{ruta_archivo}'")
    except Exception as e:
        print(f"❌ Error al escribir en '{ruta_archivo}': {e}")

def main():
    folder_id = '1YCEgOfDfyD9levr4_ouoXpxy0l0n5QXH'
    imagenes = listar_imagenes(folder_id)

    resultados_df = []

    for img in imagenes:
        nombre_archivo = img['name'].lower()
        file_id = img['id']

        for archivo in os.listdir("proveedores"):
            if archivo.endswith(".py") and archivo != "__init__.py":
                proveedor = archivo[:-3]
                if proveedor in nombre_archivo:
                    print(f"📄 Procesando imagen: {img['name']} con proveedor: {proveedor}")
                    texto = traer_texto_png(file_id)
                    if texto:
                        try:
                            modulo = importlib.import_module(f'proveedores.{proveedor}')
                            resultado_csv = modulo.procesar(texto)

                            print(f"Texto extraído por OCR: {texto}")

                            if resultado_csv is not None:
                                resultados_df.append(resultado_csv)
                                print(f"\n✅ Resultado para {proveedor}:\n{resultado_csv}\n")
                            else:
                                print(f"⚠️ No se pudo estructurar el resultado para {proveedor}")
                        except ModuleNotFoundError:
                            print(f"⚠️ No hay módulo para el proveedor '{proveedor}'")
                    else:
                        print("❌ No se pudo extraer texto con Mistral OCR.")
                    break
        else:
            print(f"❌ No se encontró proveedor coincidente para: {nombre_archivo}")

    if resultados_df:
        df_final = pd.concat(resultados_df, ignore_index=True)
        escribir_en_bd_local(df_final)
    else:
        print("⚠️ No se generaron resultados para guardar.")

if __name__ == "__main__":
    main()
