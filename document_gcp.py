import os
import time
import pandas as pd
from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions
from collections import defaultdict

# ✅ Configurar entorno
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_ocr.json"

# 📄 Configuración Document AI
project_id = "600456283474"
location = "us"
processor_id = "b668a0883f50e7fa"
endpoint = "us-documentai.googleapis.com"
input_folder = "C:/Users/gesti/Downloads/drive-download-20250708T155846Z-1-001"
output_folder = os.path.join(input_folder, "procesadas")
os.makedirs(output_folder, exist_ok=True)

# 🔌 Cliente Document AI
client_options = ClientOptions(api_endpoint=endpoint)
client = documentai.DocumentProcessorServiceClient(client_options=client_options)
processor_name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"

# 🔁 Iterar sobre imágenes JPG
for filename in os.listdir(input_folder):
    if not filename.lower().endswith(".jpg"):
        continue

    image_path = os.path.join(input_folder, filename)
    print(f"\n📄 Procesando: {filename}")

    with open(image_path, "rb") as image_file:
        image_content = image_file.read()

    raw_document = documentai.RawDocument(content=image_content, mime_type="image/jpeg")
    request = documentai.ProcessRequest(name=processor_name, raw_document=raw_document)

    # 💤 Esperar 5 segundos antes de llamar a Document AI
    time.sleep(5)

    result = client.process_document(request=request)
    document = result.document

    # 📌 Extraer entidades con coordenada Y
    column_entities = defaultdict(list)

    def get_y_position(entity):
        try:
            return min(v.y for v in entity.page_anchor.page_refs[0].bounding_poly.normalized_vertices)
        except:
            return 0.0
    for entity in document.entities:
        print(f"{entity.type_}: {entity.mention_text}")
    for entity in document.entities:
        y = get_y_position(entity)
        column_entities[entity.type_].append((y, entity.mention_text))

    # 📋 Ordenar cada columna por eje Y ascendente
    for field in column_entities:
        column_entities[field].sort(key=lambda x: x[0])

    # 🧱 Combinar por posición
    max_len = max(len(v) for v in column_entities.values())
    rows = []

    for i in range(max_len):
        row = {}
        for field, values in column_entities.items():
            if i < len(values):
                row[field] = values[i][1]
            else:
                row[field] = None
        rows.append(row)

    # 🧾 Crear DataFrame y agregar columna de nombre de archivo
    df = pd.DataFrame(rows, columns=["Cantidad", "Codigo", "Producto", "Subtotal"])
    df["Archivo"] = os.path.splitext(filename)[0]

    # 🖨 Mostrar DataFrame
    print("\n📊 DataFrame generado:")
    print(df)

    # 💾 Exportar
    excel_filename = os.path.splitext(filename)[0] + ".xlsx"
    output_path = os.path.join(output_folder, excel_filename)
    df.to_excel(output_path, index=False)
    print(f"✅ Exportado a: {output_path}")
