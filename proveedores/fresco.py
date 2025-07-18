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
Respeta siempre estas 7 columnas.
Tenes determinadamente prohibido inventar información. Como última opción si no encontras un campo, pon 0. 
⚠ No modifiques la información del OCR.
** Codigo: Corresponde a "Articulo" (segunda columna) de cada producto.
** Producto: Corresponde a los valores de la columna "Cantidad". Solo las cantidades. Es la primer columna.
** Cantidad: Corresponde a los valores de la columna "Descripción".
** Precio OCR: Corresponde a la columna "Precio unit.". Copia el número tal cual te lo brinda el OCR.
** Total: Corresponde a la columna "Importe". Copia el número tal cual te lo brinda el OCR.
📍 El Local será el texto que sigue a la palabra "Nombre de fantasia:" ignora los numeros.
🧾 El proveedor será "Fresco Pez S.A".



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
        def normalizar_numero(valor):
            try:
                val = str(valor).strip()
                if not val:
                    return 0.0

                # Encontrar última coma o punto en la cadena original
                last_comma = val.rfind(",")
                last_dot = val.rfind(".")
                last_sep = max(last_comma, last_dot)
                if last_sep == -1:
                    return float(val.replace(",", "").replace(".", ""))  # Sin separadores → entero

                # Eliminar todo excepto dígitos
                digitos = ''.join(c for c in val if c.isdigit())

                # Calcular la posición del decimal respecto a original
                cant_decimales = len(val) - last_sep - 1  # cuántos caracteres hay después del separador
                if cant_decimales == 0:
                    return float(digitos)  # el separador estaba al final, sin decimales

                parte_entera = digitos[:-cant_decimales] or "0"
                parte_decimal = digitos[-cant_decimales:]
                nuevo_valor = f"{parte_entera}.{parte_decimal}"

                return float(nuevo_valor)
            except Exception as e:
                print(f"⚠️ Error limpiando número '{valor}': {e}")
                return 0.0
        

        df["Cantidad"] = df["Cantidad"].apply(normalizar_numero)
        df["Total"] = df["Total"].apply(normalizar_numero)

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
No agregues columnas ni quites. Deben ser estas 5.
Como última opción, en caso que no encuentres un campo, pon 0.
Columnas:
- "Código Gem" corresponde a la columna "Articulo", segunda columna de la factura.
- "Producto Gem" → es la tercera columna, llamada "Descripción"
- "Cantidad Gem" → es la primer columna, llamada "Cantidad". Trae solo la cantidad.
- "Precio Gem" corresponde a la columna "Precio unit."
- "Total Gem" usar columna "Importe".




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
"0","Barritas de submarino Aguila Caja (24 x 14 gr)","1","14946,31","14946,31"
"0","Queso Crema Milka ut Balde x 3.6 Kg","2","40698,53","81397,05"
"0","Rebozador Preferido Bolsa x 5 Kg","1","8961,05","8961,05"

Imagen: {download_url}
'''
