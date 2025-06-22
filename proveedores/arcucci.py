import pandas as pd
from io import StringIO
from connect_gemini import estructurar_con_prompt_especifico

def procesar(texto_ocr):
    prompt = f"""
Tu rol es actuar como un operador de Data Entry para una empresa gastronómica. Vas a estructurar facturas como una tabla con las siguientes columnas:
Fecha, Producto, Cantidad, Total, Local, Proveedor

❗ No incluyas la columna Precio. Esa será calculada luego.
⚠ No modifiques la información del OCR.
🧾 El proveedor será "MOOP".
📍 El Local será el texto que sigue a la palabra "SEÑOR/ES".

**Formato CSV válido:**
- Todos los campos entre comillas dobles (").
- Separados por coma.
- Una línea por producto.
- Repetí la fecha si aparece solo una vez.
- No uses separadores de miles.
- Sin encabezado.

Texto OCR:
\"\"\"{texto_ocr}\"\"\"
"""
    resultado_csv = estructurar_con_prompt_especifico(prompt)

    if not resultado_csv or resultado_csv.strip() == "":
        print("⚠️ Gemini no devolvió datos útiles.")
        return None

    try:
        df = pd.read_csv(StringIO(resultado_csv), header=None)
        df.columns = ["Fecha", "Producto", "Cantidad", "Total", "Local", "Proveedor"]

        # Limpieza de números con puntos de miles o comas decimales
        def limpiar_numero(valor):
            return float(str(valor).replace(".", "").replace(",", "."))

        df["Cantidad"] = df["Cantidad"].apply(limpiar_numero)
        df["Total"] = df["Total"].apply(limpiar_numero)

        # Cálculo del precio
        df["Precio"] = (df["Total"] / df["Cantidad"]).round(2)

        # Orden final de columnas
        columnas_finales = ["Fecha", "Producto", "Cantidad", "Precio", "Total", "Local", "Proveedor"]
        return df[columnas_finales]

    except Exception as e:
        print(f"❌ Error al procesar CSV en {__file__}: {e}")
        return None
