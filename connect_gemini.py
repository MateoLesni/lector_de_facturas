from google.generativeai import configure, GenerativeModel

# Configurar API Key de Gemini
configure(api_key="AIzaSyD2Lb7u_x68AVNMskV_rrqjXl5mEwX1uH0")

# Modelo a utilizar
model = GenerativeModel("models/gemini-1.5-flash-latest")

# Función para estructurar con OCRIA
def estructurar_con_prompt_especifico(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error en estructurar_con_prompt_especifico(ocria): {e}")
        return ""

# Función para estructurar con IMGIA (imagen directa)
def estructurar_con_prompt_imgia(prompt, image):
    try:
        response = model.generate_content([prompt, image])
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error al generar contenido con Gemini: {e}")
        return None

