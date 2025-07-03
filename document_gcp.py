import os
from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions

# ✅ Configurar variables de entorno
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_ocr.json"

# 📄 Configuraciones de tu Document AI
project_id = "singular-agent-462412-h6"
location = "us"
processor_id = "90f5fb0b73cbadbd"
endpoint = "us-documentai.googleapis.com"

# 📷 Ruta a la imagen
image_path = "C:/Users/gesti/Downloads/OC 29984 - MR 1000062532 - W Infanta - CERVECERIA Y MALTERIA QUILMES SAICA Y G.jpg" # Cambialo por el nombre real

# 🧠 Crear cliente con endpoint correcto
client_options = ClientOptions(api_endpoint=endpoint)
client = documentai.DocumentProcessorServiceClient(client_options=client_options)

# 🧾 Construir nombre del procesador
processor_name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"

# 📤 Leer contenido de la imagen
with open(image_path, "rb") as image_file:
    image_content = image_file.read()

# 📦 Crear documento a procesar
raw_document = documentai.RawDocument(content=image_content, mime_type="image/jpeg")

# 📨 Construir solicitud
request = documentai.ProcessRequest(name=processor_name, raw_document=raw_document)

# 🚀 Enviar imagen a Document AI
result = client.process_document(request=request)

# 📃 Obtener el texto
document = result.document
print("📄 Texto extraído:")
print(document.text)
