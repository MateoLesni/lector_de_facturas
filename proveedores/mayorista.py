import pandas as pd
from io import StringIO
from connect_gemini import estructurar_con_prompt_especifico

def procesar(texto_ocr):
    prompt = f"""
Tu rol es actuar como un operador de Data Entry para una empresa gastronómica. Vas a estructurar facturas como una tabla con las siguientes columnas:
Obligatoriamente las columnas que debes devolver son estas:
Fecha, Producto, Cantidad, Precio OCR, Total, Local, Proveedor

❗ No incluyas la columna Precio. Esa será calculada luego.
Tenes prohibido redondear, inventar o agregar información. Solo estructuras la información brindada por el OCR.
⚠ No modifiques la información del OCR.
** Fecha: Es de las primeras líneas, luego de "Fecha" en formato "xx/xx/xxxx".
** Producto: Corresponde a "Descripción" de cada producto.
** Cantidad: Corresponde a los valores de la columna "CANT.Uni". Sólo en caso de, en la misma línea, exista un valor en "Cant.KG", dejarás solamente el valor de "Cant.KG".
** Total: Corresponde a la columna "Total". Si es un producto "Oferta", pon en "Total" la palabra "Oferta".
📍 El Local será el texto que sigue a la palabra "Señor(es):"
🧾 El proveedor será "Mayorista Net".

‼️ Siempre devolvé las 7 columnas mencionadas, incluso si algún campo está vacío. No omitas columnas. Usá "" para celdas vacías.

**Formato CSV válido:**
- Siempre 7 columnas: "Fecha","Producto","Cantidad","Precio OCR","Total","Local","Proveedor"
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

    resultado_csv = resultado_csv.replace('", "', '","')  # limpiar espacios que rompen el CSV

    try:
        df = pd.read_csv(StringIO(resultado_csv), header=None)

        columnas = ["Fecha", "Producto", "Cantidad", "Precio OCR", "Total", "Local", "Proveedor"]
        if df.shape[1] != len(columnas):
            print("📄 Resultado bruto devuelto por Gemini:")
            print(resultado_csv)
            raise ValueError(f"Formato inesperado: se esperaban {len(columnas)} columnas, pero se recibieron {df.shape[1]}.")

        df.columns = columnas

        def limpiar_numero(valor):
            if pd.isna(valor):
                return 0.0
            valor = str(valor).strip()
            if valor.lower() == "oferta" or valor == "":
                return 0.0
            valor = valor.replace(".", "").replace(",", ".")
            try:
                return float(valor)
            except ValueError:
                return 0.0

        # Aplicar limpieza a Precio OCR y Cantidad
        df["Cantidad"] = df["Cantidad"].apply(limpiar_numero)
        df["Precio OCR"] = df["Precio OCR"].apply(limpiar_numero)

        # Detectar filas con "Oferta"
        es_oferta = df["Total"].astype(str).str.lower().str.strip() == "oferta"

        # Limpiar Total solo si no es 'Oferta'
        df.loc[~es_oferta, "Total"] = df.loc[~es_oferta, "Total"].apply(limpiar_numero)

        # Calcular Total en productos con 'Oferta'
        df.loc[es_oferta, "Total"] = (df.loc[es_oferta, "Precio OCR"] * df.loc[es_oferta, "Cantidad"]).round(2)

        # Forzar tipos numéricos para evitar errores de dtype
        df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0.0)
        df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0.0)

        # Calcular Precio
        df["Precio"] = (df["Total"] / df["Cantidad"]).round(2)
        df["Precio"] = df["Precio"].replace([float("inf"), -float("inf")], 0.0).fillna(0.0)

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
                return "Diferencia de Q"
            else:
                return "OK"

        df["Alerta"] = df.apply(generar_alerta, axis=1)
        # Orden final de columnas
        columnas_finales = ["Fecha", "Producto", "Cantidad", "Precio", "Total", "Local", "Proveedor", "Alerta",
                            "Precio Check", "Total Check", "Q Check"]
        return df[columnas_finales]

    except Exception as e:
        print(f"❌ Error al procesar CSV en {__file__}: {e}")
        return None
