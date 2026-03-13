# Importamos la librería psycopg2 que actúa como puente de conexión entre Python y PostgreSQL
import psycopg2
# Importamos utilidades de tiempo de Python para manejar validaciones y operaciones de días (sumas, conversiones de texto a fecha, etc)
from datetime import datetime, timedelta

def calcular_semana_extendida(fecha):
    """
    Calcula un número de semana continuo desde el año 1963, idéntico al que usa la BD.
    """
    anio_iso = fecha.isocalendar()[0]
    semana_iso_actual = fecha.isocalendar()[1]
    return semana_iso_actual + 6 + ((anio_iso - 1963) * 52)

def calcular_fechas_tarea(fecha_inicio_texto, fecha_fin_texto, frecuencia_en_dias):
    """
    Función que recibe un rango de fechas en formato texto, las convierte y aplica 
    la regla de negocio de saltarse los domingos para devolver la lista exacta 
    de fechas en las que "toca" realizar una tarea en específico.
    """
    # Intentamos primero convertir los strings recibidos directamente asumiendo que vienen en un formato de texto estándar
    try:
        # datetime.strptime analiza un caracter de texto ("2026-03-01") según el filtro "%Y-%m-%d" y lo vuelve objeto de fecha pura (.date())
        # .date() recorta segundos, horas y minutos; dejando únicamente el aspecto día, mes y año.
        fecha_inicio_convertida = datetime.strptime(fecha_inicio_texto, "%Y-%m-%d").date()
        fecha_fin_convertida = datetime.strptime(fecha_fin_texto, "%Y-%m-%d").date()
        
    except (TypeError, ValueError):
        # Si entra al bloque except es porque psycopg2 ya nos mandó objetos pre-evaluados o hay algún formato inesperado.
        
        # Validamos: Si la fecha de inicio tiene la propiedad 'date', ejecutamos esa propiedad para limpiar horas extras
        if hasattr(fecha_inicio_texto, 'date'):
            fecha_inicio_convertida = fecha_inicio_texto.date()
        # Si ya tiene la propiedad 'year' pero no 'date', significa que es puro y directo, lo asignamos directamente
        elif hasattr(fecha_inicio_texto, 'year'):
            fecha_inicio_convertida = fecha_inicio_texto
        # Si llegamos aquí sin éxito, forzamos su formato convirtiendo de manera genérica
        else:
            fecha_inicio_convertida = datetime.strptime(fecha_inicio_texto, "%Y-%m-%d").date()
            
        # Repetimos el mismo mecanismo exacto de validación/conversión pero para el final del recorrido
        if hasattr(fecha_fin_texto, 'date'):
            fecha_fin_convertida = fecha_fin_texto.date()
        elif hasattr(fecha_fin_texto, 'year'):
            fecha_fin_convertida = fecha_fin_texto
        else:
            fecha_fin_convertida = datetime.strptime(str(fecha_fin_texto), "%Y-%m-%d").date()

    # Si por alguna incongruencia resulta que la fecha de inicio obligatoria es mayor al final fijado o la frecuencia es 0 o vacía
    if fecha_inicio_convertida > fecha_fin_convertida or not frecuencia_en_dias:
        # Termina aquí retornando una lista vacía de fechas precalculadas, sin matar el proceso para nada más
        return []

    # Empezamos una lista limpia la cual alojará y acumulará las fechas exitosas (aquellas donde caiga el evento programado)
    lista_fechas_calculadas = []
    # Generamos un puntero o "flecha indicadora" de fecha para transitar por el calendario paso a paso apuntando al inicio
    fecha_puntero_actual = fecha_inicio_convertida
    # Establecemos un marcador (aux). Sirve para medir internamente los reseteos del bloque menor a 7
    contador_dias_auxiliar = 0

    # Creamos un bucle general que estará dando vueltas mientras el puntero se mantenga detrás de la fecha final limite estipulada
    while fecha_puntero_actual <= fecha_fin_convertida:
        
        # Bifurcación A: Comportamiento para tareas MUY MUY recurrentes (casi diarias o semanales, es decir su ciclo < 7 días)
        if frecuencia_en_dias < 7:
            # Condiciones cruciales conjuntas:
            # 1. (current_date.weekday() != 6): Verificamos usando el weekday predefinido que el día actual no sea el índice 6 (que equivale al domingo)
            # 2. (...) % frequency == 0: Evaluamos si la resta entre el día de la semana actual y el inicial es un múltiplo matemático de nuestra frecuencia (Ej: restan 4 días y la frec es 2 = OK)
            if (fecha_puntero_actual.weekday() != 6) and ((fecha_puntero_actual.weekday() - fecha_inicio_convertida.weekday()) % frecuencia_en_dias == 0):
                # Como sí pasó la prueba, lo incrustamos en la lista guardando solo su apariencia en texto (AAAA-MM-DD)
                lista_fechas_calculadas.append(fecha_puntero_actual.strftime("%Y-%m-%d"))
                # Hacemos que la flecha avance al mañana agregando mágicamente 1 día lineal y contable
                fecha_puntero_actual += timedelta(days=1)
                # Acumulamos evidencia auxiliar en el contador (por las moscas para la trazabilidad)
                contador_dias_auxiliar += 1
            else:
                # Si falló la ecuación (Ej: el día actual sí era un Domingo o no era el intervalo justo), solo avanzamos al día de mañana
                fecha_puntero_actual += timedelta(days=1)
                
        # Bifurcación B: Comportamiento para tareas MEDIANAS, MENSUALES O ANUALES (deben ejecutarse cada 7 o más días)
        else:
            # Reseteamos nuestro acumulador de evidencias preventivas a 0 por si estuviese atascado en procesos previos
            contador_dias_auxiliar = 0
            
            # Caso especial B.1: Cuando el bloque es exactamente divisible por una semana entera (ej. cada 7 días, o 14, o 21 idénticos)
            if frecuencia_en_dias % 7 == 0:
                # En este tipo de ciclos tan precisos que nunca alterarían el día de inicio, simplemente anexamos a la lista la fecha actual en formato texto
                lista_fechas_calculadas.append(fecha_puntero_actual.strftime("%Y-%m-%d"))
                # Tras anexarlo, agarramos nuestra flecha indicadora y, en lugar de avanzar solo a mañana, le inyectamos varios días a la vez haciendo el gran salto de frecuencia
                fecha_puntero_actual += timedelta(days=frecuencia_en_dias)
                
            # Caso especial B.2: Cuando la tarea cae, por decir, cada 12 días; son números rebeldes que no forman semanas justas
            else:
                # Volvemos a solicitar una condición conjunta muy parecida a la primera iteración:
                # 1. Comprobamos que hoy no es domingo (weekday != 6). El requerimiento inquebrantable de la planta
                # 2. Tomamos la fecha puntero actual y le restamos sin piedad la fecha que le dio pie original, extrayendo la estocada .days (días limpios), y verificamos un residuo perfecto modular (==0) contra la frecuencia irregular
                if (fecha_puntero_actual.weekday() != 6) and ((fecha_puntero_actual - fecha_inicio_convertida).days % frecuencia_en_dias == 0):
                    # Pasada la estricta y matemática aduana, introdujimos por fin en nuestra canasta general la fecha moldeada a cadena de texto de la misma forma que antes
                    lista_fechas_calculadas.append(fecha_puntero_actual.strftime("%Y-%m-%d"))
                # En los procesos de ciclos amplios que NO forman semanas perfectas, el desplazamiento del puntero va solo 1 por 1 garantizando no brincarnos las asimetrías de días de manera errática
                fecha_puntero_actual += timedelta(days=1)

    # El ciclo general de todo este bloque finaliza y nuestra última misión de la función es liberar la valiosa bolsa ya llenada de un extremo al otro
    return lista_fechas_calculadas


