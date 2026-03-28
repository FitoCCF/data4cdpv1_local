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

sdate = "2026-03-23"
end_date = "2026-03-23"
user = 1
state = 2

records_to_insert = []

for task_id, frequency, start_date in tasks:
    #print(task_id, frequency, start_date)
    if frequency is None or frequency == '' or frequency == '999':
        continue  # Saltar si la frecuencia es 999

    #turn = "B" if task_id in tasks_with_turn_b else "A"
    formatted_start_date = start_date.strftime("%Y-%m-%d")

    # Insertar la tarea con la función insert_task
    records = insert_task(formatted_start_date, end_date, int(frequency), state, task_id, sdate)
    records_to_insert.extend(records)

# Insertar registros en la base de datos
insert_query = """
    INSERT INTO works4cdp_taskp (
        year, week, day, date, rescheduled, reschedule_reason,
        reschedule_date, reschedule_user_id, estado_id, task_id
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
cursor.executemany(insert_query, records_to_insert)
connection.commit()

print(f"{len(records_to_insert)} registros insertados correctamente en works4cdp_taskp.")

cursor.close()
connection.close()