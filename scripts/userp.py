from datetime import datetime, timedelta

def generar_horario_personalizado(inicio, fin, patron_fijo, inicio_patron):
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    horario = []
    fecha_actual = inicio

    # Ajuste del patrón según la posición inicial
    patron_reordenado = patron_fijo[inicio_patron:] + patron_fijo[:inicio_patron]

    index = 0
    while fecha_actual <= fin:
        horario.append({
            "Fecha": fecha_actual.strftime("%Y-%m-%d"),
            "Día Semana": dias_semana[fecha_actual.weekday()],
            "Turno": patron_reordenado[index % len(patron_reordenado)]  # Aplicar el patrón cíclico
        })
        fecha_actual += timedelta(days=1)
        index += 1

    return horario

# Definir fechas de inicio y fin
inicio = datetime(2025, 8, 25)
fin = datetime(2025, 10, 12)

# Patrón fijo
patron_fijo = [
    "D", "D", "X", "X", "X", "N", "N",
    "N", "N", "N", "X", "X", "X", "D",
    "D", "D", "D", "D", "X", "X", "X",
    "X", "N", "N", "N", "N", "X", "X",
    "X", "X", "D", "D", "D", "D", "X",
    "X", "X", "X", "N", "N", "N", "N",
    "N", "X", "X", "X", "D", "D", "D"
]

# Generar horarios para cada usuario con sus respectivos inicios en el patrón
horario_usuario1 = generar_horario_personalizado(inicio, fin, patron_fijo, 0)
horario_usuario2 = generar_horario_personalizado(inicio, fin, patron_fijo, 7)
horario_usuario3 = generar_horario_personalizado(inicio, fin, patron_fijo, 14)
horario_usuario4 = generar_horario_personalizado(inicio, fin, patron_fijo, 28)
horario_usuario5 = generar_horario_personalizado(inicio, fin, patron_fijo, 35)


# Mostrar los resultados
print("Horario Usuario 1:")
for dia in horario_usuario1:
    print(dia)

print("\nHorario Usuario 2:")
for dia in horario_usuario2:
    print(dia)

print("\nHorario Usuario 3:")
for dia in horario_usuario3:
    print(dia)

print("\nHorario Usuario 4:")
for dia in horario_usuario4:
    print(dia)

print("\nHorario Usuario 5:")
for dia in horario_usuario5:
    print(dia)