from datetime import datetime, timedelta

def insert_task(start_date_str, end_date_str, frequency, group_id, state_id, task_id):
    # Convertir fechas
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

    if start_date > end_date:
        return []

    # Cálculo de semana según tu lógica (initial_week + 6 + offset años)
    year = start_date.isocalendar()[0]
    # xweek = semana_iso + offset_semanas + (años_desde_1963 * 52)
    xweek = start_date.isocalendar()[1] + 6 + ((year - 1963) * 52)
    
    DAYS_OF_WEEK = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    records = []
    current_date = start_date
    current_week = xweek

    while current_date <= end_date:
        # Lógica de inserción (Saltar domingos si frec < 7 o según modulo)
        is_scheduled_day = False
        
        if frequency < 7:
            if (current_date.weekday() != 6) and ((current_date.weekday() - start_date.weekday()) % frequency == 0):
                is_scheduled_day = True
        elif frequency % 7 == 0:
            is_scheduled_day = True # El incremento se maneja al final del loop
        else:
            if (current_date.weekday() != 6) and ((current_date - start_date).days % frequency == 0):
                is_scheduled_day = True

        if is_scheduled_day:
            day_name = DAYS_OF_WEEK[current_date.weekday()]
            # TUPLA AJUSTADA AL MODELS.PY (TaskP)
            # Orden: task_id, year, week, day, date, estado_id, rescheduled, group_id, is_permanent, priority
            record = (
                task_id,                # task_id
                current_date.year,      # year
                current_week,           # week
                day_name,               # day
                current_date,           # date
                state_id,               # estado_id (P=1)
                False,                  # rescheduled
                group_id,               # group_id (Asignación inicial)
                False,                  # is_permanent_reschedule
                1                       # priority (default)
            )
            records.append(record)
            
            # Si la frecuencia es múltiplo de 7, saltamos directamente
            if frequency >= 7 and frequency % 7 == 0:
                current_date += timedelta(days=frequency)
                current_week += frequency // 7
                continue

        # Incremento estándar
        prev_weekday = current_date.weekday()
        current_date += timedelta(days=1)
        # Si pasamos de Domingo (6) a Lunes (0), incrementamos semana
        if prev_weekday == 6:
            current_week += 1
            
    return records
