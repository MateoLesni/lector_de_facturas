from google.generativeai import configure, GenerativeModel
import os


configure(api_key="AIzaSyD2Lb7u_x68AVNMskV_rrqjXl5mEwX1uH0")
model = GenerativeModel("models/gemini-1.5-flash-latest")

def estructurar_con_prompt_especifico(prompt):
    response = model.generate_content(prompt)
    return response.text.strip()
