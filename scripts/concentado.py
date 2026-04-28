import pandas as pd

# Ruta del archivo CSV
csv_path = "/home/daigo/data4cdpv1_local/data/processed/data_cobre_c2v3_fallidos.csv"

# Leer el archivo CSV
df = pd.read_csv(csv_path)

# Filtrar las filas donde la columna 'MUESTRA' es 'Concentrado Colectivo'
df_filtrado = df[df['MUESTRA'] == 'Concentrado Colectivo']

# Mostrar las primeras filas del resultado
print(df_filtrado.head())

# Opcional: Si deseas guardar este resultado en un nuevo archivo CSV
nuevo_csv_path = "/home/daigo/data4cdpv1_local/data/processed/concentrado_colectivo_fallidos.csv"
df_filtrado.to_csv(nuevo_csv_path, index=False)
print(f"\nDatos filtrados guardados en: {nuevo_csv_path}")
