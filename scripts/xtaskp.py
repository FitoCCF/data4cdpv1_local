from contextlib import nullcontext

import psycopg2
from datetime import datetime
from taskpx import insert_task

# Conexión a la base de datos PostgreSQL
connection = psycopg2.connect(
    host="localhost",
    database="mydb",
    user="myuser",
    password="mypassword",
    port=5433
)
cursor = connection.cursor()

# Consulta para obtener las tareas
query = """
    SELECT id, frequency, start_date
    FROM works4cdp_task
    WHERE id>99 order by id
"""
cursor.execute(query)
tasks = cursor.fetchall()
print(tasks)


# Fecha de inicio a partir de la cual se van a procesar las tareas matemáticamente
process_start_date = "2026-04-06"
end_date = "2026-04-12"
user = 1
state = 2

records_to_insert = []

for task_id, frequency, start_date in tasks:
    #print(task_id, frequency, start_date)
    if frequency is None or frequency == '' or frequency == '999':
        continue  # Saltar si la frecuencia es 999

    #turn = "B" if task_id in tasks_with_turn_b else "A"
    formatted_start_date = start_date.strftime("%Y-%m-%d")

    # Insertar la tarea enviando la nueva variable de inicio del proceso
    records = insert_task(formatted_start_date, end_date, int(frequency), user, state, task_id, process_start_date)
    records_to_insert.extend(records)

# Insertar registros en la base de datos
insert_query = """
    INSERT INTO works4cdp_taskp (
        year, week, day, date, estado_id, task_id,
        rescheduled, is_permanent_reschedule, priority
    ) VALUES (%s, %s, %s, %s, %s, %s, False, False, 1)
"""
cursor.executemany(insert_query, records_to_insert)
connection.commit()

print(f"{len(records_to_insert)} registros insertados correctamente en works4cdp_taskp.")

cursor.close()
connection.close()
