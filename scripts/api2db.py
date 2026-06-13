# Shebang para permitir ejecutar el script directamente.
#!/usr/bin/env python3

# Docstring informativa sobre la finalidad del script.
"""
Fetch assay data from the CLB API and insert it into `works4cdp_assay`.

The script expects the `samples` table to contain the mapping between tags and
IDs that should be used as the `sample_id` in `works4cdp_assay`.
"""

# Import futuro para habilitar anotaciones diferidas en versiones antiguas de Python.
from __future__ import annotations

# Import del módulo logging para registrar mensajes.
import logging
# Import de os para acceder a variables de entorno y utilidades del sistema.
import os
# Import de datetime para manejar conversiones de fechas y horas.
from datetime import datetime
# Import de tipos genéricos para anotaciones de funciones y estructuras.
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Set

# Import de psycopg2 para conectarse a PostgreSQL.
import psycopg2
# Import de execute_batch para ejecutar inserciones masivas eficientes.
from psycopg2.extras import execute_batch
# Import de requests para comunicarnos con la API HTTP.
import requests

# Constante que define la plantilla de URL base de la API.
API_URL_TEMPLATE = "http://{ip}:7000/api/clb/file?name={tag}"

# Mapa de ID de equipo a dirección IP.
EQUIPMENT_IP_MAP = {
    5: "172.18.16.21",
    6: "172.18.16.20",
    2: "192.168.59.55",
    1: "192.168.59.53"
}




# Alias de tipo que describe la relación entre campo API, columna DB y conversor.
# El campo API puede ser un string o una tupla de strings (para múltiples candidatos).
FieldMapping = Tuple[Any, str, Any]



# Función auxiliar que convierte una cadena de fecha al formato ISO.
def parse_date(value: Optional[str]) -> Optional[str]:
    """Return yyyy-mm-dd for a value like '17.09.2025'."""
    value = clean_string(value)  # Normaliza la entrada eliminando N/A o vacíos.
    if value is None:  # Si no hay dato, regresamos None.
        return None

    known_formats = ("%d.%m.%Y", "%Y-%m-%d")  # Formatos soportados desde la API.
    for date_format in known_formats:  # Iteramos formatos conocidos.
        try:
            parsed = datetime.strptime(value, date_format).date()  # Parseo a date.
            return parsed.isoformat()  # Retornamos en formato ISO estándar.
        except ValueError:
            continue  # Si falla, probamos el siguiente formato.

    raise ValueError(f"Unsupported date format received from API: {value}")  # Notificación de formato inválido.


# Función auxiliar que convierte una cadena de hora al formato HH:MM:SS.
def parse_time(value: Optional[str]) -> Optional[str]:
    """Return HH:MM:SS from API hour strings."""
    value = clean_string(value)  # Normaliza la entrada.
    if value is None:  # Si está vacío, devolvemos None.
        return None
    try:
        parsed = datetime.strptime(value, "%H:%M:%S").time()  # Parseo a time.
        return parsed.isoformat()  # Devolvemos la hora en formato ISO.
    except ValueError as exc:
        raise ValueError(f"Unsupported time format received from API: {value}") from exc  # Error detallado.


# Función que transforma una cadena numérica a entero.
def parse_int(value: Optional[str]) -> Optional[int]:
    value = clean_string(value)  # Limpieza previa.
    if value is None:  # Si no hay valor, devolvemos None.
        return None
    return int(value)  # Convertimos a entero estándar.


# Función que transforma una cadena numérica a float.
def parse_float(value: Optional[str]) -> Optional[float]:
    value = clean_string(value)  # Limpieza previa.
    if value is None:  # Si no hay valor, devolvemos None.
        return None
    return float(value)  # Convertimos a flotante.