# =========================================================
# --- ÁREA DE PUESTA EN MARCHA E INYECCIÓN DE LA BD ---
# =========================================================

# Esta bandera de python le habla al ejecutador nativo ordenando: si nos lanzan el script por sí solo, procesa e inicia lo que está acá a continuación
if __name__ == "__main__":
    
    # Preparamos las llaves necesarias construyendo un conector a nuestra base de host psql local (como tener la llave a mano de la puerta DB)
    conexion_hacia_postgresql = psycopg2.connect(
        host="localhost",          # Dominio del host local donde reside postgres
        database="mydb",           # Indicamos qué base del clúster abriremos
        user="myuser",             # Quien de los roles entrará 
        password="mypassword",     # Cual será la validación del usuario
        port=5432                  # Acceso por el socket clásico TCP 5432
    )
    # Activamos la manija interna que enviará nuestro código crudo a operar la conexión exitosa 
    cursor_bd = conexion_hacia_postgresql.cursor()

    # Pre-establecemos una fecha en texto límite forzada que impedirá a nuestra simulación crear bucles colosales e inmanejables a futuro lejano. El borde será la noche vieja del 2026.
    tope_fecha_limite_simulacion = "2026-12-31"
    
    # PASO NUMERO 1. Lanzamos una gran interrogante de datos contra nuestra maestra matriz 'works4cdp_task'.
    # Nos interesan las ideas nucleicas (id), su pulso biológico (frequency), inicio (start_date) y su turno (turn: A o B).
    consulta_extraccion_tareas = """
        SELECT id, frequency, start_date, turn
        FROM works4cdp_task
        WHERE id > 99 ORDER BY id
    """
    # Damos luz verde al disparo de la red por intermedio del cursor usando el bloque texto redactado recién.
    cursor_bd.execute(consulta_extraccion_tareas)
    # En este punto recuperamos físicamente el cofre del tesoro que devolvió nuestra query de forma masiva como lista multi-matriz y lo atajamos en una variable de pila 
    lista_de_todas_las_tareas_halladas = cursor_bd.fetchall()

    # Como sabemos que hay que insertar en otra tabla al finalizar, preparamos un balde transparente nuevo que acumulará en formato (IdTask, IdCal)
    bolsa_de_asignaciones_listas = []
    # Generamos de paso también un pequeño pizarrón interno donde sumaremos marcas (hits) cada vez que falle el macheo por una discrepancia calendario -> tarea.
    contador_informativo_tareas_huerfanas = 0

    # Desgranamos el cofre grande fila por fila, incluyendo el turno mapeado (A o B)
    for id_de_la_tarea, cadena_frecuencia_tarea, fecha_partida_tarea, turno_tarea in lista_de_todas_las_tareas_halladas:
        
        # Validación Preventiva: Las tareas con campos dañados, totalmente vacíos o que estén etiquetadas bajo la frecuencia mística "999" (descartable) no entrarán.
        if cadena_frecuencia_tarea is None or cadena_frecuencia_tarea == '' or str(cadena_frecuencia_tarea) == '999':
            # Skip completo a la fila en el for usando continue para ahorrarnos procesar polvo.
            continue
            
        # Re transformamos a número entero duro y duro el aspecto que represente la frecuencia para dáselo al conversor matricial.
        frecuencia_numerica_tarea = int(cadena_frecuencia_tarea)
        
        # Validación de seguridad N°2. Si el inicio está borrado o roto, tampoco jugamos; bye bye con un continue.
        if fecha_partida_tarea is None:
            continue
            
        # PASO NÚMERO 2. Llegados vivos acá; le pasamos la estafeta a nuestra grandiosa función matemática y esperamos pacientemente un momento
        # Que de sus engranes lógicos saque para cada uno de nuestros mantenimientos una lista pura y real conformada del arreglo textual de fechas: ['2026-X', '2026-Y'] 
        lista_con_dias_donde_cae_esta_tarea = calcular_fechas_tarea(fecha_partida_tarea, tope_fecha_limite_simulacion, frecuencia_numerica_tarea)
        
        # Abrazamos e introducimos esa sub-sub-lista entregada de regreso a un loop que por cada una de esas probables fechas le hará el chequeo cruzado de validaciones...
        # Para buscar el calendario, transformamos el turno de la tabla Task (ej. 'A' o 'B')
        # al turno equivalente en la tabla Calendar ('D' o 'N')
        turno_buscado = 'D' # Por defecto asume Día
        if turno_tarea == 'A':
            turno_buscado = 'D'
        elif turno_tarea == 'B':
            turno_buscado = 'N'

        for dia_de_aplicacion_especifico in lista_con_dias_donde_cae_esta_tarea:
            
            # PASO NÚMERO 3. Ya sé que esta tarea toca el "28 de Marzo".
            # Primero, registramos este Evento Único en la tabla central (TaskP)
            # Para guardar su estado, su fecha, y el año/semana correspondiente
            fecha_obj = datetime.strptime(dia_de_aplicacion_especifico, "%Y-%m-%d")
            semana_calculada = calcular_semana_extendida(fecha_obj) # Semana continua histórica desde 1963
            dia_letra = fecha_obj.strftime("%A")          # Lunes, Martes... etc

            comando_insertar_taskp = """
                INSERT INTO works4cdp_taskp (
                    task_id, year, week, day, date,
                    rescheduled, is_permanent_reschedule,
                    estado_id, priority
                ) VALUES (%s, %s, %s, %s, %s, False, False, 1, 1) RETURNING id
            """
            
            # Ejecutamos la inyección y pedimos de vuelta el ID recién creado
            cursor_bd.execute(comando_insertar_taskp, (
                id_de_la_tarea, fecha_obj.year, semana_calculada, dia_letra, dia_de_aplicacion_especifico
            ))
            id_nuevo_evento_taskp = cursor_bd.fetchone()[0]

            # PASO NÚMERO 4. Ahora sí, preguntamos por TODOS los grupos que estén trabajando en ese turno para ese día.
            comando_busca_id_calendario_ideal = """
                SELECT id FROM works4cdp_calendar 
                WHERE date = %s AND turn = %s
            """
            
            cursor_bd.execute(comando_busca_id_calendario_ideal, (dia_de_aplicacion_especifico, turno_buscado))
            # Obtenemos TODOS los grupos incidentales del calendario para esa jornada
            resultados_calendario = cursor_bd.fetchall()
            
            # Analizamos y enlazamos el Calendario Humano con el Evento Programado (TaskP)
            if resultados_calendario:
                for fila in resultados_calendario:
                    id_confirmado_del_calendario = fila[0]
                    # Aquí la magia: unimos el TaskP con el Calendar
                    bolsa_de_asignaciones_listas.append((id_nuevo_evento_taskp, id_confirmado_del_calendario))
            else:
                # Si de plano se programó el mantenimiento fuera de los límites donde hay grupos en el calendario
                contador_informativo_tareas_huerfanas += 1

    # PASO NÚMERO 5. Cuando todo haya terminado satisfactoriamente revisamos el empaque de la bolsa general para las asignaciones múltipes
    if bolsa_de_asignaciones_listas:
        # Preparamos al motor para incrustar esta dupla simétrica en nuestro puente relacional sagrado, apuntando ahora a TaskP
        consulta_inyeccion_final_para_esquema = """
            INSERT INTO works4cdp_taskgroupassignment (taskp_id, calendar_id)
            VALUES (%s, %s)
        """
        try:
            # Emulamos un disparo masivo con .executemany incrustando cientos de paridades de puente relacional desde la RAM de python hacia Postgres en milisegundos
            cursor_bd.executemany(consulta_inyeccion_final_para_esquema, bolsa_de_asignaciones_listas)
            # Ordenamos como un escribano asentar los cientos de bloques inyectados asegurando su permanencia atada a lo ACID del motor DB
            conexion_hacia_postgresql.commit()
            
            # Presumimos las credenciales y logros arrojando el balance y cantidad masiva lograda a plena luz
            print(f"¡Éxito! {len(bolsa_de_asignaciones_listas)} asignaciones registradas en works4cdp_taskgroupassignment.")
            
            # Como recordamos llevar notas, sí de último resulta que al menos 1 triste tarea quedó viuda o descasada por no existir calendario en esa época futurista
            if contador_informativo_tareas_huerfanas > 0:
                # Levantamos el letrero naranja por consola previniendo la falta administrativa detectada.
                print(f"Aviso: {contador_informativo_tareas_huerfanas} fechas generadas cayeron fuera del rango de fechas que existen en works4cdp_calendar.")
                
        # Cuando el motor reniega sobre lo empacado en toda forma e irrumpe un Exception que rompe el commit
        except Exception as error_capturado_de_base:
            # Damos reversa rápida y desatamos nudos desde Python para no dañar índices de otras funciones
            conexion_hacia_postgresql.rollback()
            # Mostramos un cartel rojo donde acusamos el nombre preciso de la anomalía y razón que arrojó psycopg2
            print(f"Error insertando asignaciones: {error_capturado_de_base}")
    # En contraparte; en caso de que todo el loop for hubiera sido procesado y sencillamente la bolsa haya cerrado en cero por simpleza o incompatibilidad
    else:
        # Hablamos plano al analista anunciándole que a nivel lógico la inyección no se aplicará para no mandar vacíos a PGAdmin.
        print("No se generaron asignaciones para insertar. (Verifica si las fechas de las tareas caen en el rango del calendario).")

    # Llegando al final del telón indistintamente apaga y desconecta todos los candados con gracia asegurando los recursos del OS
    cursor_bd.close()
    conexion_hacia_postgresql.close()
