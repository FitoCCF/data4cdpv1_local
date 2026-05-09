import pandas as pd
import psycopg2
import numpy as np
import os

def update_assays_from_csv(csv_path: str, db_config: dict):
    # 1. Conectar a la base de datos PostgreSQL usando el diccionario de credenciales
    conn = psycopg2.connect(**db_config)
    # Creamos el cursor para poder ejecutar comandos SQL
    cursor = conn.cursor()

    try:
        # 2. Leer el archivo CSV completo en memoria utilizando la librería pandas
        df = pd.read_csv(csv_path)
        
        # 3. Limpiar espacios en blanco al principio y al final de MUESTRA y CODIGO_MUESTRA
        df['MUESTRA'] = df['MUESTRA'].astype(str).str.strip()
        df['CODIGO_MUESTRA'] = df['CODIGO_MUESTRA'].astype(str).str.strip()

        # 4. Corregir formato de horas (ej. cambiar un punto '11.06' a dos puntos '11:06')
        df['time'] = df['time'].astype(str).str.replace('.', ':')
        
        # 5. Parsear la hora para extraerla estrictamente en formato HH:MM (ignorando los segundos)
        df['time_hhmm'] = pd.to_datetime(df['time'], format='mixed').dt.strftime('%H:%M')
        
        # 6. Parsear la fecha para asegurar que siempre use el formato estándar de base de datos AAAA-MM-DD
        df['date'] = pd.to_datetime(df['date'], format='mixed').dt.strftime('%Y-%m-%d')

        # 7. Reemplazar valores vacíos (NaN) del CSV por "None" para que se inserten como NULL reales en PostgreSQL
        df = df.replace({np.nan: None})

        # Inicializamos listas para agrupar las filas que tienen éxito y las que fallan
        success_rows = []
        failed_rows = []
        # Inicializamos el contador visual de cuántos registros logramos actualizar
        updated_count = 0
        
        # Tupla restrictiva que solo permite consultar estos identificadores en la tabla sample
        ids_permitidos = (17, 18, 19, 20, 21, 22, 23, 24, 25, 26)

        # 8. Bucle principal que recorrerá una a una cada fila del dataframe de pandas
        for _, row in df.iterrows():
            
            # PASO 1: Leer los datos clave (fecha, hora, muestra, código) de la fila actual del CSV
            csv_date = row['date']
            csv_time = row['time_hhmm']
            csv_muestra = str(row['MUESTRA']).strip()
            csv_codigo = str(row['CODIGO_MUESTRA']).strip()
            
            # PASO 2: Buscar en la base de datos (works4cdp_assay) si existe un ensayo que coincida con esa fecha y hora, permitiendo solo los sample_ids de la tupla
            query_buscar_fecha_hora = """
                SELECT a.id, s.name, s.tag 
                FROM works4cdp_assay a
                JOIN works4cdp_sample s ON a.sample_id = s.id
                WHERE a.date = %s AND to_char(a.time, 'HH24:MI') = %s AND a.sample_id IN %s;
            """
            cursor.execute(query_buscar_fecha_hora, (csv_date, csv_time, ids_permitidos))
            ensayos_encontrados = cursor.fetchall()
            
            # Si no devolvió nada, entonces sabemos que falló en el primer paso (No hay fecha/hora)
            if not ensayos_encontrados:
                # Hacemos una copia de la fila original para no alterar el dataframe madre
                fila_fallida = row.copy()
                # Agregamos la nueva columna indicando que la hora, fecha o el ID son los culpables
                fila_fallida['motivo_error'] = f"Fallo Fecha/Hora/ID: No existe ensayo válido (IDs 17-26) el {csv_date} a las {csv_time}."
                # Se añade a la lista de registros fallidos y saltamos a procesar la siguiente fila
                failed_rows.append(fila_fallida)
                continue
            
            # Creamos una bandera (flag) para registrar si logramos el éxito en esta fila
            fue_actualizado = False
            # Lista de apoyo para guardar el diagnóstico de qué muestras sí estaban en esa hora
            diagnostico_muestras = []
            
            # PASO 3: De los ensayos encontrados a esa hora, vamos a verificar el valor de la muestra
            for assay_id, db_name, db_tag in ensayos_encontrados:
                
                # Limpiamos espacios del nombre y tag que nos devolvió la base de datos
                db_muestra_nombre = str(db_name).strip()
                db_muestra_codigo = str(db_tag).strip()
                
                # PASO 4: Comparamos el nombre y código de la BD contra los del archivo CSV
                if db_muestra_nombre == csv_muestra and db_muestra_codigo == csv_codigo:
                        
                        # Si son idénticos, PASO 5: preparamos el SQL de actualización con el assay_id exacto
                        update_query = """
                            UPDATE works4cdp_assay
                            SET 
                                tara = %s, tweight = %s, dweight = %s, pweight = %s,
                                chemical_id = %s, "pFe" = %s, "pCu" = %s, "pZn" = %s,
                                "pMo" = %s, "pIns" = %s, "pSol" = %s
                            WHERE id = %s;
                        """
                        
                        # Empaquetamos los valores exactos requeridos de la fila en orden
                        valores_actualizacion = (
                            row['tara'], row['tweight'], row['dweight'], row['pweight'],
                            row['chemical_id'], row['%Fe'], row['%Cu'], row['%Zn'],
                            row['%Mo'], row['%Ins'], row['pSol'], 
                            assay_id # Le damos el ID real obtenido del SELECT inicial
                        )
                        
                        # Ejecutamos el comando UPDATE en la base de datos
                        cursor.execute(update_query, valores_actualizacion)
                        
                        # Sumamos 1 al contador global de actualizaciones exitosas
                        updated_count += 1
                        # Marcamos la bandera como Verdadera
                        fue_actualizado = True
                        
                        # Copiamos la fila para el archivo de éxitos
                        fila_exitosa = row.copy()
                        # Removemos el motivo de error si es que se reprocesaba
                        if 'motivo_error' in fila_exitosa:
                            del fila_exitosa['motivo_error']
                        # Se guarda en la lista de éxitos
                        success_rows.append(fila_exitosa)
                        
                        # Terminamos este bucle 'for' ya que logramos encontrar la muestra correcta
                        break
                else:
                    # Si el nombre no coincidía, guardamos en la memoria qué nombre tenía para el reporte final
                    diagnostico_muestras.append(f"{db_muestra_nombre} [{db_muestra_codigo}]")
            
            # PASO 6: Si al finalizar de revisar todos los ensayos de esa hora no se actualizó nada...
            if not fue_actualizado:
                # Clonamos la fila original
                fila_fallida = row.copy()
                # Escribimos un mensaje con el contexto de qué falló (la Muestra / El Código)
                if diagnostico_muestras:
                    fila_fallida['motivo_error'] = f"Fallo Muestra/Código: A esa hora existen las muestras {diagnostico_muestras}, pero no '{csv_muestra}' ['{csv_codigo}']."
                else:
                    fila_fallida['motivo_error'] = "Fallo Muestra/Código: La muestra del CSV no coincide con las registradas a esta hora."
                # Agregamos esta fila al contenedor de fallidos
                failed_rows.append(fila_fallida)

        # 9. Confirmar todos los cambios (si no hubo errores en el ciclo, se aplica el commit masivo)
        conn.commit()
        # Imprimimos el log en la consola
        print(f"Proceso finalizado. Se actualizaron exitosamente {updated_count} registros en works4cdp_assay.")

        # 10. Dividir las rutas para preparar los nombres de los nuevos CSVs
        base_path, ext = os.path.splitext(csv_path)
        success_csv_path = f"{base_path}_exitosos{ext}"
        failed_csv_path = f"{base_path}_fallidos{ext}"
        
        # Exportar las filas que se lograron inyectar
        if success_rows:
            pd.DataFrame(success_rows).to_csv(success_csv_path, index=False)
            print(f"Archivo de éxitos generado: {success_csv_path}")
        
        # Exportar las filas que no lograron inyectarse
        if failed_rows:
            pd.DataFrame(failed_rows).to_csv(failed_csv_path, index=False)
            print(f"Archivo de fallos generado: {failed_csv_path}")

    except Exception as e:
        # Si en cualquier punto hubo un fallo de ejecución en la base de datos (e.g. timeout), deshacer.
        conn.rollback()
        print(f"Error crítico durante la actualización: {e}")
    finally:
        # Garantizar cerrar las conexiones y cursores para no saturar memoria en PostgreSQL
        cursor.close()
        conn.close()

if __name__ == "__main__":
    CSV_PATH = "/home/fito/Proyects/data4cdpv1_local/data/processed/data_cobre_c2v3.csv"
    
    DB_CONFIG = {
        "dbname": "mydb",
        "user": "myuser",
        "password": "mypassword",
        "host": "localhost",
        "port": 5432
    }
    
    update_assays_from_csv(CSV_PATH, DB_CONFIG)
