import pandas as pd
from io import StringIO
from connect_gemini import estructurar_con_prompt_especifico

def procesar(texto_ocr):
    prompt = f"""
Tu rol es actuar como un operador de Data Entry para una empresa gastronómica. Vas a estructurar facturas como una tabla con las siguientes columnas:
Fecha, Producto, Cantidad, Total, Local, Proveedor

❗ No incluyas la columna Precio. Esa será calculada luego.
⚠ No modifiques la información del OCR.
** Fecha: Es de las primeras líneas, luego de "Fecha" en formato "xx/xx/xxxx".
** Producto: Corresponde a "Descripcion" de cada producto. (Recorta lo que diga "Oferta").
** Cantidad: Corresponde a los valores de la columna "CANT.1", la cual nos brinda información de cuantos kgs o unidades compramos. Ten en cuenta en este campo que, el proveedor indica de estas maneras: "50,00" para decir correctamente cincuenta unidades (50). O también puede indicarlo de manera "50.00" para decir correctamente cincuenta unidades (50). Es importante que incluyas las "," comas en los separadores decimales. No incluyas separador de miles.
** Cantidad: Siempre se encuentra después después del código. No confundas código (código que además de números contiene letras) con Cantidades que solo son números. Las cantidades son el segundo valor, ya que el primero es el código del proveedor, el cual no nos interesa.
** Total: Corresponde a la columna "Importe". Ten en cuenta que, al igual que en cantidad, el proveedor puede indicarnos de manera: "81.704,32" para informarnos de, (manera que corresponde) 81704,32. Es importante que incluyas las comas "," en los decimales. No incluyas separador de miles.
📍 El Local será el texto que sigue a la palabra "Sres.:" debes darme todo el campo hasta que aparezca un guión "-". Después del guión no debes traer nada.
🧾 El proveedor será "Blanca Luna".



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