# Tupla que contiene la correspondencia campo API -> columna DB -> conversor.
FIELD_MAPPINGS: Tuple[FieldMapping, ...] = (
    ("date", "date", parse_date),    # Mapeo de la fecha.
    ("hour", "time", parse_time),    # Mapeo de la hora.
    ("instance", "instance", parse_int),  # Mapeo de la instancia.
    ("n1fe", "n1fe", parse_float),   # Mapeo del valor n1fe.
    ("n2cu", "n2cu", parse_float),   # Mapeo del valor n2cu.
    ("n3zn", "n3zn", parse_float),   # Mapeo del valor n3zn.
    ("n4mo", "n4mo", parse_float),   # Mapeo del valor n4mo.
    ("n5ech5", "n5ech5", parse_float),  # Mapeo del valor n5ech5.
    ("n5ech5", "n5ech5", parse_float),  # Mapeo del valor n5ech5.
    # Mapeo del valor n6 (n6sc, n6w_sc, n6kpsc).
    (("n6sc", "n6w_sc", "n6kpsc", "n6"), "n6sc", parse_float),
    ("n7ech7", "n7ech7", parse_float),  # Mapeo del valor n7ech7.
    ("a1fe", "a1fe", parse_float),   # Mapeo de a1fe.
    ("a2cu", "a2cu", parse_float),   # Mapeo de a2cu.
    ("a3zn", "a3zn", parse_float),   # Mapeo de a3zn.
    ("a5a5", "a5a5", parse_float),   # Mapeo de a5a5.
    # Mapeo de a6 (a6sol, a6sc, a6).
    (("a6sol", "a6sc", "a6"), "a6sol", parse_float),
    # Mapeo de a7 (a7a7, a7ins, a7).
    (("a7a7", "a7ins", "a7"), "a7a7", parse_float),
)

# Tupla que define el orden de columnas usado en la sentencia INSERT.
DB_COLUMNS: Tuple[str, ...] = (
    "sample_id",  # ID de la muestra (tabla samples).
    "date",       # Fecha de la medición.
    "time",       # Hora de la medición.
    "instance",   # Instancia asociada.
    "n1fe",       # Valor del campo n1fe.
    "n2cu",       # Valor del campo n2cu.
    "n3zn",       # Valor del campo n3zn.
    "n4mo",       # Valor del campo n4mo.
    "n5ech5",     # Valor del campo n5ech5.
    "n6sc",       # Valor del campo n6sc (original n6kpsc).
    "n7ech7",     # Valor del campo n7ech7.
    "a1fe",       # Valor del campo a1fe.
    "a2cu",       # Valor del campo a2cu.
    "a3zn",       # Valor del campo a3zn.
    "a5a5",       # Valor del campo a5a5.
    "a6sol",      # Valor del campo a6sol.
    "a7a7",       # Valor del campo a7a7.
    "timestamp",  # Timestamp requerido por TimescaleDB.

)


# Función que limpia cadenas y normaliza valores vacíos o "N/A".
def clean_string(value: Optional[str]) -> Optional[str]:
    """Normalise sentinel values ('N/A', '', None) to None."""
    if value is None:  # Si ya es None, retornamos None.
        return None
    normalized = value.strip()  # Eliminamos espacios en blanco.
    if not normalized or normalized.upper() == "N/A":  # Detectamos valores vacíos.
        return None
    return normalized  # Devolvemos la cadena limpia.


# Función que obtiene todas las entradas de la API para un tag específico en una IP específica.
def fetch_entries(session: requests.Session, tag: str, ip: str) -> Sequence[Mapping[str, Any]]:
    """Retrieve all payload entries for the provided tag from the given IP."""
    url = API_URL_TEMPLATE.format(ip=ip, tag=tag)  # Construimos la URL final para el tag e IP.
    logging.debug("Requesting %s", url)  # Mensaje de depuración con la URL solicitada.
    response = session.get(url, timeout=10)  # Llamada HTTP con tiempo máximo de espera.
    response.raise_for_status()  # Eleva excepción si la respuesta no fue exitosa.

    payload = response.json()  # Obtenemos el JSON devuelto por la API.
    key = tag.lower()  # La API usa claves en minúsculas.
    items = payload.get(key) or []  # Recuperamos la lista de registros para el tag.
    if not items:  # Si no hay datos, lo notificamos en el log.
        logging.warning("API response for %s did not contain data", tag)
    return items  # Devolvemos la lista (posiblemente vacía).


