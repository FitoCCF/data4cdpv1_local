import psycopg2
from datetime import datetime, timedelta

def calcular_semana_extendida(fecha):
    """Calcula un número de semana continuo desde el año 1963."""
    anio_iso = fecha.isocalendar()[0]
    semana_iso_actual = fecha.isocalendar()[1]
    return semana_iso_actual + 6 + ((anio_iso - 1963) * 52)

def calcular_fechas_tarea(fecha_inicio_texto, fecha_fin_texto, frecuencia_en_dias):
    """Calcula las fechas de ejecución saltando domingos."""
    try:
        fecha_inicio_convertida = datetime.strptime(fecha_inicio_texto, "%Y-%m-%d").date()
        fecha_fin_convertida = datetime.strptime(fecha_fin_texto, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        if hasattr(fecha_inicio_texto, 'date'):
            fecha_inicio_convertida = fecha_inicio_texto.date()
        elif hasattr(fecha_inicio_texto, 'year'):
            fecha_inicio_convertida = fecha_inicio_texto
        else:
            fecha_inicio_convertida = datetime.strptime(str(fecha_inicio_texto), "%Y-%m-%d").date()

        if hasattr(fecha_fin_texto, 'date'):
            fecha_fin_convertida = fecha_fin_texto.date()
        elif hasattr(fecha_fin_texto, 'year'):
            fecha_fin_convertida = fecha_fin_texto
        else:
            fecha_fin_convertida = datetime.strptime(str(fecha_fin_texto), "%Y-%m-%d").date()

    if fecha_inicio_convertida > fecha_fin_convertida or not frecuencia_en_dias:
        return []

    lista_fechas_calculadas = []
    fecha_puntero_actual = fecha_inicio_convertida

    while fecha_puntero_actual <= fecha_fin_convertida:
        if frecuencia_en_dias < 7:
            if (fecha_puntero_actual.weekday() != 6) and ((fecha_puntero_actual.weekday() - fecha_inicio_convertida.weekday()) % frecuencia_en_dias == 0):
                lista_fechas_calculadas.append(fecha_puntero_actual.strftime("%Y-%m-%d"))
                fecha_puntero_actual += timedelta(days=1)
            else:
                fecha_puntero_actual += timedelta(days=1)
        else:
            if frecuencia_en_dias % 7 == 0:
                lista_fechas_calculadas.append(fecha_puntero_actual.strftime("%Y-%m-%d"))
                fecha_puntero_actual += timedelta(days=frecuencia_en_dias)
            else:
                if (fecha_puntero_actual.weekday() != 6) and ((fecha_puntero_actual - fecha_inicio_convertida).days % frecuencia_en_dias == 0):
                    lista_fechas_calculadas.append(fecha_puntero_actual.strftime("%Y-%m-%d"))
                fecha_puntero_actual += timedelta(days=1)

    return lista_fechas_calculadas

if __name__ == "__main__":
    # Configuración de conexión
    conexion_hacia_postgresql = psycopg2.connect(
        host="localhost",
        database="mydb",
        user="myuser",
        password="mypassword",
        port=5433
    )
    cursor_bd = conexion_hacia_postgresql.cursor()

    tope_fecha_limite_simulacion = "2027-01-03"

    # PASO 1. Extracción de tareas maestras
    consulta_extraccion_tareas = """
        SELECT id, frequency, start_date, turn
        FROM works4cdp_task
        WHERE id > 99 ORDER BY id
    """
    cursor_bd.execute(consulta_extraccion_tareas)
    lista_de_todas_las_tareas_halladas = cursor_bd.fetchall()

    bolsa_de_asignaciones_listas = []
    
    # MODIFICACIÓN ANALÍTICA: Estructura para identificar tareas sin calendario
    registro_tareas_huerfanas = [] 

    for id_de_la_tarea, cadena_frecuencia_tarea, fecha_partida_tarea, turno_tarea in lista_de_todas_las_tareas_halladas:

        if cadena_frecuencia_tarea in [None, '', '999']:
            continue
        
        frecuencia_numerica_tarea = int(cadena_frecuencia_tarea)

        if fecha_partida_tarea is None:
            continue

        # PASO 2. Cálculo de fechas proyectadas
        lista_con_dias_donde_cae_esta_tarea = calcular_fechas_tarea(fecha_partida_tarea, tope_fecha_limite_simulacion, frecuencia_numerica_tarea)

        # Mapeo de turnos
        turno_buscado = 'N' if turno_tarea == 'B' else 'D'

        for dia_de_aplicacion_especifico in lista_con_dias_donde_cae_esta_tarea:
            # PASO 3. Inserción en TaskP (Evento programado)
            fecha_obj = datetime.strptime(dia_de_aplicacion_especifico, "%Y-%m-%d")
            semana_calculada = calcular_semana_extendida(fecha_obj)
            dia_letra = fecha_obj.strftime("%A")

            comando_insertar_taskp = """
                INSERT INTO works4cdp_taskp (
                    task_id, year, week, day, date,
                    rescheduled, is_permanent_reschedule,
                    estado_id, priority
                ) VALUES (%s, %s, %s, %s, %s, False, False, 1, 1) RETURNING id
            """

            cursor_bd.execute(comando_insertar_taskp, (
                id_de_la_tarea, fecha_obj.year, semana_calculada, dia_letra, dia_de_aplicacion_especifico
            ))
            id_nuevo_evento_taskp = cursor_bd.fetchone()[0]

            # PASO 4. Cruce con Calendario Humano
            comando_busca_id_calendario_ideal = """
                SELECT id FROM works4cdp_calendar
                WHERE date = %s AND turn = %s
            """
            cursor_bd.execute(comando_busca_id_calendario_ideal, (dia_de_aplicacion_especifico, turno_buscado))
            resultados_calendario = cursor_bd.fetchall()

            if resultados_calendario:
                for fila in resultados_calendario:
                    id_confirmado_del_calendario = fila[0]
                    bolsa_de_asignaciones_listas.append((id_nuevo_evento_taskp, id_confirmado_del_calendario))
            else:
                # IDENTIFICACIÓN: Guardamos la tarea que no encontró personal
                registro_tareas_huerfanas.append({
                    'id_taskp': id_nuevo_evento_taskp,
                    'id_original': id_de_la_tarea,
                    'fecha': dia_de_aplicacion_especifico,
                    'turno': turno_buscado
                })

    # PASO 5. Inyección masiva y Reporte
    if bolsa_de_asignaciones_listas:
        consulta_inyeccion_final_para_esquema = """
            INSERT INTO works4cdp_taskgroupassignment (taskp_id, calendar_id)
            VALUES (%s, %s)
        """
        try:
            cursor_bd.executemany(consulta_inyeccion_final_para_esquema, bolsa_de_asignaciones_listas)
            conexion_hacia_postgresql.commit()
            
            print(f"--- PROCESO FINALIZADO ---")
            print(f"Asignaciones exitosas: {len(bolsa_de_asignaciones_listas)}")

            if registro_tareas_huerfanas:
                print(f"\n[ALERTA] Se detectaron {len(registro_tareas_huerfanas)} tareas huérfanas en TaskP:")
                print(f"{'ID_TASKP':<10} | {'ID_ORIGINAL':<12} | {'FECHA':<12} | {'TURNO'}")
                print("-" * 55)
                for h in registro_tareas_huerfanas:
                    print(f"{h['id_taskp']:<10} | {h['id_original']:<12} | {h['fecha']:<12} | {h['turno']}")
                print("-" * 55)

        except Exception as error_capturado_de_base:
            conexion_hacia_postgresql.rollback()
            print(f"Error crítico en la base de datos: {error_capturado_de_base}")
    else:
        print("No se generaron asignaciones. Revisa la compatibilidad de fechas y turnos.")

    cursor_bd.close()
    conexion_hacia_postgresql.close()
