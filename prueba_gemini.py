import google.generativeai as genai
import PIL.Image
import io
import os

# --- 1. Configura tu clave de API ---
# Es una buena práctica no codificar la clave directamente.
# Puedes guardarla en una variable de entorno o en un archivo .env
# Para este ejemplo, la ponemos directamente (¡solo para desarrollo/prueba!)
# Reemplaza 'TU_API_KEY_AQUI' con tu clave real.
genai.configure(api_key="AIzaSyD2Lb7u_x68AVNMskV_rrqjXl5mEwX1uH0")

# --- 2. Carga el modelo Gemini 1.5 Flash ---
# Usamos "-latest" para obtener la versión más reciente y estable.
model = genai.GenerativeModel("models/gemini-1.5-flash-latest")

# --- 3. Define la ruta de tu imagen de factura ---
# Asegúrate de que esta ruta sea correcta y que la imagen exista.
imagen_factura_path = "C:/Users/gesti/Downloads/OC 38204 - MR 1000058447 - La Mala - Mayoristanet.Com Sa.jpg" # O tu otra imagen de factura

# --- 4. Carga la imagen usando Pillow ---
try:
    img = PIL.Image.open(imagen_factura_path)
    print(f"Imagen '{imagen_factura_path}' cargada exitosamente.")
except FileNotFoundError:
    print(f"Error: La imagen '{imagen_factura_path}' no se encontró. Verifica la ruta.")
    exit()
except Exception as e:
    print(f"Error al cargar la imagen: {e}")
    exit()

# --- 5. Prepara el prompt de texto ---
prompt_texto = """
Eres un experto en extracción de datos de facturas.
Extrae la siguiente información de la factura y preséntala en formato Csv, de manera tabular
Asegúrate de incluir solo los campos solicitados y si un campo no está presente, usa un valor nulo (null).
No agregues texto antes ni después del csv. Solo la tabla con información.

Campos a extraer:
"Fecha_Factura" fecha en formato dd/mm/yyyy
"Descripcion": "Descripción del producto",
"Cantidad": "Cantidad del producto (si hay KG, dame el número en KG, si es unidad, el número de unidades)",
"Precio_Unitario": "Precio unitario (solo el número)",
"Total_Producto": "Total de la línea del producto (solo el número)"


**Formato CSV válido:**
- Siempre 7 columnas: "Fecha","Producto","Cantidad","Precio OCR","Total","Local","Proveedor"
- Todos los campos entre comillas dobles (").
- Separados por coma.
- Una línea por producto.
- Repetí la fecha si aparece solo una vez.
- No uses separadores de miles.
- Sin encabezado.

"""

# --- 6. Realiza la solicitud al modelo ---
print("\nEnviando solicitud a Gemini 1.5 Flash...")
try:
    response = model.generate_content([prompt_texto, img])

    # --- 7. Imprime la respuesta ---
    print("\nRespuesta del modelo:")
    print(response.text)

except Exception as e:
    print(f"\nOcurrió un error al generar el contenido: {e}")
    # Si recibes un error de "Blocked due to safety", el contenido o la respuesta
    # pueden haber sido marcados por las políticas de seguridad.
    # Puedes intentar ajustar tu prompt o el contenido si es el caso.
    # También, si la imagen es muy grande o compleja, puede haber problemas de token.