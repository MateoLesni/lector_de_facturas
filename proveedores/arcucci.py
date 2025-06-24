import pandas as pd
import re
from io import StringIO
from connect_gemini import estructurar_con_prompt_especifico

def limpiar_numero(valor):
    s = str(valor).strip().replace('"', '')

    # Si ya es un número con punto decimal, simplemente parsealo
    if re.fullmatch(r"\d+\.\d+", s):
        return round(float(s), 2)

    # Si tiene coma como decimal, reemplazar por punto y parsear
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
        return round(float(s), 2)

    # Si es entero sin separador decimal, asumir que los últimos 2 dígitos son decimales
    if re.fullmatch(r"\d+", s):
        if len(s) <= 2:
            return round(float("0." + s.zfill(2)), 2)
        return round(float(s[:-2] + "." + s[-2:]), 2)

    raise ValueError(f"Formato numérico inesperado: '{valor}'")


def procesar(texto_ocr):
    prompt = f"""
Tu rol es actuar como un operador de Data Entry para una empresa gastronómica. Vas a estructurar facturas como una tabla con las siguientes columnas:
Fecha, Producto, Cantidad, Precio OCR, Total, Local, Proveedor.
Importante, el CSV siempre tiene que tener 7 columnas.
- No generes líneas en blanco entre productos.
- No agregues ningún texto ni antes ni después del csv. Solo debes devolver el CSV limpio.
- Todas las líneas deben tener exactamente 7 valores, uno por campo.
- No uses saltos de línea dentro de una celda.
- Asegurate de que todas las líneas tengan comillas dobles y estén separadas por coma.

❗ No incluyas la columna Precio calculado. Esa se calculará luego en Python.
⚠ No modifiques la información del OCR.
🧾 El proveedor será "ARCUCCI".
** Producto: Es la descripción del producto, en este proveedor compramos generalmente artículos de limpieza y packagine, entre otros. No confundas este campo "Producto" con el código del proveedor, código cual por ahora no nos interesa.
Tenes prohibido inventar, redondear cualquier numero o información. Solo podes organizar la extracción del OCR basado en las siguientes reglas:
📍 El Local será el texto que sigue a la palabra "SEÑOR/ES".
    ** ¡¡ MUY IMPORTANTE, CAMPO 'CANTIDAD'!!:
        ** Las cantidades el OCR las proporciona de la siguiente manera: "10,00" (corresponde a diez unidades, (10.0)). No confundas estos campos.
        ** Debes poner las cantidades tal cual te las da el OCR, solo cambia la "," por el ".". 
        ** Reglas campo "Cantidad":
        ** Importante: El campo "Cantidad", siempre lo encontrarás posterior a la descripción.
        ** Es decir, cuando termina la descripción de un producto, el próximo número con el siguiente formato: "3,00" será la cantidad facturada del producto.
        ** El campo Cantidad es el más importante y en el que no se puede fallar.
        ** El OCR brinda un campo "CTD ITEMS:" el cual tiene el total de Cantidades facturadas. Las cantidades que pongas tienen que ser las que sigan las instrucciones, y deben coincidir con ese total.
❗ ATENCIÓN: Si una celda contiene comillas dobles dentro del texto (por ejemplo `"SEIQ"`), debés ESCAPARLAS correctamente usando doble comilla ("").
❗ Todos los números decimales deben estar escritos con punto como separador decimal y sin comas de miles.

**Formato CSV válido:**
- Todos los campos entre comillas dobles (").
- Separados por coma.
- Una línea por producto.
- Repetí la fecha si aparece solo una vez.
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
        expected_cols = 7

        if df.shape[1] != expected_cols:
            print(f"⚠️ CSV malformado: se esperaban {expected_cols} columnas, pero se encontraron {df.shape[1]}")
            print("🔎 Resultado CSV devuelto por Gemini:\n", resultado_csv)
            return None

        df.columns = ["Fecha", "Producto", "Cantidad", "Precio OCR", "Total", "Local", "Proveedor"]

        # Limpieza numérica inteligente
        df["Cantidad"] = df["Cantidad"].apply(limpiar_numero)
        df["Precio OCR"] = df["Precio OCR"].apply(limpiar_numero)
        df["Total"] = df["Total"].apply(limpiar_numero)

        # Cálculo del precio real = Total / Cantidad
        df["Precio"] = (df["Total"] / df["Cantidad"]).round(2)

        # Precio Check = Precio OCR * 0.9
        df["Precio Check"] = (df["Precio OCR"] * 0.9).round(2)

        # Total Check = Precio Check * Cantidad
        df["Total Check"] = (df["Precio Check"] * df["Cantidad"]).round(2)

        # Diferencias
        df["Dif Precio"] = (df["Precio Check"] - df["Precio"]).round(2)
        df["Dif Total"] = (df["Total Check"] - df["Total"]).round(2)

        # Alerta
        def generar_alerta(row):
            if abs(row["Dif Precio"]) > 2:
                return "Diferencia de Precio"
            elif abs(row["Dif Total"]) > 2:
                return "Diferencia de Total"
            else:
                return "OK"

        df["Alerta"] = df.apply(generar_alerta, axis=1)

        # Orden final de columnas
        columnas_finales = [
            "Fecha", "Producto", "Cantidad", "Precio", 
            "Total", "Local", "Proveedor", "Alerta", "Precio Check", "Total Check"
        ]
        return df[columnas_finales]

    except Exception as e:
        print(f"❌ Error al procesar CSV en {__file__}: {e}")
        return None
