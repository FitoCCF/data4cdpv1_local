import nbformat as nbf
import sys

try:
    notebook_path = '/home/fito/Proyects/data4cdpv1_local/notebooks/assay2db.ipynb'
    nb = nbf.read(notebook_path, as_version=4)

    # Define cells
    cell1 = nbf.v4.new_markdown_cell("### Paso 1: Importar librerías y configurar conexión\nBasado en `csv2db.py`, configuramos la conexión a la base de datos e importamos pandas.")
    cell2 = nbf.v4.new_code_cell("""import pandas as pd
import psycopg2
import numpy as np

# Configuración de base de datos (Asegúrate de cambiar por tus credenciales reales si difieren)
DB_CONFIG = {
    "dbname": "mydb",
    "user": "myuser",
    "password": "mypassword",
    "host": "localhost",
    "port": 5432
}

# Conectar a la base de datos PostgreSQL
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()
print("Conexión establecida.")""")

    cell3 = nbf.v4.new_markdown_cell("### Paso 2: Leer solo la primera línea de `data1.csv`\nUtilizamos `nrows=1` para leer únicamente la primera línea con datos. Adaptamos las columnas al formato de `csv2db.py`.")

    cell4 = nbf.v4.new_code_cell("""# Leer el archivo CSV limitando a 1 fila
csv_path = '../data/raw/data1.csv'
df = pd.read_csv(csv_path, nrows=1)

# Limpiar nombres de columnas (quitar espacios sobrantes)
df.columns = df.columns.str.strip()

# Limpiar espacios en los datos
df['MUESTRA'] = df['MUESTRA'].astype(str).str.strip()
df['CODLAB'] = df['CODLAB'].astype(str).str.strip()

# Formatear la hora y fecha
df['time_hhmm'] = pd.to_datetime(df['Hora'].astype(str).str.replace('.', ':'), format='mixed').dt.strftime('%H:%M')
df['date'] = pd.to_datetime(df['Fecha'], format='mixed').dt.strftime('%Y-%m-%d')

# Reemplazar NaN por None
df = df.replace({np.nan: None})

# Extraer la fila
row = df.iloc[0]
display(row)""")

    cell5 = nbf.v4.new_markdown_cell("### Paso 3: Buscar en la base de datos el ensayo correspondiente\nFiltramos por `date`, `time_hhmm` y los `sample_id` permitidos.")

    cell6 = nbf.v4.new_code_cell("""# Extraer datos clave de la fila
csv_date = row['date']
csv_time = row['time_hhmm']
csv_muestra = str(row['MUESTRA']).strip()
csv_codigo = str(row['CODLAB']).strip()

ids_permitidos = (17, 18, 19, 20, 21, 22, 23, 24, 25, 26)

# Buscar en works4cdp_assay
query_buscar_fecha_hora = "SELECT id, sample_id FROM works4cdp_assay WHERE date = %s AND to_char(time, 'HH24:MI') = %s AND sample_id IN %s;"
cursor.execute(query_buscar_fecha_hora, (csv_date, csv_time, ids_permitidos))
ensayos_encontrados = cursor.fetchall()

print(f"Ensayos encontrados a las {csv_time} del {csv_date}: {ensayos_encontrados}")""")

    cell7 = nbf.v4.new_markdown_cell("### Paso 4: Validar la muestra y ejecutar la inserción/actualización\nValidamos el nombre y código de la muestra. Si coincide, realizamos el UPDATE al igual que `csv2db.py`. Note que `data1.csv` tiene diferentes nombres de columnas que mapear.")

    cell8 = nbf.v4.new_code_cell("""fue_actualizado = False

for assay_id, sample_id in ensayos_encontrados:
    query_buscar_muestra = "SELECT name, tag FROM works4cdp_sample WHERE id = %s;"
    cursor.execute(query_buscar_muestra, (sample_id,))
    datos_muestra_bd = cursor.fetchone()
    
    if datos_muestra_bd:
        db_muestra_nombre = str(datos_muestra_bd[0]).strip()
        db_muestra_codigo = str(datos_muestra_bd[1]).strip()
        
        # Validar coincidencia (CODLAB hace de CODIGO_MUESTRA)
        if db_muestra_nombre == csv_muestra and db_muestra_codigo == csv_codigo:
            print(f"¡Coincidencia! Preparando UPDATE para ID Assay: {assay_id}")
            
            # Query ajustada a las columnas disponibles en data1.csv (se omite chemical_id ya que no está)
            update_query = \"\"\"
                UPDATE works4cdp_assay
                SET 
                    tara = %s, tweight = %s, dweight = %s, pweight = %s,
                    "pFe" = %s, "pCu" = %s, "pZn" = %s,
                    "pMo" = %s, "pIns" = %s, "pSol" = %s
                WHERE id = %s;
            \"\"\"
            
            valores_actualizacion = (
                row['Tara'], row['PESOTOTAL'], row['PESOSECO'], row['PESOPULPA'],
                row['%Fe'], row['%Cu'], row['%Zn'],
                row['%Mo'], row['%Ins'], row['%Sol'], 
                assay_id
            )
            
            try:
                # cursor.execute(update_query, valores_actualizacion) # Descomentar para ejecutar
                print("Ejecución SQL preparada con éxito.")
                fue_actualizado = True
                
                # conn.commit()
                break
            except Exception as e:
                print(f"Error en BD: {e}")
                conn.rollback()

if not fue_actualizado:
    print("No se encontró coincidencia o no se pudo actualizar.")

# cursor.close()
# conn.close()""")

    nb.cells.extend([cell1, cell2, cell3, cell4, cell5, cell6, cell7, cell8])
    nbf.write(nb, notebook_path)
    print("Celdas generadas con exito.")
except Exception as e:
    print(f"Error: {e}")