# Función que prepara una fila para insertarla en la base de datos.
def build_row(entry: Mapping[str, Any], sample_id: int) -> Dict[str, Any]:
    """Convert an API entry into a row ready to be inserted."""
    row: Dict[str, Any] = {"sample_id": sample_id}  # Inicializamos con el sample_id.

    for api_field, db_column, converter in FIELD_MAPPINGS:  # Iteramos cada mapeo.
        try:
            raw_value = None
            # Si api_field es una tupla, probamos cada llave en orden
            if isinstance(api_field, tuple):
                for key in api_field:
                    if key in entry:
                        raw_value = entry[key]
                        break
            else:
                raw_value = entry.get(api_field)  # Obtenemos el valor original.
            
            row[db_column] = converter(raw_value)  # Convertimos y guardamos en la columna destino.
        except Exception as exc:  # Capturamos cualquier error durante la conversión.
            logging.error(
                "Failed to convert field '%s' for sample_id %s: %s",
                api_field,
                sample_id,
                exc,
            )
            # raise  # Recomendación: No detener todo el proceso por un campo fallido, pero si es crítico mantener el raise.
            # En este contexto, si falla un campo, quizás queramos seguir o poner None. 
            # Mantendremos el comportamiento original de re-lanzar para ser seguros.
            raise

        # Calculamos el campo timestamp concatenando date y time para TimescaleDB
        date_val = row.get("date")
        time_val = row.get("time") or "00:00:00"
        if date_val:
            row["timestamp"] = f"{date_val} {time_val}.000000 +00:00"
        else:
            logging.error("Falta 'date' para sample_id %s, ignorando registro por restricción de TimescaleDB.", sample_id)
            raise ValueError("Missing 'date' field")

    return row  # Devolvemos el diccionario listo para insertar.


# Función que inserta múltiples filas en la tabla works4cdp_assay.
def insert_rows(conn_params: Mapping[str, Any], rows: Iterable[Mapping[str, Any]]) -> None:
    """Insert rows into works4cdp_assay using psycopg2's execute_batch."""
    rows = list(rows)  # Convertimos a lista para evaluar la cantidad.
    if not rows:  # Si no hay filas, no hacemos nada.
        logging.info("No rows to insert; skipping database work.")
        return

    placeholders = ", ".join(["%s"] * len(DB_COLUMNS))  # Generamos placeholders para los valores.
    column_list = ", ".join(DB_COLUMNS)  # Lista de columnas a insertar.
    sql = f"INSERT INTO works4cdp_assay ({column_list}) VALUES ({placeholders})"  # Sentencia SQL final.

    values = [tuple(row.get(column) for column in DB_COLUMNS) for row in rows]  # Construimos la matriz de valores.

    logging.info("Inserting %s rows into works4cdp_assay", len(values))  # Mensaje informativo.
    with psycopg2.connect(**conn_params) as connection:  # Abrimos conexión a la base.
        with connection.cursor() as cursor:  # Abrimos un cursor para ejecutar SQL.
            execute_batch(cursor, sql, values)  # Ejecutamos el insert masivo.
        connection.commit()  # Confirmamos la transacción para persistir los datos.


