# Importamos el módulo psycopg2 para conectarnos y operar con la base de datos PostgreSQL
import psycopg2
# Importamos datetime y timedelta para poder crear y manipular fechas (sumar días, calcular semanas, etc.)
from datetime import datetime, timedelta
import argparse

def calcular_semana_extendida(fecha):
    """
    Calcula un número de semana continuo desde el año 1963.
    Esto evita que el conteo de semanas vuelva a 1 cada enero, 
    permitiendo programar mantenimientos a largo plazo sin cortes anuales.
    """
    # Extraemos el año según la norma ISO a partir de la fecha proporcionada
    anio_iso = fecha.isocalendar()[0]
    # Extraemos el número de semana del año según la norma ISO (del 1 al 52 o 53)
    semana_iso_actual = fecha.isocalendar()[1]
    # Calculamos cuántos años enteros han pasado desde 1963
    anios_transcurridos_desde_1963 = anio_iso - 1963
    # Convertimos esos años en semanas (multiplicando por 52)
    semanas_acumuladas_por_anios = anios_transcurridos_desde_1963 * 52
    # Sumamos la semana actual + un desfase fijo de 6 + las semanas acumuladas históricamente
    semana_extendida_final = semana_iso_actual + 6 + semanas_acumuladas_por_anios
    # Devolvemos el cálculo convertido en un número entero continuo
    return semana_extendida_final


def generar_registros_calendar(fecha_inicio, fecha_fin, patron_de_turnos_fijo, lista_ids_de_grupos):
    """
    Toma un rango de fechas y una lista de grupos, y genera una lista de filas (tuplas)
    listas para ser insertadas en la base de datos, distribuyendo de forma equitativa
    un patrón de rotación de turnos entre todos los grupos.
    """
    # Definimos un arreglo estático para traducir los índices de los días de la semana a texto en español
    nombres_dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    
    # Contamos cuántos grupos reales existen leyendo la longitud de la lista proporcionada
    cantidad_total_grupos = len(lista_ids_de_grupos)
    
    # Si la lista de grupos viene vacía, retornamos una lista vacía para no procesar nada
    if cantidad_total_grupos == 0:
        return []

    # Obtenemos cuántos días en total dura el patrón base de turnos (en este caso 49 días / 7 semanas)
    longitud_total_del_patron = len(patron_de_turnos_fijo)
    
    # Dividimos la longitud del patrón entre la cantidad de grupos. 
    # Esto nos dirá cuántos días de "ventaja" debe llevar un grupo sobre otro para no coincidir en los mismos turnos.
    desfase_de_dias_por_grupo = longitud_total_del_patron / cantidad_total_grupos

    # Inicializamos una lista vacía donde iremos guardando todas las tuplas generadas
    lista_de_registros_finales = []

    # Iteramos sobre la lista de IDs de grupos, obteniendo tanto el índice (indice_grupo) como el valor real del ID (id_del_grupo)
    for indice_grupo, id_del_grupo in enumerate(lista_ids_de_grupos):
        
        # Calculamos desde qué día del patrón debe empezar este grupo en específico, redondeando al entero más cercano
        posicion_inicial_en_patron = round(indice_grupo * desfase_de_dias_por_grupo)
        
        # Creamos una versión única del patrón para este grupo, cortando el original desde la posición inicial calculada...
        # ... y pegando al final el trozo del patrón que quedó atrás, así completamos el ciclo girado
        patron_adaptado_al_grupo = patron_de_turnos_fijo[posicion_inicial_en_patron:] + patron_de_turnos_fijo[:posicion_inicial_en_patron]

        # Establecemos la fecha actual del bucle como la fecha de inicio recibida en los parámetros
        fecha_evaluada_actualmente = fecha_inicio
        
        # Inicializamos un contador de días (índice) en cero para recorrer el patrón
        contador_dias_transcurridos = 0

        # Mantenemos un bucle vivo mientras la fecha evaluada no supere la fecha final deseada
        while fecha_evaluada_actualmente <= fecha_fin:
            # Obtenemos el tamaño real de la lista del patrón adaptado
            tamanio_patron_adaptado = len(patron_adaptado_al_grupo)
            
            # Calculamos la posición exacta en el patrón usando el módulo (%). 
            # Esto permite que el contador crezca al infinito, pero siempre reinicie el ciclo del patrón al llegar al final
            posicion_en_ciclo = contador_dias_transcurridos % tamanio_patron_adaptado
            
            # Obtenemos la letra del turno ("D", "N", "x") correspondiente a este día en el ciclo
            turno_del_dia = patron_adaptado_al_grupo[posicion_en_ciclo]

            # Construimos una tupla (que no puede ser modificada luego) con la estructura exacta que pide la base de datos
            nuevo_registro_calendario = (
                fecha_evaluada_actualmente.year,                             # year: El año extraído de la fecha
                calcular_semana_extendida(fecha_evaluada_actualmente),       # week: La semana continua personalizada
                nombres_dias_semana[fecha_evaluada_actualmente.weekday()],   # day: El nombre en español del día de la semana
                fecha_evaluada_actualmente.strftime("%Y-%m-%d"),             # date: La fecha formateada en texto como AAAA-MM-DD
                turno_del_dia,                                               # turn: La letra del turno ("D", "N", "x")
                id_del_grupo,                                                # group_id: El ID real de la base de datos para la cuadrilla
                0,                                                           # overtime: Horas extras que inician por defecto en cero
                None                                                         # user_id: Nulo porque la programación es a nivel cuadrilla, no a nivel empleado
            )
            
            # Agregamos la tupla recién creada a la lista general de registros
            lista_de_registros_finales.append(nuevo_registro_calendario)

            # Sumamos literalmente un día (1 día) a la fecha actual para evaluar el mañana en la siguiente vuelta
            fecha_evaluada_actualmente += timedelta(days=1)
            # Incrementamos en uno el contador que determina el paso por el patrón de turnos
            contador_dias_transcurridos += 1

    # Una vez procesados todos los días para todos los grupos, devolvemos la matriz completa
    return lista_de_registros_finales


