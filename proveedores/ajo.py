import pandas as pd
from io import StringIO
from connect_gemini import estructurar_con_prompt_especifico
import csv

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
** Código: Es la primer columna, que se referencia como "ID". El contenido, osea los ID o Códigos puede variar un poco pero generalmente siguen un formato como: ECOM035, ECOM107. 
** Producto: Corresponde a descripcion de cada producto, columna "Producto".
En el campo Producto puede que de desacomoden las columnas en el OCR, por ende, te voy a dar algunos artículos (no todos), para que entiendas en dónde están ubicadas las descripciones correctamente en el OCR, para que no te confundas con otro campo:
Pan de Pebete,Baby Ribs Ahumado,Pulled Bites,Patitas de Pollo,Salsa Cheddar,Salsa BBQ Baby,Ali oli,Bbq Black,Salsa Coleslaw,Salsa de remolacha,Empanadas de Carne,Recargo 15% por refuerzo,Queso Pategras,SAL DE HAMBURGUESA,Mantel Grande (parafinado con logo),MEDALLON DE HAMBURGUESA,Beef Ahumado (Beef Ahumado (pulled)),Spare Ribs Ahumadas,St. Louis ahumadas,Salsa lomo / beef,Hummus,Pepinos encurtido seco,Locro,SALSA DE HAMBURGUESA,Queso Crispy,Pan de papa,PAN CON SESAMO PARA HAMBURGUESA,Panceta para hamburguesa,Lomo Ahumado (Porcionado),All Oli,Sal de papas fritas,Mantel Tetra 5%co,Tortilla de Miel,Pan de paov
Beef Ahumado (Beef Ahumado (pulle-fil)  
Pulled Poix (Pulled Poix)
Lomo Ahumado (Porcionado)
Pollo Ahumado (para Caesar)
PAPEL BOBINA KRAFT ANCHO 40CM - CON LOGO
Buzo para personal (S)
Tortilla de Maíz
Pulled Pork (Pulled Pork)
AROS DE CEBOLLA
Buzo para personal (M)
Pan de Pebete
** Cantidad: Corresponde a los valores de la columna "Cantidad", la cual nos brinda información de cuantos kgs o unidades compramos. Ten en cuenta en este campo que, el proveedor indica de estas maneras: "1.0" para decir correctamente una unidad (1). No uses separador de miles, solo "," comas para separador de decimales.
** Ejemplo de valores en Cantidad que se presentarán en las facturas: "40.0", Correcta transformacion: "40,0". Ej: "1.0", Correcta transofrmación: "1,0".
** Ignora los valores de la columna "Unidad".
** Precio OCR: Corresponde a la columna "Precio" unitario. Ten en cuenta que, al igual que en cantidad, el proveedor puede indicarnos de manera: "81.704,32" para informarnos de, (manera que corresponde) 81704,32. Es importante que incluyas las comas "," en los decimales. No incluyas separador de miles.
** Total: Corresponde a la columna "Total". Ten en cuenta que, al igual que en cantidad, el proveedor puede indicarnos de manera: "81.704,32" para informarnos de, (manera que corresponde) 81704,32. Es importante que incluyas las comas "," en los decimales. No incluyas separador de miles.
📍 El Local será el primer texto de la factura antes del guión "-"
🧾 El proveedor será "Ajo".

**Formato CSV válido:**
Tenes prohibido agregar texto, información o lo que fuera antes o después del csv. Solo quiero la tabla con información, lista para integrar en posteriores procesos.
- Todos los campos entre comillas dobles (").
- Separados por coma.
- Una línea por producto.
- Repetí la Codigo si aparece solo una vez.
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

        df = pd.DataFrame(filas_validas, columns=["Codigo", "Producto", "Cantidad", "Precio OCR", "Total", "Local", "Proveedor"])

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
            "Codigo", "Producto", "Cantidad", "Precio", "Total", "Local", "Proveedor", "Alerta",
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

⚠ No modifiques la información del OCR.
** Código: Es la primer columna, que se referencia como "ID". El contenido, osea los ID o Códigos puede variar un poco pero generalmente siguen un formato como: ECOM035, ECOM107. 
** Producto: Corresponde a descripcion de cada producto, columna "Producto".
En el campo Producto puede que de desacomoden las columnas en el OCR, por ende, te voy a dar algunos artículos (no todos), para que entiendas en dónde están ubicadas las descripciones correctamente en el OCR, para que no te confundas con otro campo:
Pan de Pebete,Baby Ribs Ahumado,Pulled Bites,Patitas de Pollo,Salsa Cheddar,Salsa BBQ Baby,Ali oli,Bbq Black,Salsa Coleslaw,Salsa de remolacha,Empanadas de Carne,Recargo 15% por refuerzo,Queso Pategras,SAL DE HAMBURGUESA,Mantel Grande (parafinado con logo),MEDALLON DE HAMBURGUESA,Beef Ahumado (Beef Ahumado (pulled)),Spare Ribs Ahumadas,St. Louis ahumadas,Salsa lomo / beef,Hummus,Pepinos encurtido seco,Locro,SALSA DE HAMBURGUESA,Queso Crispy,Pan de papa,PAN CON SESAMO PARA HAMBURGUESA,Panceta para hamburguesa,Lomo Ahumado (Porcionado),All Oli,Sal de papas fritas,Mantel Tetra 5%co,Tortilla de Miel,Pan de paov
Beef Ahumado (Beef Ahumado (pulle-fil)  
Pulled Poix (Pulled Poix)
Lomo Ahumado (Porcionado)
Pollo Ahumado (para Caesar)
PAPEL BOBINA KRAFT ANCHO 40CM - CON LOGO
Buzo para personal (S)
Tortilla de Maíz
Pulled Pork (Pulled Pork)
AROS DE CEBOLLA
Buzo para personal (M)
Pan de Pebete
** Cantidad: Corresponde a los valores de la columna "Cantidad", la cual nos brinda información de cuantos kgs o unidades compramos. Ten en cuenta en este campo que, el proveedor indica de estas maneras: "1.0" para decir correctamente una unidad (1). No uses separador de miles, solo "," comas para separador de decimales.
** Ejemplo de valores en Cantidad que se presentarán en las facturas: "40.0", Correcta transformacion: "40,0". Ej: "1.0", Correcta transofrmación: "1,0".
** Ignora los valores de la columna "Unidad".
** Precio OCR: Corresponde a la columna "Precio" unitario. Ten en cuenta que, al igual que en cantidad, el proveedor puede indicarnos de manera: "81.704,32" para informarnos de, (manera que corresponde) 81704,32. Es importante que incluyas las comas "," en los decimales. No incluyas separador de miles.
** Total: Corresponde a la columna "Total". Ten en cuenta que, al igual que en cantidad, el proveedor puede indicarnos de manera: "81.704,32" para informarnos de, (manera que corresponde) 81704,32. Es importante que incluyas las comas "," en los decimales. No incluyas separador de miles.

**Formato CSV válido:**
Prohibido agregar letras, texto, palabras antes o después del CSV. Solo necesito la tabla limpia con la información.
 No pongas ```csv ni ningun carácter fuera del CSV.
 Es importante que no pongas ```csv ni ``` ya que esto rompe el formato. Respeta. Solo CSV limpio.
- Todos los campos entre comillas dobles (").
- Separados por coma.
- Una línea por producto.
- Repetí la Codigo si aparece solo una vez.
- No uses separadores de miles.
- Sin encabezado.

Imagen: {download_url}
'''