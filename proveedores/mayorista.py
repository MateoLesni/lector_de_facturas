import pandas as pd
from io import StringIO
from connect_gemini import estructurar_con_prompt_especifico

def limpiar_cantidad(valor):
    val = str(valor).strip()
    if val == "" or pd.isna(val):
        return 0.0

    # Reemplazar "," por "." y remover espacios
    val = val.replace(",", ".").replace(" ", "")

    # Si hay más de un ".", dejar solo el último como separador decimal
    if val.count(".") > 1:
        partes = val.split(".")
        val = "".join(partes[:-1]) + "." + partes[-1]

    try:
        return float(val)
    except:
        return 0.0

def limpiar_numero(valor):
    if pd.isna(valor):
        return 0.0

    val = str(valor).strip().lower()

    if val in ["oferta", ""]:
        return 0.0

    # Reemplazar "," por "." y remover espacios
    val = val.replace(",", ".").replace(" ", "")

    # Si hay más de un ".", dejar solo el último como separador decimal
    if val.count(".") > 1:
        partes = val.split(".")
        val = "".join(partes[:-1]) + "." + partes[-1]

    try:
        return float(val)
    except:
        return 0.0

def procesar(texto_ocr):
    prompt = f"""
Tu rol es actuar como un operador de Data Entry para una empresa gastronómica. Vas a estructurar facturas como una tabla con las siguientes columnas:
Obligatoriamente las columnas que debes devolver son estas:
Fecha, Producto, Cantidad, Precio OCR, Total, Local, Proveedor

❗ No incluyas la columna Precio. Esa será calculada luego.
Tenes prohibido redondear, inventar o agregar información. Solo estructuras la información brindada por el OCR.
⚠ No modifiques la información del OCR.
** Código: Devuelve el código de cada artículo. Los códigos pueden variar, pero generalmente tienen un formato así: F00098, F00516, A00645, A00801, G00498.
** Producto: Corresponde a "Descripción" de cada producto.
** Cantidad: Corresponde a los valores de la columna "CANT.Uni". Sólo en caso de, en la misma línea, exista un valor en "Cant.KG", dejarás solamente el valor de "Cant.KG".
** Ambos campos de cantidad están posterior a la descripción. Si no hay de una, hay de la otra y pueden haber ambas. Si hay ambas, tiene prioridad la de "Cant.KG", recuerda.
** Precio OCR: El precio de un producto jamás puede ser igual a 0, 21,00 o 10,5. Debes buscar bien en el texto, ignora las campos vacíos y extrae el precio correcto del producto.
** Total: Corresponde a la columna "Total". Si es un producto "Oferta", pon en "Total" la palabra "Oferta". En caso que no sea un producto Oferta, el valor nunca puede ser 21, 10,5. Esos son impuestos, no te confundas. Si no conseguís extraer el total, escribí "Oferta" para identificar el error.
** Total: Los totales están en formato "30.772.55" que, correctamente estaríamos hablando de treinta mil setecientos setenta y dos con 55 centavos. Seguí esta lógica con todos los totales.
📍 El Local será el texto que sigue a la palabra "Señor(es):"
🧾 El proveedor será "Mayorista Net".

‼️ Siempre devolvé las 7 columnas mencionadas, incluso si algún campo está vacío. No omitas columnas. Usá "" para celdas vacías.

**Formato CSV válido:**
- Siempre 7 columnas: "Código","Producto","Cantidad","Precio OCR","Total","Local","Proveedor"
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

    resultado_csv = resultado_csv.replace('", "', '","')  # limpieza básica

    try:
        df = pd.read_csv(StringIO(resultado_csv), header=None)
        columnas = ["Fecha", "Producto", "Cantidad", "Precio OCR", "Total", "Local", "Proveedor"]
        if df.shape[1] != len(columnas):
            print("📄 Resultado bruto devuelto por Gemini:")
            print(resultado_csv)
            raise ValueError(f"Formato inesperado: se esperaban {len(columnas)} columnas, pero se recibieron {df.shape[1]}.")
        df.columns = columnas

        df["Cantidad"] = df["Cantidad"].apply(limpiar_cantidad)
        df["Precio OCR"] = df["Precio OCR"].apply(limpiar_numero)

        es_oferta = df["Total"].astype(str).str.lower().str.strip() == "oferta"
        df.loc[~es_oferta, "Total"] = df.loc[~es_oferta, "Total"].apply(limpiar_numero)
        df.loc[es_oferta, "Total"] = (df["Cantidad"] * df["Precio OCR"]).round(2)

        df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0.0)
        df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0.0)
        df["Precio"] = (df["Total"] / df["Cantidad"]).round(2).replace([float("inf"), -float("inf")], 0.0)

        # Controles cruzados
        df["Precio Check"] = df["Precio OCR"].round(2)
        df["Total Check"] = (df["Precio Check"] * df["Cantidad"]).round(2)
        df["Q Check"] = (df["Total"] / df["Precio"]).round(2)

        df["Dif Precio"] = (df["Precio Check"] - df["Precio"]).round(2)
        df["Dif Total"] = (df["Total Check"] - df["Total"]).round(2)
        df["Dif Q"] = (df["Q Check"] - df["Cantidad"]).round(2)

        def generar_alerta(row):
            if abs(row["Dif Precio"]) > 2:
                return "Diferencia de Precio"
            elif abs(row["Dif Total"]) > 2:
                return "Diferencia de Total"
            elif abs(row["Dif Q"]) > 0:
                return "Diferencia de Q"
            return "OK"

        df["Alerta"] = df.apply(generar_alerta, axis=1)

        columnas_finales = [
            "Fecha", "Producto", "Cantidad", "Precio", "Total", "Local", "Proveedor",
            "Alerta", "Precio Check", "Total Check", "Q Check"
        ]
        return df[columnas_finales]

    except Exception as e:
        print(f"❌ Error al procesar CSV en {__file__}: {e}")
        return None

def prompt_imgia(download_url):
    return f'''
Estás en rol de un Data Entry profesional. Vas a procesar la siguiente imagen de una factura gastronómica.

🔗 Enlace a la imagen: {download_url}
Extraé la siguiente información y devolvela en formato CSV:
Respeta estas 5 columnas, siempre deben ser las mismas. La información está en la factura, no hay información faltante.
No agregues columnas ni quites. Deben ser estas 4.
Columnas:
- "Código Gem" usar el "Código" del proveedor para cada artículo. Los códigos pueden variar, pero generalmente tienen un formato así: F00098, F00516, A00645, A00801, G00498.
- "Producto Gem"  usar "Descripción"
- "Cantidad Gem" → usar "Cant.Kg" si está, si no "Cant.Uni". Es decir, siempre trae con prioridad "Cant.Kg", si ese campo está vacío, traes "Cant.Uni"
- "Precio Gem" usar "Precio Unit"
- "Total Gem" usar "Total"

No agregues ninguna palabra, ningún texto ni carácter antes ni después del CSV. Solo quiero la tabla limpia con los datos correctos para que no se rompan los procesos posteriores.

📌 Instrucciones:
- No pongas texto fuera del CSV.
- Si no hay un campo, dejar en blanco ("").
- Usá comillas dobles en todos los valores.
- Sin encabezado.
- Separador de columnas: coma.
- Repetí la fecha en todas las líneas.
- No uses separadores de miles.
- Una línea por producto.

Una devolución correcta es exactamente así (Ejemplo):
"Barritas de submarino Aguila Caja (24 x 14 gr)","1","14946,31","14946,31"
"Queso Crema Milka ut Balde x 3.6 Kg","2","40698,53","81397,05"
"Rebozador Preferido Bolsa x 5 Kg","1","8961,05","8961,05"

Imagen: {download_url}
'''
