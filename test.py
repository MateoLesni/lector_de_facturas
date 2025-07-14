import pandas as pd
import importlib

# Importar el módulo
entre_amigos = importlib.import_module("proveedores.entre_amigos")

# Probar la función
valores = ["21.4", "15", "11.6", "12,242.00", "7.000"]
for v in valores:
    print(f"{v} → {entre_amigos.normalizar_numero(v)}")
