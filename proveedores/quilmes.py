import pandas as pd
from io import StringIO
from connect_gemini import estructurar_con_prompt_especifico
import csv

def corregir_columna_codigo(df):
    """
    Detecta si la columna de códigos no está en la posición 0.
    Si es así, la mueve al inicio y desplaza la columna que estaba allí a su lugar original.
    """
    if df.shape[1] != 5:
        print(f"❌ Error: se esperaban 5 columnas, se recibieron {df.shape[1]}")
        return df

    def es_codigo(celda):
        val = str(celda).strip().replace('"', '').replace(" ", "")
        return val.isdigit() and not any(c in val for c in [",", "."])

    # Buscar qué columna contiene mayor cantidad de códigos válidos
    puntajes = []
    for i in range(5):
        puntaje = df.iloc[:, i].apply(es_codigo).sum()
        puntajes.append(puntaje)

    indice_codigo = puntajes.index(max(puntajes))

    if indice_codigo == 0:
        # Ya está bien ubicada
        return df

    # Intercambiar columna de códigos con la que está en la posición 0
    columnas = list(df.columns)
    columnas[indice_codigo], columnas[0] = columnas[0], columnas[indice_codigo]
    df = df[columnas]

    print(f"🔁 Columna de códigos detectada en posición {indice_codigo}, movida al inicio.")
    return df



def limpiar_cantidad(valor):
    try:
        val = str(valor).strip().lower()
        if val in ["", "nan", "none", "oferta"]:
            return 0.0
        val = val.replace('"', "").replace(" ", "").replace(".", "").replace(",", ".")
        return float(val)
    except:
        return 0.0


def limpiar_numero(valor):
    try:
        val = str(valor).strip().lower()
        if val in ["", "nan", "none", "oferta"]:
            return 0.0
        val = val.replace('"', "").replace(" ", "").replace(".", "").replace(",", ".")
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
** Código: Es la tercer columna, que se referencia como "COD" en el OCR. El contenido, osea los ID o Códigos puede variar un poco pero generalmente siguen un formato como: 14933, 31205, 30481, 30648. 
** Producto: Corresponde a descripcion de cada producto, columna "DESCRIPCION" del OCR.
** Cantidad: Corresponde a los valores de la primer columna, es decir columna del OCR "BULTOS", la cual nos brinda información de cuantos kgs o unidades compramos. Ten en cuenta en este campo que, el proveedor indica de estas maneras: "1.0" para decir correctamente una unidad (1). No uses separador de miles, solo "," comas para separador de decimales.
** Ejemplo de valores en Cantidad que se presentarán en las facturas: "40.0", Correcta transformacion: "40,0". Ej: "1.0", Correcta transofrmación: "1,0".
** Precio OCR: Corresponde a la columna "PRECIO UNI" del OCR. Ten en cuenta que, el proveedor puede indicarnos de manera: "81704.32" para informarnos de, (manera que corresponde) 81704,32. Es importante que incluyas las comas "," en los decimales. No incluyas separador de miles.
** Total: Corresponde a la columna "SUBTOTAL" del OCR. Ten en cuenta que, al igual que en PRECIO OCR, el proveedor puede indicarnos de manera: "81704,32" para informarnos de, (manera que corresponde) 81704,32. Es importante que incluyas las comas "," en los decimales. No incluyas separador de miles.
🧾 El proveedor será "Quilmes".

No podes inventar información. Es decir, si no encuentras la información; mira repetidas veces el texto del OCR. Si dados estos intentos no encuentras la información, como última opción, pon 0 en el campo y listo. 

**Formato CSV válido:**
En caso que un campo sea error, pon "0". Debe estar entre doble comillas también al igual que todos los valores.
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
Las columnas deben estar en el siguiente orden exacto:
"Código Gem","Producto Gem","Cantidad Gem","Precio Gem,"Total Gem"

Siempre tienen que ser 5 columnas. Los valores están en la imagen, busca bien.
Respeta el Orden. Siempre comienza por el código.

⚠ No modifiques la información de la imagen.
(Las referencias de número de columna son dadas contando desde la primera de la izquierda, osea BULTOS sería la número 1.)
Importante: Tenes que tener en claro estas reglas, ya que estas son estáticas. No cambia nunca el orden. Respeta a raja tabla cada una de las especificaciones y tendremos la extracción correcta.
** Reglas:
Siempre ignora los valores de "UNI" es decir las unidades de medida como pack, unidad, etc. No nos interesan.
** Código Gem: Siempre es un número que jamás un código tendría un punto com oseparador de miles. Si tiene un separador de miles, o decimales, no es el código.
Es la (columna 3) que se referencia como "COD". El contenido, osea los ID o Códigos puede variar un poco pero generalmente siguen un formato como: 14933, 31205, 99900, 31074. 
El código siempre está antes de la descripción. Es decir, cuando termina el número, comienza la descripción del artículo.
La manera de reconocer el código puede ser el saber que el código no tiene separador de miles en la factura. Es decir, es siempre "20301" por ej.
** Producto Gem: Corresponde a (la columna 4) "DESCRIPCION" de la factura, que indica detalle de cada producto.
** Cantidad Gem: Corresponde a los valores de la primer columna (Columna 1), es decir columna del OCR "BULTOS", la cual nos brinda información de cuantos kgs o unidades compramos. Ten en cuenta en este campo que, el proveedor indica de estas maneras: "1.0" para decir correctamente una unidad (1). No uses separador de miles, solo "," comas para separador de decimales.
** Precio Gem: Corresponde a la (columna 5) "PRECIO UNI" de la imagen, es el campo posterior a la descripción. Ten en cuenta que, el proveedor puede indicarnos de manera: "81704.32" para informarnos de, (manera que corresponde) 81704,32. Es importante que incluyas las comas "," en los decimales. No incluyas separador de miles.
** Ejemplo de valores en Cantidad que se presentarán en las facturas: "40.0", Correcta transformacion: "40,0". Ej: "1.0", Correcta transofrmación: "1,0".
** Total Gem: Corresponde a la columna (En imagen"SUBTOTAL") del OCR (columna 8). Ten en cuenta que, el proveedor puede indicarnos de manera: "81704,32" para informarnos de, (manera que corresponde) 81704,32. Es importante que incluyas las comas "," en los decimales. No incluyas separador de miles.
** Necesitamos el SubTotal ya que es el subtotal sin impuestos y es lo que nos interesa. No traigas otro campo.
** Hay posibilidad de que el "Total" (En imagen SubTotal) diga 0.00. Si es el caso, trae el 0,00
**Formato CSV válido:**
Prohibido agregar letras, texto, palabras antes o después del CSV. Solo necesito la tabla limpia con la información.
 Importante: No pongas ```csv ni ningun carácter fuera del CSV.
 Es importante que no pongas ```csv ni ``` ya que esto rompe el formato. Respeta. Solo CSV limpio.
- Todos los campos entre comillas dobles (").
- Separados por coma.
- Una línea por producto.
- Repetí la fecha si aparece solo una vez.
- No uses separadores de miles.
- Sin encabezado.

Imagen: {download_url}
'''