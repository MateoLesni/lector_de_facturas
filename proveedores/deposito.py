import pandas as pd
from io import StringIO
from connect_gemini import estructurar_con_prompt_especifico
import csv


def limpiar_numero(valor):
    try:
        val = str(valor).strip()
        if not val or pd.isna(val):
            return 0.0

        # Si es número argentino con separador de miles: "18.974,70"
        if "," in val and "." in val:
            val = val.replace(".", "").replace(",", ".")
        elif "," in val:
            val = val.replace(",", ".")  # decimal simple
        # Si solo tiene punto (en lugar de coma), lo dejamos así

        return float(val)
    except:
        return 0.0

# Lo mismo para cantidad:
def limpiar_cantidad(valor):
    return limpiar_numero(valor)




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
"Código","Producto","Cantidad","Precio OCR","Total","Local","Proveedor"

Está totalmente prohibido inventar información. Si no encuentras algo, como última opción pon "0". La información está toda en el texto del OCR.
Prohibido agregar texto, carácteres o letras antes o despúes del csv. (Ejemplo prohibido: ```csv)
❗ No incluyas la columna Precio. Esa será calculada luego.
⚠ No modifiques la información del OCR.
** Código: Es la primer columna, es decir la columna del OCR "Codigo"
** Producto: Corresponde a descripcion de cada producto, columna "DESCRIPCION" del OCR.
** Cantidad: Corresponde a los valores de la tercer columna, es decir columna del OCR "Cantidad", la cual nos brinda información de cuantos kgs o unidades compramos. 
** Precio OCR: Corresponde a la columna "Precio Neto Unitario" del OCR.
** Total: Corresponde a la columna "Total Neto" del OCR. 
🧾 El proveedor será "Depósito Central".

Los números proporcionados son formato "132,00" o "132,000" que corresponden a ciento treinta y dos. Otro ej: "5.142,00" y "5.142,000" que ambos corresponden a cinco mil ciento cuarenta y dos. No uses separador de miles, solo usa "," para separador de decimales.


No podes inventar información. Es decir, si no encuentras la información; mira repetidas veces el texto del OCR. Si dados estos intentos no encuentras la información, como última opción, pon 0 en el campo y listo. 

**Formato CSV válido:**
Tenes prohibido agregar texto, información o lo que fuera antes o después del csv. Solo quiero la tabla con información, lista para integrar en posteriores procesos.
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
                val = str(valor).strip()
                if not val or pd.isna(val):
                    return 0.0

                # Si tiene coma, es formato europeo: separador decimal es la coma
                if "," in val:
                    # Elimina todos los puntos (separadores de miles)
                    val = val.replace(".", "")
                    # Reemplaza la coma decimal por punto
                    val = val.replace(",", ".")
                else:
                    # Si no tiene coma pero tiene múltiples puntos, es tipo 18.974.700
                    # → mantener solo el último punto como decimal
                    if val.count(".") > 1:
                        partes = val.split(".")
                        val = "".join(partes[:-1]) + "." + partes[-1]
                    # Sino, dejar el punto como está (formato inglés)

                return float(val)
            except:
                return 0.0

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
                return "Diferencia de Q"
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
    

def prompt_imgia(download_url):
    return f'''
Estás en rol de un Data Entry profesional. Vas a procesar la siguiente imagen de una factura gastronómica.

🔗 Enlace a la imagen: {download_url}


Tu rol es actuar como un operador de Data Entry profesional para una empresa gastronómica. Vas a extraer y estructurar facturas como una tabla con las siguientes columnas:
Las columnas deben estar en el siguiente orden exacto:
"Código Gem","Producto Gem","Cantidad Gem","Precio Gem,"Total Gem"

Está totalmente prohibido inventar información. Si no encuentras algo, como última opción pon "0". La información está toda en el texto del OCR.
Prohibido agregar texto, carácteres o letras antes o despúes del csv. (Ejemplo prohibido: ```csv)
⚠ No modifiques la información del OCR.
** Código Gem: Es la primer columna, es decir la columna del OCR "Codigo"
** Producto Gem: Corresponde a descripcion de cada producto, columna "DESCRIPCION" del OCR.
** Cantidad Gem: Corresponde a los valores de la tercer columna, es decir columna del OCR "Cantidad", la cual nos brinda información de cuantos kgs o unidades compramos. 
** Precio Gem: Corresponde a la columna "Precio Neto Unitario" de la imagen.
** Total Gem: Corresponde a la columna "Total Neto" de la imagen.
🧾 El proveedor será "Depósito Central".

Los números proporcionados son formato "132,00" ciento treinta y dos o "5.142,00" cinco mil ciento cuarenta y dos. No uses separador de miles, solo usa "," para separador de decimales.

No podes inventar información. Es decir, si no encuentras la información; mira repetidas veces el texto del OCR. Si dados estos intentos no encuentras la información, como última opción, pon 0 en el campo y listo. 

**Formato CSV válido:**
Obligatoriamente el CSV tiene que contener las 5 columnas extraídas.
No puede haber ni más ni menos columnas. Teniendo en cuenta las anteriores reglas, puedes crear el csv con las columnas.
Tenes prohibido agregar texto, información o lo que fuera antes o después del csv. Solo quiero la tabla con información, lista para integrar en posteriores procesos.
Esos son los campos que tenes que rellenar en base a las reglas anteriormente dadas.
Todos los valores tienen que estar encerrados entre comillas dobles. Es decir: "valor" "21,00", etc. Si no lo haces, rompes el código posterior.
- Todos los campos entre comillas dobles (").
- Separados por coma.
- Una línea por producto.
- No uses separadores de miles.
- Sin encabezado.


Imagen: {download_url}
''' 