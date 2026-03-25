import psycopg2
from taskpx import insert_task

# Configuración de conexión
db_config = {
    "host": "localhost",
    "database": "mydb",
    "user": "myuser",
    "password": "mypassword",
    "port": 5433
}

try:
    connection = psycopg2.connect(**db_config)
    cursor = connection.cursor()

    # 1. Obtener ID del estado 'Pendiente' u obtener el 1 por defecto
    # Asumimos que ID 1 = Pendiente (P)
    state_p_id = 2 
    
    # 2. Obtener tareas base
    query = """
        SELECT id, frequency, start_date, turn 
        FROM works4cdp_task 
        WHERE frequency IS NOT NULL
          AND frequency != ''
          AND frequency != '999'
        ORDER BY id
    """
    cursor.execute(query)
    tasks = cursor.fetchall()

    end_date = "2026-12-31"
    records_to_insert = []

    for task_id, frequency, start_date, turn in tasks:
        if not start_date:
            continue
            
        formatted_start_date = start_date.strftime("%Y-%m-%d")
        
        # El campo 'turn' de Task se puede usar para asignar un group_id inicial si existe
        # Por ahora enviamos None o un ID fijo si tienes grupos creados
        group_id = None 

        # Generar registros
        records = insert_task(formatted_start_date, end_date, int(frequency), group_id, state_p_id, task_id)
        records_to_insert.extend(records)

    # 3. Insert Query ajustada a los campos del models.py
    # NOTA: Se omiten campos nullables como comments, reschedule_reason, etc.
    insert_query = """
        INSERT INTO works4cdp_taskp (
            task_id, year, week, day, date, estado_id, 
            rescheduled, group_id, is_permanent_reschedule, priority
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    print(f"Insertando {len(records_to_insert)} registros...")
    
    # Ejecución por lotes para mayor eficiencia
    cursor.executemany(insert_query, records_to_insert)
    connection.commit()

    print("Inserción completada exitosamente.")

except Exception as error:
    print(f"Error: {error}")
finally:
    if connection:
        cursor.close()
        connection.close()