def parse_arguments():
    parser = argparse.ArgumentParser(description='Generar calendario de turnos para grupos.')
    parser.add_argument(
        '--fecha_inicio',
        type=str,
        help='Fecha de inicio en formato YYYY-MM-DD',
        default='2025-12-30'
    )
    parser.add_argument(
        '--fecha_fin',
        type=str,
        help='Fecha de fin en formato YYYY-MM-DD',
        default='2027-01-03'
    )
    return parser.parse_args()


# =========================================================
# --- BLOQUE DE EJECUCIÓN PRINCIPAL Y CONEXIÓN A LA BD ---
# =========================================================

# Este bloque if garantiza que el código de abajo solo se ejecute si llamamos al archivo directamente, no si lo importamos en otro lado
if __name__ == "__main__":
    
    args = parse_arguments()
    
    try:
        # Convertimos los argumentos de texto a objetos datetime
        fecha_inicio_de_simulacion = datetime.strptime(args.fecha_inicio, '%Y-%m-%d')
        fecha_fin_de_simulacion = datetime.strptime(args.fecha_fin, '%Y-%m-%d')
    except ValueError as e:
        print(f"Error parseando las fechas. Asegúrese de que el formato sea YYYY-MM-DD: {e}")
        exit(1)

    # Definimos estáticamente un arreglo de 49 elementos que representa la rotación madre ideal de 7 semanas (D=Día, N=Noche, x=Descanso)
    plantilla_patron_de_turnos = [
        "B", "B", "B", "x", "x", "x", "A",
        "A", "A", "A", "A", "x", "x", "x",
        "x", "B", "B", "B", "B", "x", "x",
        "x", "x", "A", "A", "A", "A", "x",
        "x", "x", "x", "B", "B", "B", "B",
        "B", "x", "x", "x", "A", "A", "A",
        "A", "A", "x", "x", "x", "B", "B"
    ]
    
    # Creamos un objeto "Connection" de psycopg2 apuntando a las credenciales locales de la instancia PostgreSQL
    conexion_base_datos = psycopg2.connect(
        host="localhost",         # Servidor local de PostgreSQL
        database="mydb",          # Nombre explícito de la base de datos
        user="myuser",            # Usuario de la base de datos
        password="mypassword",    # Contraseña en texto plano
        port=5433                 # Puerto por defecto de PostgreSQL
    )
    
    # A partir de la conexión, generamos un cursor. El cursor es el objeto que viaja a la base e inserta u obtiene sentencias SQL
    cursor_ejecutor = conexion_base_datos.cursor()

    try:
        # Preparamos una consulta simple para solicitar todos los IDs de la tabla works4cdp_userp (nuestras cuadrillas)
        consulta_obtener_grupos = "SELECT id FROM works4cdp_userp ORDER BY id"
        # Le pedimos al cursor que envíe y ejecute esa consulta en el motor de base de datos
        cursor_ejecutor.execute(consulta_obtener_grupos)
        
        # Recuperamos todas las filas devueltas por la consulta (que viene en forma de una lista de tuplas: [(1,), (2,), (3,)])
        resultado_tuplas_grupos = cursor_ejecutor.fetchall()
        
        # Iteramos sobre esa lista de tuplas y extraemos solo el primer valor (índice [0]) de cada tupla para armar una lista de números planos
        lista_final_ids_grupos = [fila_grupo[0] for fila_grupo in resultado_tuplas_grupos]

        # Validamos: Si la lista quedó vacía significa que la tabla UserP está en blanco en PostgreSQL
        if not lista_final_ids_grupos:
            # Imprimimos en consola un mensaje de error legible para parar el proceso a tiempo
            print("No se encontraron grupos en la tabla works4cdp_userp. No se puede generar el calendario.")
        else:
            # Mostramos un mensaje informativo indicando sobre cuántos grupos de la BD se hará el cálculo
            print(f"Generando calendario para {len(lista_final_ids_grupos)} grupos encontrados: {lista_final_ids_grupos}")
            print(f"Desde {fecha_inicio_de_simulacion.strftime('%Y-%m-%d')} hasta {fecha_fin_de_simulacion.strftime('%Y-%m-%d')}")
            
            # Invocamos nuestra función maestra pasando las fechas, el patrón y los IDs reales de la base de datos
            matriz_datos_listos_para_insertar = generar_registros_calendar(
                fecha_inicio_de_simulacion, 
                fecha_fin_de_simulacion, 
                plantilla_patron_de_turnos, 
                lista_final_ids_grupos
            )

            # Escribimos el comando SQL puro mediante marcadores de posición (%s) para evitar inyección SQL
            # y para decirle a la tabla works4cdp_calendar qué columnas corresponden a la tupla que generamos
            consulta_insercion_masiva = """
                INSERT INTO works4cdp_calendar (
                    year, week, day, date, turn, group_id, overtime, id_user
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            # Usamos executemany: viaja a la base de datos una sola vez con toda la lista entera, optimizando milisegundos de latencia de red
            cursor_ejecutor.executemany(consulta_insercion_masiva, matriz_datos_listos_para_insertar)
            
            # Ordenamos confirmar los cambios aplicados en la base de datos para que persistan, o de lo contrario haría rollback automático
            conexion_base_datos.commit()
            
            # Confirmamos e imprimimos por pantalla que el bloque se ejecutó de forma correcta y la cantidad que se salvó en BD
            print(f"¡Éxito! {len(matriz_datos_listos_para_insertar)} registros se han insertado correctamente en works4cdp_calendar.")

    except Exception as error_capturado:
        # En caso de que se haya roto la conexión, haya duplicidad o una llave foránea falte, deshacemos cualquier inserción a medias
        conexion_base_datos.rollback()
        # Mostramos en pantalla qué motivó la falla del proceso entero
        print(f"Error durante el proceso: {error_capturado}")
        
    finally:
        # Finalmente, haya ocurrido error o no, cerramos limpiamente el objeto cursor
        cursor_ejecutor.close()
        # Cortamos la conexión cliente-servidor con PostgreSQL para no dejar conexiones colgadas
        conexion_base_datos.close()
