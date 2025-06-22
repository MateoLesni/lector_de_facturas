from mistralai import Mistral

client = Mistral(api_key="6KFGSjbO7hEFxnJIwUMrQ8Fzm9j6Pgsp")

def traer_texto_png(file_id):
    public_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    try:
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "image_url",
                "image_url": public_url
            },
            include_image_base64=False
        )

        # ✅ IMPORTANTE: recorrer las páginas y concatenar markdown
        if hasattr(ocr_response, "pages"):
            texto_paginas = [page.markdown for page in ocr_response.pages]
            return "\n\n".join(texto_paginas).strip()
        else:
            print("⚠️ OCR no devolvió páginas.")
            return ""

    except Exception as e:
        print(f"❌ Error en OCR de Mistral: {e}")
        return ""
