import pandas as pd
from io import StringIO
from rapidfuzz import process, fuzz
import unicodedata
from connect_gemini import estructurar_con_prompt_especifico

articulos_validos = [
    "APIO", "ACELGA", "AJO", "AJO GRANDE", "AJI AMARILLO", "AJI JALAPEÑO", "ALBAHACA", "ANCO BATATA", "ANCO"
    "BROTES VARIOS", "BOÑATO", "BATATA", "BERENJENA", "BERRO", "BROCCOLI LIMPIO", "BROCOLI LIMPIO", "BROCOLI CON HOJAS", "BROCCOLI CON TA/HOJAS",
    "CABUTIE", "CAPUCHINA", "CEBOLLA ROJA", "CEBOLLON", "CEBOLLA", "C. DE VERDEO", "CEBOLLA DE VERDEO", "CEBOLLA MORADA",
    "CIBOULETTE", "CILANTRO", "COLIFLOR", "CHAMPIÑON", "CHAUCHA", "CHOCLO", "CEDRON", "ENELDO", "ESPINACA",
    "FLORES", "HINOJO", "HUACATAY", "JENGIBRE", "KALE", "LECHUGA","LECHUGA MORADA", "LECHUGA FRANCESA", "LECHUGA MANTECOSA",
    "LOCOTO", "MANDIOCA", "MENTA", "MORADA", "MORRON VER", "MORRON AMARIL", "MORRON ROJO", "OREGANO",
    "PAPON X BOLSA", "PAPA LAVADA", "PAPA BLANCA/ NEGRA", "PAPA BLANCA", "PAPA NEGRA", "PAPIN", "PEPINO",
    "PEREJIL", "PEREJIL CRESPO", "PORTOBELLO", "PUERRO", "REMOLACHA LIMPIA", "ROMERO", "RUCULA",
    "REPOLLO BCO", "REPOLLO ROJO", "TOMATE", "T. CHERRY", "T.PERITA", "TOMILLO", "ZANAHORIA", "ZANAHORIA INDUS", "FRUTILLA",
    "ZAPALLITO", "ZUCHINI", "ARANDANO", "BANANA ECU", "BANANA ECUADOR", "BANANA BOLI", "BANANA", "BANANA ECUADOR", "CIRUELA", "FRUTILLA TAMARA", "DURAZNO",
    "GIRGOLAS", "KIWI IMP GDE", "KIWI", "LIMON", "LIMA BRAZIL", "MANDARINA", "MANZANA RED", "MANZANA RED  TOP",
    "MANZANA GRANY", "MELON AMARILLO", "MANGO UNI", "NARANJA JUGO", "NARANJA OMBLIGO", "PERA CAJA", "PIÑA", "NARANJA",
    "PALTA HASS", "PALTA A PUNTO", "PALTA A PUNTO X", "POMELO ROJO", "POMELO", "SANDIA", "SOJA BOLSA", "SOJA", "SALVIA", "UVA NEGRA S/SEMILLA",
    "UVA BLANCA S/SEMILLA", "HUEVO BCO", "HUEVO", "CARBON", "CONGELADOS", "FRUTILLA CONGELADA",
    "FRUTOS ROJOS CONG", "MARACUYA CONGELA", "ARANDANO CONGEL"  
]

diccionario_errores = {
    "FRUTILLA": ["frut", "fretillu", "frotillen", "frutila", "frutilla.", "frutill"],
    "PERA": ["pero", "peru", "perra", "peda", "peta"],
    "CEBOLLA": ["CERULLA", "seboya", "CERVILLA"],
    "CEBOLLON": ["CEROLLOA", "CEROLLON", "CEBOLOA"],
    "ALBAHACA": ["albajaca", "albahca", "alvaaca", "ALABANCA", "ALBHARACA"],
    "ZANAHORIA": ["zanaharia", "zanajoria", "sanahoria"],
    "CIBOULETTE": ["CIRCULLATE", "CIBOLETE"],
    "SOJA": ["AGIA", "SOJ"],
    "PAPA NEGRA": ["PAPA NEURA", "PAPA NERA", "PAPA EGRA", "PEPE NEGRA", "PARA SEURA"],
    "KIWI": ["KINT", "KIW", "KII", "NIWI", "NIKI", "KINC"],
    "TOMILLO": ["TORCELO", "TOMELO"],
    "NARANJA": ["BARANZE", "NRNJA", "BARARJA"],
    "BANANA": ["BANDES", "BARANA", "BAN"],
    "PEREJIL": ["PERSJIL", "PERIJOL"],
    "RUCULA": ["RUCOLA", "RUCULE"],
    "ARANDANO": ["ARABOANO", "ARADAN"],
    "TOMATE": ["TUMATE", "TOMETE"],
    "PALTA A PUNTO": ["PALTA A PUNTO X", "PALTA"],
    "ZUCHINI":["ZOQUINI", "ZOQUINl"],
    "MANZANA":["MINCARA", "MANSARA"]
}

