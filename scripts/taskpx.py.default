from datetime import datetime, timedelta

def insert_task(start_date, end_date, frec, user, state, task):
    # Convertir las fechas de entrada en objetos datetime y luego a date
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

    if start_date_obj > end_date_obj:
        return []

    # Parámetros iniciales de la tarea
    initial_week = 1  # Número de semana inicial
    year = start_date_obj.isocalendar()[0]
    #xweek = initial_week + 6 + ((year - 1963) * 52)

    start_date = start_date_obj  # Lunes 30 de diciembre
    xweek = start_date.isocalendar()[1] + 6 + ((year - 1963) * 52)
    frequency = frec  # Días entre repeticiones
    end_date = end_date_obj  # Rango final
    #print(start_date)
    #print(start_date.isocalendar()[1])
    # Días de la semana (de lunes a sábado)
    DAYS_OF_WEEK = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    # Crear registros para la tabla works4cdp_taskp
    aux=0
    records = []
    current_date = start_date
    current_week = xweek


    while current_date <= end_date:
        #print("Current date: ", current_date)
        if frequency<7:
            #if (current_date.weekday() !=6)&((current_date.weekday()-start_date.weekday())%frequency==0)&(aux<=frequency):
            if (current_date.weekday() != 6) & ((current_date.weekday() - start_date.weekday()) % frequency == 0):

                day_name = DAYS_OF_WEEK[current_date.weekday()]
                record=(
                    current_date.year,
                    current_week,
                    day_name,
                    current_date.strftime("%Y-%m-%d"),
                    user,
                    False,
                    None,
                    None,
                    None,
                    state,
                    task,
                )
                records.append(record)
                current_date += timedelta(days=1)
                if current_date.weekday()==6:
                    current_week += 1
                    aux=0
                aux+=1
            else:
                current_date += timedelta(days=1)
                if current_date.weekday()==6:
                    current_week += 1
                    aux = 0

        else:
            aux=0
            if frequency%7==0:
                day_name = DAYS_OF_WEEK[current_date.weekday()]
                record=(
                    current_date.year,
                    current_week,
                    day_name,
                    current_date.strftime("%Y-%m-%d"),
                    user,
                    False,
                    None,
                    None,
                    None,
                    state,
                    task,
                )
                records.append(record)
                current_date += timedelta(days=frequency)
                    #if current_date.weekday()==6:
                current_week += frequency // 7
            else:
                if (current_date.weekday() != 6) and ((current_date - start_date).days % frequency == 0):
                    day_name = DAYS_OF_WEEK[current_date.weekday()]
                    record = (
                        current_date.year,
                        current_week,
                        day_name,
                        current_date.strftime("%Y-%m-%d"),
                        user,
                        False,
                        None,
                        None,
                        None,
                        state,
                        task,
                    )
                    records.append(record)
                current_date += timedelta(days=1)
                if current_date.weekday()==6:
                    current_week += 1


    #record = xweek
    return records

# # Ejemplo de uso
# start_date = "2025-01-25"
# end_date = "2025-04-08"
# frecuency = 70
# turn = "A"
# user = 1
# state = 2
# task = 1
#
# records = insert_task(start_date, end_date, frecuency, turn, user, state, task)
# # Verificar los registros generados
# for record in records[:150]:  # Muestra solo los primeros 10 registros
#     print(record)
