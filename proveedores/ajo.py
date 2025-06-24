import pandas as pd
from io import StringIO
from connect_gemini import estructurar_con_prompt_especifico
import csv

def procesar(texto_ocr):
    # 🔧 Preprocesamiento: unir líneas cortadas en la tabla
    lineas = texto_ocr.split("\n")
    lineas_procesadas = []
    for i in range(len(lineas)):
        if i > 0 and not lineas[i].startswith("|") and lineas[i-1].startswith("|"):
            lineas_procesadas[-1] += " " + lineas[i].strip()
        else:
            lineas_procesadas.append(lineas[i])
    texto_ocr = "\n".join(lineas_procesadas)

    # 🧠 Prompt
    prompt = f"""
Tu rol es actuar como un operador de Data Entry para una empresa gastronómica. Vas a estructurar facturas como una tabla con las siguientes columnas:
Las columnas deben estar en el siguiente orden exacto:
"Fecha","Producto","Cantidad","Precio OCR","Total","Local","Proveedor"

❗ No incluyas la columna Precio. Esa será calculada luego.
⚠ No modifiques la información del OCR.
** Fecha: Es de las primeras líneas, luego de "Fecha de entrega:" en formato "xx/xx/xxxx".
** Producto: Corresponde a descripcion de cada producto, columna "Producto".
** Cantidad: Corresponde a los valores de la columna "Cantidad", la cual nos brinda información de cuantos kgs o unidades compramos. Ten en cuenta en este campo que, el proveedor indica de estas maneras: "1.0" para decir correctamente una unidad (1). No uses separador de miles, solo "," comas para separador de decimales.
** Ejemplo de valores en Cantidad que se presentarán en las facturas: "40.0", Correcta transformacion: "40,0". Ej: "1.0", Correcta transofrmación: "1,0".
** Ignora los valores de la columna "Unidad".
** Precio OCR: Corresponde a la columna "Precio" unitario. Ten en cuenta que, al igual que en cantidad, el proveedor puede indicarnos de manera: "81.704,32" para informarnos de, (manera que corresponde) 81704,32. Es importante que incluyas las comas "," en los decimales. No incluyas separador de miles.
** Total: Corresponde a la columna "Total". Ten en cuenta que, al igual que en cantidad, el proveedor puede indicarnos de manera: "81.704,32" para informarnos de, (manera que corresponde) 81704,32. Es importante que incluyas las comas "," en los decimales. No incluyas separador de miles.
📍 El Local será el primer texto de la factura antes del guión "-"
🧾 El proveedor será "Ajo".

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
        # 🔎 Validación previa de estructura con csv.reader
        filas_validas = []
        for linea in resultado_csv.strip().splitlines():
            reader = csv.reader([linea], delimiter=',', quotechar='"')
            for partes in reader:
                if len(partes) == 7:
                    filas_validas.append([p.strip() for p in partes])
                else:
                    print(f"⚠️ Fila descartada por estructura inválida: {linea}")

        if not filas_validas:
            print("❌ No hay filas válidas en el CSV generado.")
            return None

        df = pd.DataFrame(filas_validas, columns=["Fecha", "Producto", "Cantidad", "Precio OCR", "Total", "Local", "Proveedor"])

        # 🧼 Limpieza segura de números
        def limpiar_numero(valor):
            try:
                return float(str(valor).replace(".", "").replace(",", "."))
            except:
                return None

        df["Cantidad"] = df["Cantidad"].apply(limpiar_numero)
        df["Total"] = df["Total"].apply(limpiar_numero)
        df["Precio OCR"] = df["Precio OCR"].apply(limpiar_numero)

        df = df.dropna(subset=["Cantidad", "Total"])

        # 💰 Cálculos y controles
        df["Precio"] = (df["Total"] / df["Cantidad"]).round(2)
        df["Precio Check"] = df["Precio OCR"].round(2)
        df["Total Check"] = (df["Precio Check"] * df["Cantidad"]).round(2)
        df["Dif Precio"] = (df["Precio Check"] - df["Precio"]).round(2)
        df["Dif Total"] = (df["Total Check"] - df["Total"]).round(2)
        df["Q Check"] = (df["Total"] / df["Precio"]).round(2)
        df["Dif Q"] = (df["Q Check"] - df["Cantidad"]).round(2)

        def generar_alerta(row):
            if abs(row["Dif Precio"]) > 2:
                return "Diferencia de Precio"
            elif abs(row["Dif Total"]) > 2:
                return "Diferencia de Total"
            elif abs(row["Dif Q"]) > 0:
                return "Diferencia de Total"
            else:
                return "OK"

        df["Alerta"] = df.apply(generar_alerta, axis=1)

        columnas_finales = [
            "Fecha", "Producto", "Cantidad", "Precio", "Total", "Local", "Proveedor", "Alerta",
            "Precio Check", "Total Check", "Q Check"
        ]
        return df[columnas_finales]

    except Exception as e:
        print(f"❌ Error al procesar CSV en {__file__}: {e}")
        return None