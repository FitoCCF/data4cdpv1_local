import psycopg2

# Configura aquí las credenciales para conectarte a tu base de datos expuesta fuera del contenedor
DB_HOST = "localhost"  # O la IP/host de tu servidor de BD
DB_PORT = "5433"
DB_NAME = "mydb"
DB_USER = "myuser"
DB_PASSWORD = "mypassword"


def poblar_task_group_assignment():
    try:
        # 1. Establecer conexión con la base de datos
        conexion = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conexion.cursor()

        # 2. Consulta SQL para insertar registros cruzando las tablas.
        # Condición 1: Que coincida la fecha de TaskP con la fecha de Calendar.
        # Condición 2: Que coincida el turno de Task con el turno de Calendar.
        # Condición 3: Que el calendario esté asignado a un grupo (group_id IS NOT NULL).
        # Condición 4: NOT EXISTS para evitar insertar duplicados.
        sql_query = """
                    INSERT INTO works4cdp_taskgroupassignment (taskp_id, calendar_id)
                    SELECT tp.id, c.id
                    FROM works4cdp_taskp tp
                             JOIN works4cdp_task t ON tp.task_id = t.id
                             JOIN works4cdp_calendar c ON tp.date = c.date AND t.turn = c.turn
                    WHERE c.group_id IS NOT NULL
                      AND NOT EXISTS (SELECT 1 \
                                      FROM works4cdp_taskgroupassignment tga \
                                      WHERE tga.taskp_id = tp.id \
                                        AND tga.calendar_id = c.id); \
                    """

        # 3. Ejecutar la consulta
        cursor.execute(sql_query)

        # Obtener la cantidad de filas insertadas
        filas_insertadas = cursor.rowcount

        # 4. Confirmar los cambios en la base de datos
        conexion.commit()

        print(f"Proceso completado exitosamente.")
        print(f"Se insertaron {filas_insertadas} nuevos registros en TaskGroupAssignment.")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error al conectar o ejecutar la consulta: {error}")
        if conexion:
            conexion.rollback()

    finally:
        # 5. Cerrar la conexión
        if conexion:
            cursor.close()
            conexion.close()
            print("Conexión a la base de datos cerrada.")


if __name__ == "__main__":
    poblar_task_group_assignment()