# Función que carga la configuración de muestras desde la base de datos.
def load_samples_config(conn_params: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    """Fetch sample configuration (id, tag, equipment_id) from works4cdp_sample."""
    query = "SELECT id, tag, equipment_id FROM works4cdp_sample WHERE tag IS NOT NULL"
    try:
        with psycopg2.connect(**conn_params) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                # Obtenemos todos los registros y los convertimos a diccionarios
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return results
    except Exception as exc:
        logging.error("Failed to load samples config from DB: %s", exc)
        return []

def load_existing_keys(conn_params: Mapping[str, Any]) -> Set[Tuple[int, str, str, int]]:
    """Fetch existing (sample_id, date, time, instance) tuples from works4cdp_assay."""
    query = "SELECT sample_id, to_char(date, 'YYYY-MM-DD'), to_char(time, 'HH24:MI:SS'), instance FROM works4cdp_assay"
    try:
        with psycopg2.connect(**conn_params) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                return set(cursor.fetchall())
    except Exception as exc:
        logging.error("Failed to load existing keys from DB: %s", exc)
        return set()



# Función que recorre todos los tags y compila las filas a insertar.
def collect_rows(session: requests.Session, db_settings: Dict[str, Any], existing_keys: Set[Tuple[int, str, str, int]]) -> List[Dict[str, Any]]:
    """Fetch and convert all sample rows from the API using DB configuration."""
    rows: List[Dict[str, Any]] = []  # Lista donde acumulamos filas listas para la BD.
    
    samples = load_samples_config(db_settings)
    if not samples:
        logging.warning("No samples configuration found in database.")
        return []

    for sample in samples:
        sample_id = sample['id']
        tag = sample['tag']
        equipment_id = sample['equipment_id']
        
        # Determinar IP basada en equipment_id
        ip = EQUIPMENT_IP_MAP.get(equipment_id)
        if not ip:
            logging.warning("Unknown equipment_id %s for tag %s. Skipping.", equipment_id, tag)
            continue

        try:
            entries = fetch_entries(session, tag, ip)  # Obtenemos las entradas para el tag actual.
        except Exception as exc:  # Manejamos cualquier falla de comunicación.
            logging.error("Request failed for tag %s (IP: %s): %s", tag, ip, exc)
            continue  # Saltamos al siguiente tag.

        if not entries:  # Si no hay datos, seguimos con el siguiente tag.
            continue

        for entry in entries:  # Procesamos cada registro recibido.
            try:
                row = build_row(entry, sample_id)  # Convertimos la entrada en una fila de BD.
            except Exception:  # Si build_row falló ya lo registró.
                continue  # Pasamos al siguiente registro.
            
            # Deduplication check
            key = (row['sample_id'], row['date'], row['time'], row['instance'])
            if key in existing_keys:
                continue

            rows.append(row)  # Agregamos la fila lista a la lista general.
    return rows  # Regresamos todas las filas recopiladas.


# Función que obtiene la configuración de la base desde variables de entorno.
def load_db_settings() -> Dict[str, Any]:
    """Read database connection settings from environment variables."""
    return {
        "host": os.getenv("DB_HOST", "localhost"),      # Host de la base.
        "port": int(os.getenv("DB_PORT", "5433")),      # Puerto de conexión.
        "database": os.getenv("DB_NAME", "mydb"),       # Nombre de la base.
        "user": os.getenv("DB_USER", "myuser"),         # Usuario de la base.
        "password": os.getenv("DB_PASSWORD", "mypassword"),  # Contraseña del usuario.
    }


# Función principal que orquesta el flujo completo.
def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),  # Nivel de log configurable.
        format="%(asctime)s %(levelname)s %(message)s",  # Formato estándar de logs.
    )

    db_settings = load_db_settings()  # Cargamos los parámetros de conexión.
    logging.debug(
        "Using database settings: host=%s db=%s",
        db_settings["host"],
        db_settings["database"],
    )

    with requests.Session() as session:  # Creamos una sesión HTTP reutilizable.
        existing_keys = load_existing_keys(db_settings)
        logging.info("Loaded %d existing keys", len(existing_keys))
        rows = collect_rows(session, db_settings, existing_keys)  # Recolectamos todas las filas desde la API.

    if not rows:  # Si no obtuvimos datos, lo advertimos y terminamos.
        logging.warning("No rows were collected from the API; nothing to insert.")
        return

    # print(rows[0])
    insert_rows(db_settings, rows)  # Insertamos las filas en la base de datos.
    logging.info("Finished loading %s rows into works4cdp_assay", len(rows))  # Mensaje final.


# Punto de entrada estándar en Python.
if __name__ == "__main__":
    main()  # Ejecutamos la función principal cuando el script se ejecuta directamente.
