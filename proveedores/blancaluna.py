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
Codigo, Producto, Cantidad, Precio OCR, Total, Local, Proveedor
Tenes determinadamente prohibido inventar información. Como última opción si no encontras un campo, pon 0. 
⚠ No modifiques la información del OCR.
** Codigo: Corresponde a "Codigo" del proveedor. Los códigos tienen estructura similar a:
8544AC
5001AC
5386AC
9570EN
3075CG
2028MC
4579LT
8078VN
4531LT
7735CR
8119LC
9010LC
1041UPUH
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
        df.columns = ["Codigo", "Producto", "Cantidad", "Precio OCR", "Total", "Local", "Proveedor"]

        # Limpieza de números con puntos de miles o comas decimales
        def limpiar_numero(valor):
            return float(str(valor).replace(".", "").replace(",", "."))

        df["Cantidad"] = df["Cantidad"].apply(limpiar_numero)
        df["Total"] = df["Total"].apply(limpiar_numero)

        # Cálculo del precio
        df["Precio OCR"] = df["Precio OCR"].apply(limpiar_numero)
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
                return "Diferencia de Q"
            else:
                return "OK"

        df["Alerta"] = df.apply(generar_alerta, axis=1)

        # Orden final de columnas
        columnas_finales = ["Codigo", "Producto", "Cantidad", "Precio", "Total", "Local", "Proveedor", "Alerta",
                            "Precio Check", "Total Check"]
        return df[columnas_finales]

    except Exception as e:
        print(f"❌ Error al procesar CSV en {__file__}: {e}")
        return None


def prompt_imgia(download_url):
    return f'''
Estás en rol de un Data Entry profesional. Vas a procesar la siguiente imagen de una factura gastronómica.
Tenes determinadamente prohibido inventar información. Como última opción si no encontras un campo, pon 0. 


🔗 Enlace a la imagen: {download_url}
Extraé la siguiente información y devolvela en formato CSV:
Respeta estas 5 columnas, siempre deben ser las mismas. La información está en la factura, no hay información faltante.
No agregues columnas ni quites. Deben ser estas 4.
Columnas:
- "Código Gem" usar el "Código" del proveedor para cada artículo. Los códigos pueden variar, pero generalmente tienen un formato así: F00098, F00516, A00645, A00801, G00498.
- "Producto Gem"  usar "Descripción"
- "Cantidad Gem" → usar "Cant.1". Ignora el valor que esté en "Cant.2". Es decir, por lo general esel número posterior al 
código. No pongas el valor de "Cant.2", ese no nos interesa.
- "Precio Gem" usar "Precio"
- "Total Gem" usar "Importe"

No agregues ninguna palabra, ningún texto ni carácter antes ni después del CSV. Solo quiero la tabla limpia con los datos correctos para que no se rompan los procesos posteriores.

📌 Instrucciones:
- No pongas texto fuera del CSV.
- Si no hay un campo, dejar en blanco ("").
- Usá comillas dobles en todos los valores.
- Sin encabezado.
- Separador de columnas: coma.
- No uses separadores de miles.
- Una línea por producto.

Una devolución correcta es exactamente así (Ejemplo):
"Barritas de submarino Aguila Caja (24 x 14 gr)","1","14946,31","14946,31"
"Queso Crema Milka ut Balde x 3.6 Kg","2","40698,53","81397,05"
"Rebozador Preferido Bolsa x 5 Kg","1","8961,05","8961,05"

Imagen: {download_url}
'''
