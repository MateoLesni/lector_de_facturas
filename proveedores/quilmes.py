import pandas as pd
from collections import defaultdict

def limpiar_numero(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return valor

    try:
        valor = valor.strip()

        # Si contiene coma y no punto: europeo (ej. 3660,00)
        if "," in valor and "." not in valor:
            valor = valor.replace(",", ".")
        # Si contiene punto y coma: 1.234,56 → 1234.56
        elif "," in valor and "." in valor:
            valor = valor.replace(".", "").replace(",", ".")

        return float(valor)

    except Exception as e:
        print(f"⚠️ Error limpiando número '{valor}': {e}")
        return None


def procesar(document, nombre_archivo):
    """
    Procesa un objeto Document AI y devuelve un DataFrame limpio y listo para exportar.
    """
    column_entities = defaultdict(list)

    def get_y_position(entity):
        try:
            return min(v.y for v in entity.page_anchor.page_refs[0].bounding_poly.normalized_vertices)
        except:
            return 0.0

    for entity in document.entities:
        y = get_y_position(entity)
        column_entities[entity.type_].append((y, entity.mention_text))

    for field in column_entities:
        column_entities[field].sort(key=lambda x: x[0])

    max_len = max((len(v) for v in column_entities.values()), default=0)
    rows = []

    for i in range(max_len):
        row = {}
        for field, values in column_entities.items():
            row[field] = values[i][1] if i < len(values) else None
        rows.append(row)

    df = pd.DataFrame(rows)

    print("\n📋 DataFrame original:")
    print(df)

    # Limpiar valores numéricos
    for col in ["Cantidad", "Total"]:
        if col in df.columns:
            df[col] = df[col].apply(limpiar_numero)

    # Convertir cantidad a valor absoluto
    if "Cantidad" in df.columns:
        df["Cantidad"] = df["Cantidad"].apply(lambda x: abs(x) if pd.notnull(x) else None)

    print("\n🧼 DataFrame después de limpiar 'Cantidad' y 'Total':")
    print(df)

    # Agregar columnas faltantes
    partes = nombre_archivo.split(" - ")
    local = partes[2].strip() if len(partes) > 2 else "Desconocido"

    df["Local"] = local
    df["Proveedor"] = "Quilmes"

    columnas_requeridas = ["Codigo", "Producto", "Cantidad", "Precio", "Total", "Local", "Proveedor"]
    for col in columnas_requeridas:
        if col not in df.columns:
            df[col] = "" if col in ["Codigo", "Producto", "Local", "Proveedor"] else 0

    # Calcular Precio (aunque la columna exista)
    if "Total" in df.columns and "Cantidad" in df.columns:
        df["Precio"] = df.apply(
            lambda row: round(row["Total"] / row["Cantidad"], 2)
            if pd.notnull(row["Cantidad"]) and row["Cantidad"] != 0 and pd.notnull(row["Total"]) else 0,
            axis=1
        )

    # Convertir numéricos a string con coma decimal para exportar a Excel (estilo latino)
    for col in ["Cantidad", "Total", "Precio"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{x:.2f}".replace(".", ",") if pd.notnull(x) else "")

    # Reordenar columnas
    df = df[columnas_requeridas]

    print("\n✅ DataFrame final estructurado:")
    print(df)

    return df