def normalizar(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.upper().strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8")
    return texto

def match_con_diccionario(producto):
    producto_normalizado = normalizar(producto)
    for clave_correcta, variantes in diccionario_errores.items():
        variantes_normalizadas = [normalizar(v) for v in variantes]
        match = process.extractOne(producto_normalizado, variantes_normalizadas, scorer=fuzz.ratio)
        if match and match[1] >= 81:
            return clave_correcta
    return None

def procesar(texto_ocr):
    prompt=f"""
Tu rol es actuar como un operador de Data Entry para una empresa gastronómica. Vas a estructurar facturas como una tabla con las siguientes columnas:
Codigo, Producto, Cantidad, Precio OCR, Total, Local, Proveedor
Tenes determinadamente prohibido inventar información. Si no encontras un campo, como última opción pon '0'.
Local: El local está escrito debajo del logo del proveedor.
Proveedor: Siempre será "Verduleria Raices"
⚠️ Cada línea debe tener exactamente 7 columnas, separadas por coma.
⚠️ No incluyas comentarios ni líneas fuera del formato CSV. Ignorá remitos, totales, descuentos y notas al pie.
Las cantidades y subtotal está siempre a la derecha de la descripción del producto. Subtotal es muy importante que entiendas que está al final de la línea de cada producto. No puedes equivocarte en ningún campo, menos en este!
Ignorar los numeros que están antes del producto o descripción. (Son códigos del proveedor que no nos interesan.)
Por ej: (código)'2' 1 (descripción)'Albahaca' ....... PAQUETE...     (cantidad)'6.00'  (precio)'500.00'   (subtotal)'3000.00' 
|  2 | 1 ALBANACA. | PAQUETE. | 6.00 | 500.00 | 3,000.00  |
| --- | --- | --- | --- | --- | --- |
|  33 | 1 ZOQUINI. | KILOS. | 2.00 | 930.00 | 1,860.00  |
|  18 | 1 BERENJENA. | KILOS. | 2.00 | 1,200.00 | 2,400.00  |
|  35 | 1 BATATA. | KILOS. | 4.00 | 890.00 | 3,560.00  |
|  1 | 3 CEBOLLA. | MORADA. | 1.50 | 818.00 | 1,227.00  |
|  38 | 1 HUEVO. | bandeja. | 1.00 | 6,000.00 | 6,000.00  |
|  191 | 1 APIO. | UNIZAD. | 1.00 | 2,000.00 | 2,000.00  |
|  923 | 1 CHERRY. | KILOS. | 2.00 | 7,000.00 | 14,000.00  |
En este caso, por más que el OCR marcó una línea debajo de la "albanaca", debes integrarlo también como un producto ya que contiene todos los campos como un artículo más.

La primer columna es el código, segunda columna es descripción, cuarta columna cantidades, quinta columna precio, sexta columna subtotal.
El orden de estas puede que varíe según el trabajo del OCR. Es solo a modo informativo para que encuentres patrones.
Ignora si el producto es por Paquete o por Kilo/s. Solo nos interesa saber qué verdura o fruta es. El resto no importa en descripción.
**Formato CSV válido:**  
   - IMPORTANTE: los campos deben estar entre comillas dobles (`"`).  por ej "Lechuga", "0,5", "100", "50"
   - Separá los campos con comas.  
   - Una línea por producto.  
   - **No uses separadores de miles.**

Tenes totalmente prohibido recortar o agregar información no pedida explícitamente. No recortes ni abrevies descripciones, no modifiques ni redondees precios ni cantidades.

 ** Cantidad: El proveedor en Cantidad pondrá "0.50" o pondrá "1.0" esto significa, correctamente en "0,5" y en el segundo ejemplo "1". No uses los puntos que usa el proveedor. Solo tienes permitido usar las comas para separar decimales. Miles no separes.
 ** Total: Es el último número de cada fila que presenta el OCR. Lo mismo que en "Cantidad", el proveedor usa "," para separar los miles y "." para separar decimales. Solo usaremos "," para separar decimales. Tenes prohibido separar miles.  
No uses puntos en ningún campo. Solo usa "," para separar decimales. Como por ejemplo "0,5" o "1234,4" (mil doscientos trenta y cuatro con cuarenta)
 Estos dos puntos son claves para el exitoso funcionamiento del prompt. Presta atención.
   
 No recortes información de la descripción a menos que sean palabras exactamente como "UNIDAD", "KILO", "BANDEJA","KILOS", "PAQ", "PAQUETES", "PAQUETE", "KG".
Importante: Tenes totalmente prohibido inventar numeros, precios, lo que fuera. Solo eres un proceso de estructuracion del texto del OCR.
Respeta el OCR, solo tenes permitido encontrar similitudes con los productos proporcionados. Del resto, respeta absolutamente todo.
Examina con detenimiento similitudes de letras. No pongas cualquier cosa.
❗ Devuelve solo los datos en formato CSV puro (sin encabezados Markdown, sin texto extra, sin explicaciones). Si no hay datos, devuelve un CSV vacío con solo los encabezados.
Solo devuelve las filas estructuradas en formato CSV puro.
❌ No uses `|` ni encabezados de tabla.
✅ Usa comas para separar los campos.
Recuerda que los campos deben estar entre comillas dobles (`"`)
✅ No devuelvas explicaciones ni encabezados Markdown.


Texto OCR:
\"\"\"{texto_ocr}\"\"\"
"""
    
    resultado_csv = estructurar_con_prompt_especifico(prompt)

    if not resultado_csv or resultado_csv.strip() == "":
        print("⚠️ Gemini no devolvió datos útiles.")
        return None

    try:
        df = pd.read_csv(StringIO(resultado_csv), header=None)

        if df.shape[1] == 7:
            df.columns = ["Codigo", "Producto", "Cantidad", "Precio OCR", "Total", "Local", "Proveedor"]
        elif df.shape[1] == 6:
            df.columns = ["Codigo", "Producto", "Cantidad", "Total", "Local", "Proveedor"]
            df["Precio OCR"] = ""
            df = df[["Codigo", "Producto", "Cantidad", "Precio OCR", "Total", "Local", "Proveedor"]]
        else:
            print(f"❌ Estructura de columnas inesperada: {df.shape[1]} columnas")
            print(df.head())
            return None

        def limpiar_numero(valor):
            if pd.isna(valor):
                return 0.0
            valor_str = str(valor).replace("$", "").replace(" ", "").replace(".", "").replace(",", ".")
            return float(valor_str)

        df["Cantidad"] = df["Cantidad"].apply(limpiar_numero)
        df["Total"] = df["Total"].apply(limpiar_numero)

        
        df["Precio"] = (df["Total"] / df["Cantidad"]).round(2)

        df = df[df["Producto"].notna() & (df["Producto"].str.strip() != "")]
        df = df[df["Cantidad"] > 0]
        

        def obtener_mejor_match(producto_original):
            producto_normalizado = normalizar(producto_original)

            for umbral in [90, 88]:
                match = process.extractOne(producto_normalizado, [normalizar(x) for x in articulos_validos], scorer=fuzz.token_sort_ratio)
                if match:
                    mejor_match, score, *_ = match
                    if score >= umbral:
                        return mejor_match

            corregido = match_con_diccionario(producto_original)
            if corregido:
                return corregido

            return producto_original


        df["Producto"] = df["Producto"].apply(obtener_mejor_match)
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
Columnas:
- "Código Gem" usar el "Código" del proveedor para cada artículo. Los códigos pueden variar, generalmente son números chicos como "12", "1", "2". Son números sin espacios. y el código es el primero que está antes del espacio.
- "Producto Gem"  usar "Descripción"
- "Cantidad Gem" → usar el número que está luego de descripción y unidad de medida. es decir, primer número luego de texto.
- "Precio Gem" es la columna que le sigue a cantidad.
- "Total Gem" última columna del lado derecho.

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
