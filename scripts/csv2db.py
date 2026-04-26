
import pandas as pd
import psycopg2
import numpy as np

def update_assays_from_csv(csv_path: str, db_config: dict):
    """
    Actualiza la tabla 'works4cdp_assay' con datos del CSV.
    Ignora los segundos en el cruce de la hora y busca el sample_id en base 
    a la combinación de MUESTRA y CODIGO_MUESTRA.
    """
    # 1. Conectar a la base de datos de PostgreSQL (expuesta por el contenedor data4cdpv1-backend-1)
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()

    try:
        # 2. Obtener el mapeo de (name, tag) -> id del modelo Sample
        # Django genera la tabla con el nombre appname_modelname (works4cdp_sample)
        cursor.execute("SELECT id, name, tag FROM works4cdp_sample;")
        samples = cursor.fetchall()
        
        # Diccionario para buscar sample_id rápidamente: {(MUESTRA, CODIGO_MUESTRA): id}
        sample_map = {(name, tag): sample_id for sample_id, name, tag in samples}

        # 3. Leer el CSV con Pandas
        df = pd.read_csv(csv_path)
        
        # 4. Limpieza y procesamiento de Fechas y Horas
        # Reemplazamos puntos por dos puntos por si hay horas con formato erróneo (Ej: '11.06')
        df['time'] = df['time'].astype(str).str.replace('.', ':')
        
        # Parseamos la hora y extraemos explícitamente el formato HH:MM (ignorando segundos)
        df['time_hhmm'] = pd.to_datetime(df['time'], format='mixed').dt.strftime('%H:%M')
        
        # Aseguramos el formato de la fecha en YYYY-MM-DD
        df['date'] = pd.to_datetime(df['date'], format='mixed').dt.strftime('%Y-%m-%d')

        # Reemplazar NaN con None para que psycopg2 lo inyecte como NULL en PostgreSQL
        df = df.replace({np.nan: None})

        # 5. Consulta SQL paramétrica para actualizar
        # Nota: En PostgreSQL, los nombres de campo con mayúsculas generados por Django (pFe) 
        # deben ir entre comillas dobles ("pFe") para evitar que la base de datos los pase a minúsculas.
        update_query = """
            UPDATE works4cdp_assay
            SET 
                tara = %s,
                tweight = %s,
                dweight = %s,
                pweight = %s,
                chemical_id = %s,
                "pFe" = %s,
                "pCu" = %s,
                "pZn" = %s,
                "pMo" = %s,
                "pIns" = %s,
                "pSol" = %s
            WHERE 
                date = %s 
                AND to_char(time, 'HH24:MI') = %s -- Ignora segundos en la BD ('15:23:00' -> '15:23')
                AND sample_id = %s;
        """

        updated_count = 0

        # 6. Iterar sobre el DataFrame y ejecutar los updates
        for _, row in df.iterrows():
            # Buscar el ID de la muestra combinando columnas del CSV
            muestra_key = (row['MUESTRA'], row['CODIGO_MUESTRA'])
            sample_id = sample_map.get(muestra_key)

            if not sample_id:
                print(f"Advertencia: No se encontró Sample {muestra_key} en la BD. Omitiendo fila de fecha {row['date']}.")
                continue

            # Valores a inyectar en la consulta (en el mismo orden que los %s)
            values = (
                # Valores del SET
                row['tara'],
                row['tweight'],
                row['dweight'],
                row['pweight'],
                row['chemical_id'],
                row['%Fe'],
                row['%Cu'],
                row['%Zn'],
                row['%Mo'],
                row['%Ins'],
                row['pSol'],
                
                # Valores del WHERE
                row['date'],
                row['time_hhmm'], 
                sample_id
            )

            cursor.execute(update_query, values)
            updated_count += cursor.rowcount # Sumamos 1 si encontró coincidencia, 0 si no

        # 7. Confirmar cambios
        conn.commit()
        print(f"Proceso finalizado. Se actualizaron {updated_count} registros en works4cdp_assay.")

    except Exception as e:
        conn.rollback() # Revertir si hay un error fatal
        print(f"Error crítico durante la actualización: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    # Ruta al archivo (relativa a donde se ejecute el script)
    CSV_PATH = "/home/fito/Proyects/data4cdpv1_local/data/processed/data_cobre_c2v3.csv"
    
    # Credenciales de base de datos
    # Como corre fuera de Django y backend corre en contenedor, apunta a 'localhost' 
    # o a la IP local expuesta del servicio postgres de tu docker-compose.
    DB_CONFIG = {
        "dbname": "mydb",   # Reemplazar con el nombre real de tu base de datos
        "user": "myuser",           # Reemplazar con tu user de postgres
        "password": "mypassword",      # Reemplazar con tu contraseña de postgres
        "host": "localhost",            # IP local expuesta en tu host
        "port": 5432                    # Puerto local mapeado al contenedor
    }
    
    update_assays_from_csv(CSV_PATH, DB_CONFIG)
