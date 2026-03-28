from datetime import datetime, timedelta


def insert_task(start_date, end_date, frec, state, task, gen_start=None):
    """
    Genera registros de tareas repetitivas entre gen_start y end_date,
    respetando la frecuencia definida a partir de start_date.

    Parámetros:
    - start_date (str): Fecha de inicio de la repetición (formato YYYY-MM-DD)
    - end_date (str): Fecha límite para generar registros
    - frec (int): Frecuencia en días
    - state: Estado de la tarea
    - task: Identificador de la tarea
    - gen_start (str, opcional): Fecha desde la cual comenzar a generar. Si no se
      proporciona, se usa start_date.
    """
    # Convertir las fechas de entrada en objetos date
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Si no se especifica gen_start, se usa start_date_obj
    if gen_start is None:
        gen_start_obj = start_date_obj
    else:
        gen_start_obj = datetime.strptime(gen_start, "%Y-%m-%d").date()

    # Validación básica
    if start_date_obj > end_date_obj or gen_start_obj > end_date_obj:
        return []

    # Parámetros iniciales
    year = start_date_obj.isocalendar()[0]
    # Fórmula de número de semana personalizada (se mantiene igual)
    xweek = start_date_obj.isocalendar()[1] + 6 + ((year - 1963) * 52)
    frequency = frec

    # Días de la semana (de lunes a domingo)
    DAYS_OF_WEEK = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    # --- Función auxiliar para determinar si una fecha es de repetición ---
    def is_repetition(date):
        """Usa la misma lógica que el bucle original según la frecuencia."""
        if frequency < 7:
            # Condición original (basada en weekday)
            return (date.weekday() != 6) and ((date.weekday() - start_date_obj.weekday()) % frequency == 0)
        elif frequency % 7 == 0:
            # En el bucle original, para múltiplos de 7 se genera en cada fecha que se avanza,
            # asumiendo que la fecha actual es de repetición. Para la búsqueda inicial,
            # usamos la condición correcta de días.
            return (date - start_date_obj).days % frequency == 0
        else:
            # Para otros casos, el bucle usa la condición de días
            return (date - start_date_obj).days % frequency == 0

    # --- Encontrar la primera fecha de repetición >= gen_start_obj ---
    first_date = max(start_date_obj, gen_start_obj)
    # Si la primera fecha candidata no es válida, buscar la siguiente que sí lo sea
    if not is_repetition(first_date):
        # Buscar día a día hasta encontrar una válida (rango limitado por end_date)
        while first_date <= end_date_obj and not is_repetition(first_date):
            first_date += timedelta(days=1)
        if first_date > end_date_obj:
            return []  # No hay ninguna fecha válida en el rango

    # --- Configurar variables iniciales para el bucle ---
    current_date = first_date
    # Calcular current_week usando la misma fórmula personalizada, pero basada en current_date
    current_week = current_date.isocalendar()[1] + 6 + ((current_date.year - 1963) * 52)

    aux = 0  # Variable auxiliar que se usa en el bucle original (se mantiene)
    records = []

    # --- Bucle principal (sin modificar la lógica interna) ---
    while current_date <= end_date_obj:
        if frequency < 7:
            # Caso original para frecuencias menores a 7 días
            if (current_date.weekday() != 6) and ((current_date.weekday() - start_date_obj.weekday()) % frequency == 0):
                day_name = DAYS_OF_WEEK[current_date.weekday()]
                record = (
                    current_date.year,
                    current_week,
                    day_name,
                    current_date.strftime("%Y-%m-%d"),
                    False,
                    None,
                    None,
                    None,
                    state,
                    task,
                )
                records.append(record)
                current_date += timedelta(days=1)
                if current_date.weekday() == 6:
                    current_week += 1
                    aux = 0
                aux += 1
            else:
                current_date += timedelta(days=1)
                if current_date.weekday() == 6:
                    current_week += 1
                    aux = 0
        else:
            aux = 0
            if frequency % 7 == 0:
                # Frecuencia múltiplo de 7: avanzar de a frequency días
                day_name = DAYS_OF_WEEK[current_date.weekday()]
                record = (
                    current_date.year,
                    current_week,
                    day_name,
                    current_date.strftime("%Y-%m-%d"),
                    False,
                    None,
                    None,
                    None,
                    state,
                    task,
                )
                records.append(record)
                current_date += timedelta(days=frequency)
                current_week += frequency // 7
            else:
                # Frecuencia mayor a 7 pero no múltiplo: iterar día a día
                if (current_date.weekday() != 6) and ((current_date - start_date_obj).days % frequency == 0):
                    day_name = DAYS_OF_WEEK[current_date.weekday()]
                    record = (
                        current_date.year,
                        current_week,
                        day_name,
                        current_date.strftime("%Y-%m-%d"),
                        False,
                        None,
                        None,
                        None,
                        state,
                        task,
                    )
                    records.append(record)
                current_date += timedelta(days=1)
                if current_date.weekday() == 6:
                    current_week += 1

    return records