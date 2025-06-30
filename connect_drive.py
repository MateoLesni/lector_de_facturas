import os
import importlib
import pandas as pd
from io import StringIO, BytesIO
from document_ai import traer_texto_png
from connect_gemini import estructurar_con_prompt_especifico, estructurar_con_prompt_imgia
from google.oauth2 import service_account
from googleapiclient.discovery import build
from openpyxl import load_workbook
from PIL import Image
import requests

# Configuración de acceso a Google Drive
SERVICE_ACCOUNT_FILE = 'credentials/credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
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
        for _, fila in df_resultado.iterrows():
            hoja.append(fila.tolist())
        libro.save(ruta_archivo)
        print(f"\n✅ Datos agregados correctamente en '{ruta_archivo}'")
    except Exception as e:
        print(f"\n❌ Error al escribir en '{ruta_archivo}': {e}")

def obtener_imagen_desde_drive(file_id):
    url = f"https://drive.google.com/uc?id={file_id}&export=download"
    response = requests.get(url)
    response.raise_for_status()
    return Image.open(BytesIO(response.content))

def alinear_y_combinar(df_ocr, df_img_raw):
    """
    Si OCRIA devuelve una sola fila y Gemini varias, se permite expandir.
    En otros casos, Gemini no puede agregar filas.
    """
    # Alinear longitud si OCRIA tiene solo una fila
    if len(df_ocr) == 1 and len(df_img_raw) > 1:
        df_ocr = pd.DataFrame([[""] * df_ocr.shape[1]] * len(df_img_raw), columns=df_ocr.columns)
    elif len(df_ocr) != len(df_img_raw):
        df_img_raw = df_img_raw.reindex(range(len(df_ocr))).fillna("")

    df_final = pd.concat([df_ocr.reset_index(drop=True), df_img_raw.reset_index(drop=True)], axis=1)
    return df_final


def main():
    folder_id = '1YCEgOfDfyD9levr4_ouoXpxy0l0n5QXH'
    imagenes = listar_imagenes(folder_id)
    resultados_df = []

    for img in imagenes:
        nombre_archivo = img['name'].lower()
        file_id = img['id']

        for archivo in os.listdir("proveedores"):
            if archivo.endswith(".py") and archivo != "__init__.py":
                proveedor = archivo[:-3].lower()
                if proveedor in nombre_archivo:
                    print(f"\n📄 Procesando imagen: {img['name']} con proveedor: {proveedor}")
                    texto = traer_texto_png(file_id)

                    if texto:
                        print("📤 Texto OCR Mistral:")
                        print(texto)

                        try:
                            modulo = importlib.import_module(f'proveedores.{proveedor}')
                            df_ocr = modulo.procesar(texto)

                            if df_ocr is None:
                                print(f"❌ No se pudo procesar OCRIA para proveedor '{proveedor}'")
                                continue

                            print("\n✅ Resultado estructurado OCRIA:")
                            print(df_ocr)

                            download_url = f"https://drive.google.com/uc?id={file_id}&export=download"
                            prompt_img = modulo.prompt_imgia(download_url)
                            imagen_pil = obtener_imagen_desde_drive(file_id)
                            resultado_img = estructurar_con_prompt_imgia(prompt_img, imagen_pil)

                            columnas_img = ["Código Gem", "Producto Gem", "Cantidad Gem", "Precio Gem", "Total Gem"]
                            df_img_raw = pd.DataFrame(columns=columnas_img)

                            if resultado_img:
                                print("\n📥 Resultado crudo de IMGIA:")
                                print(resultado_img)
                                try:
                                    df_img_raw = pd.read_csv(StringIO(resultado_img), header=None)
                                    if df_img_raw.shape[1] == 5:
                                        df_img_raw.columns = columnas_img

                                        for col, func_name in [
                                            ("Cantidad Gem", "limpiar_cantidad"),
                                            ("Precio Gem", "limpiar_numero"),
                                            ("Total Gem", "limpiar_numero")
                                        ]:
                                            try:
                                                func = getattr(modulo, func_name)
                                                df_img_raw[col] = df_img_raw[col].apply(func)
                                            except AttributeError:
                                                print(f"⚠️ {func_name} no está definido en el módulo del proveedor '{proveedor}'. Se dejan valores originales.")
                                            except Exception as e:
                                                print(f"⚠️ Error aplicando {func_name} para '{proveedor}': {e}. Se dejan valores originales.")
                                    else:
                                        print(f"❌ IMGIA devolvió un formato inesperado: {df_img_raw.shape[1]} columnas")
                                        df_img_raw = pd.DataFrame(columns=columnas_img)
                                except Exception as e:
                                    print(f"❌ Error al convertir resultado IMGIA en DataFrame: {e}")
                                    df_img_raw = pd.DataFrame(columns=columnas_img)

                            # Alinear y combinar según nueva lógica
                            df_final = alinear_y_combinar(df_ocr, df_img_raw)

                            if pd.Series(df_final.columns).duplicated().any():
                                df_final.columns = [
                                    f"{col}_{i}" if pd.Series(df_final.columns).duplicated()[j] else col
                                    for j, (i, col) in enumerate(zip(range(len(df_final.columns)), df_final.columns))
                                ]
                                print("⚠️ Columnas duplicadas detectadas. Fueron renombradas.")

                            resultados_df.append(df_final)
                            print(f"✅ Resultado final para {proveedor}:")
                            print(df_final)

                        except Exception as e:
                            print(f"❌ Error procesando proveedor '{proveedor}': {e}")
                    else:
                        print("❌ No se pudo extraer texto con Mistral OCR.")
                    break
        else:
            print(f"❌ No se encontró proveedor coincidente para: {nombre_archivo}")

    if resultados_df:
        df_total = pd.concat(resultados_df, ignore_index=True)
        escribir_en_bd_local(df_total)
    else:
        print("⚠️ No se generaron resultados para guardar.")

if __name__ == "__main__":
    main()
