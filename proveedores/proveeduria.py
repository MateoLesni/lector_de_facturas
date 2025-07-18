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
** Codigo: Corresponde a la columna "Código" del OCR.
** Producto: Corresponde a "Descripcion" (segunda columna) de cada producto.
** Cantidad: Corresponde a los valores de la columna "Cant. Kg/Lt". Solo las cantidades. Es la cuarta columna.
** Precio OCR: Corresponde a la columna "Precio" Copia el número tal cual te lo brinda el OCR.
** Total: Corresponde a la columna "Importe". Copia el número tal cual te lo brinda el OCR.
📍 El Local será el texto que sigue a la palabra "Cliente:"
🧾 El proveedor será "Le Soleil".

Código Descripción Cant.
UNI Cant.
Kg/Lt Precio Importe
00002 JAMON CUCIDO SABORES 5.00 20.70 Kg 7,947.18 164,506.63
00295 Mermeleda de frutos 1.00 1.00 UN 20,032.53 20,032.53
00261 Hjnicocale x 200 u T 4.00 4.00 UN 11,169.60 44,679.40
00293 Barritas cacao y ama 1.00 1.00 UN 25,415.00 25,415.00
00266 Papas gauchitas caja 1.00 1.00 UN 21,736.00 21,736.00
00312 Rodajas de naranja 1 1.00 1.00 UN 48,100.00 48,100.00
00277 Granola para yogurt 1.00 1.00 UN 8,953.31 8,953.31
00296 Tableta Dulce de leo 1.00 1.00 UN 27,306.76 27,306.76
00281 Chocolate p/rahmarin 1.00 1.00 UN 102,860.55 102,860.55
00331 Mla de semillas 1.00 1.00 UN 12,350.00 12,350.00

De esta extracción del OCR, la correcta estructuración de la factura según sus columnas sería así:
Ejemplo primera línea.
"Código","Producto", "Cantidad", "Precio OCR", "Importe"
"00002", "Jamon Cucido Sabores", "20,70", "7.947,18", "164.506,63" 


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
- "Código Gem" corresponde la primer columna, llamada "Código"
- "Producto Gem" → es la segunda columna, llamada "Descripción"
- "Cantidad Gem" → es la cuarta columna, llamada "Cant. Kg/Lt". 
- "Precio Gem" corresponde a la columna "Precio"
- "Total Gem" usar columna "Importe".

**
Si extrayeras texto de la factura como este:

Código Descripción Cant.
UNI Cant.
Kg/Lt Precio Importe
00002 JAMON CUCIDO SABORES 5.00 20.70 Kg 7,947.18 164,506.63
00295 Mermeleda de frutos 1.00 1.00 UN 20,032.53 20,032.53
00261 Hjnicocale x 200 u T 4.00 4.00 UN 11,169.60 44,679.40
00293 Barritas cacao y ama 1.00 1.00 UN 25,415.00 25,415.00
00266 Papas gauchitas caja 1.00 1.00 UN 21,736.00 21,736.00
00312 Rodajas de naranja 1 1.00 1.00 UN 48,100.00 48,100.00
00277 Granola para yogurt 1.00 1.00 UN 8,953.31 8,953.31
00296 Tableta Dulce de leo 1.00 1.00 UN 27,306.76 27,306.76
00281 Chocolate p/rahmarin 1.00 1.00 UN 102,860.55 102,860.55
00331 Mla de semillas 1.00 1.00 UN 12,350.00 12,350.00

De esta extracción del OCR, la correcta estructuración de la factura según sus columnas sería así:
Ejemplo primera línea.
"Código","Producto", "Cantidad", "Precio OCR", "Importe"
"00002", "Jamon Cucido Sabores", "20,70", "7.947,18", "164.506,63" 

Entiende cuáles son las columnas que necesito, esto es importante.


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
