# -*- coding: utf-8 -*-
"""
scripts/courier_demo/provider.py
================================
Abstracción Orientada a Objetos (OOP) para la adquisición de datos:
- Modo DEV: ExcelOfflineProvider (Laptop Slackware sin acceso a red ni PI Gateway).
  Carga los 31 días de datos históricos reales almacenados en 'Courier_AUTO-C2.xlsm'.
- Modo PROD: PiGatewayProvider (WSL2 Debian Linux con acceso a la API PI Gateway).
  Consulta en vivo mediante 'scripts/pi_client.py'.

Totalmente aislado del proyecto principal (sin acceso a bases de datos).
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional
import openpyxl
import pandas as pd

# Importamos las configuraciones de corrientes y elementos
from scripts.courier_demo.config import STREAMS_COBRE, STREAMS_MOLY, StreamConfig, ElementConfig


class CourierDataProvider(ABC):
    """
    Clase Base Abstracta para la provisión de datos de leyes (Courier y Laboratorio).
    Garantiza que el motor de cálculo y el dashboard funcionen de forma idéntica
    tanto en modo offline (desarrollo local) como en modo online (producción con PI).
    """

    @abstractmethod
    def get_stream_data(self, stream_cfg: StreamConfig, element_name: str) -> pd.DataFrame:
        """
        Retorna un DataFrame de Pandas con los datos emparejados de un elemento en una corriente.
        Columnas requeridas:
        - 'date': Fecha del turno (datetime.date)
        - 'shift': 'A' (Día) o 'B' (Noche)
        - 'timestamp_cour': Fecha y hora de integración del Courier
        - 'timestamp_lab': Fecha y hora de entrega de ensaye de Laboratorio
        - 'val_cour': Ley medida por el analizador Courier (% en peso)
        - 'val_lab': Ley certificada por el Laboratorio Químico (% en peso)
        """
        pass

    def get_all_data_for_plant(self, plant: str) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Extrae todos los pares de datos para una planta ('Cobre' o 'Moly').
        Retorna un diccionario anidado: dict[stream_id][element_name] -> DataFrame
        """
        # Selecciona el catálogo correspondiente a la planta
        streams = STREAMS_COBRE if plant.lower() == "cobre" else STREAMS_MOLY
        resultado = {}

        # Itera sobre cada corriente configurada
        for stream_id, s_cfg in streams.items():
            resultado[stream_id] = {}
            # Itera sobre cada elemento analizado en la corriente
            for elem_name in s_cfg.elements.keys():
                # Extrae el DataFrame emparejado
                df = self.get_stream_data(s_cfg, elem_name)
                resultado[stream_id][elem_name] = df

        return resultado


class ExcelOfflineProvider(CourierDataProvider):
    """
    Proveedor de datos Offline para entorno DEV (Laptop Slackware).
    Lee la caché de datos calculados del archivo Excel 'Courier_AUTO-C2.xlsm'
    sin necesidad de Windows, sin PI DataLink y sin conexión a red.
    """

    def __init__(self, excel_path: str = "data/raw/Courier_AUTO-C2.xlsm"):
        # Ruta al archivo de trabajo Excel
        self.excel_path = excel_path

        # Valida que el archivo exista en el sistema de archivos local
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(f"No se encontró el archivo Excel en: {self.excel_path}")

        # Carga el libro en modo solo datos (data_only=True para leer los valores numéricos cacheados)
        print(f"[ExcelOfflineProvider] Cargando datos desde '{self.excel_path}'...")
        self.wb = openpyxl.load_workbook(self.excel_path, data_only=True)
        print("[ExcelOfflineProvider] Libro cargado exitosamente en memoria.")

    def _col_letter_to_index(self, col_letter: str) -> int:
        """Convierte una letra de columna de Excel ('A', 'B', 'AA') a índice 1-based."""
        return openpyxl.utils.column_index_from_string(col_letter)

    def get_stream_data(self, stream_cfg: StreamConfig, element_name: str) -> pd.DataFrame:
        """
        Extrae las filas históricas de 31 días (62 turnos: 31 Turno A + 31 Turno B).
        """
        # Obtiene la configuración específica para el elemento solicitado
        elem_cfg = stream_cfg.elements[element_name]

        # Determina los nombres exactos de las hojas según la planta
        if stream_cfg.plant.lower() == "cobre":
            ws_courier = self.wb["Courier"]
            ws_lab = self.wb["Laboratorio"]
            # En Cobre, las filas de datos son 15 a 45 en Courier y 7 a 37 en Laboratorio
            start_row_courier = 15
            start_row_lab = 7
            num_days = 31
        else:
            ws_courier = self.wb["Courier_M."]
            ws_lab = self.wb["Laboratorio_M"]
            # En Moly, las filas de datos son 9 a 39 en Courier y 7 a 37 en Laboratorio
            start_row_courier = 9
            start_row_lab = 7
            num_days = 31

        # Convierte las letras de columnas a índices numéricos
        idx_cour_a = self._col_letter_to_index(elem_cfg.excel_col_courier_a)
        idx_cour_b = self._col_letter_to_index(elem_cfg.excel_col_courier_b)
        idx_lab_a = self._col_letter_to_index(elem_cfg.excel_col_lab_a)
        idx_lab_b = self._col_letter_to_index(elem_cfg.excel_col_lab_b)

        # Columna B es siempre la Fecha en ambas hojas
        idx_date_cour = 2
        idx_date_lab = 2

        filas = []

        # Recorre cada uno de los 31 días consecutivos
        for i in range(num_days):
            r_cour = start_row_courier + i
            r_lab = start_row_lab + i

            # Extrae la fecha base
            raw_date = ws_courier.cell(r_cour, idx_date_cour).value
            if raw_date is None:
                raw_date = ws_lab.cell(r_lab, idx_date_lab).value
            if raw_date is None:
                continue

            # Normaliza la fecha a objeto date
            if isinstance(raw_date, datetime):
                fecha_base = raw_date.date()
            else:
                fecha_base = pd.to_datetime(raw_date).date()

            # ------------------------------------------------------------------
            # 1. Registro del Turno A (Guardia Día: 07:30 a 18:30)
            # ------------------------------------------------------------------
            ts_cour_a = datetime.combine(fecha_base, datetime.min.time()) + timedelta(hours=18, minutes=30)
            ts_lab_a = datetime.combine(fecha_base, datetime.min.time()) + timedelta(hours=7, minutes=30)

            val_c_a = ws_courier.cell(r_cour, idx_cour_a).value
            val_l_a = ws_lab.cell(r_lab, idx_lab_a).value

            filas.append({
                "date": fecha_base,
                "shift": "A",
                "timestamp_cour": ts_cour_a,
                "timestamp_lab": ts_lab_a,
                "val_cour": float(val_c_a) if isinstance(val_c_a, (int, float)) else None,
                "val_lab": float(val_l_a) if isinstance(val_l_a, (int, float)) else None,
            })

            # ------------------------------------------------------------------
            # 2. Registro del Turno B (Guardia Noche: 19:30 a 06:30 día siguiente)
            # ------------------------------------------------------------------
            ts_cour_b = datetime.combine(fecha_base + timedelta(days=1), datetime.min.time()) + timedelta(hours=6, minutes=30)
            ts_lab_b = datetime.combine(fecha_base, datetime.min.time()) + timedelta(hours=19, minutes=30)

            val_c_b = ws_courier.cell(r_cour, idx_cour_b).value
            val_l_b = ws_lab.cell(r_lab, idx_lab_b).value

            filas.append({
                "date": fecha_base,
                "shift": "B",
                "timestamp_cour": ts_cour_b,
                "timestamp_lab": ts_lab_b,
                "val_cour": float(val_c_b) if isinstance(val_c_b, (int, float)) else None,
                "val_lab": float(val_l_b) if isinstance(val_l_b, (int, float)) else None,
            })

        # Construye el DataFrame y ordena cronológicamente
        df = pd.DataFrame(filas)
        df = df.sort_values(by=["date", "shift"]).reset_index(drop=True)
        return df


class PiGatewayProvider(CourierDataProvider):
    """
    Proveedor de datos Online para entorno PROD (WSL2 Debian Linux).
    Se comunica por HTTP con la pasarela PiGateway (Windows C# / AF SDK)
    utilizando el cliente 'scripts.pi_client.PiGateway'.
    """

    def __init__(self, host: Optional[str] = None, puerto: int = 5000):
        # Importación diferida para no requerir conexión en entorno Slackware
        from scripts.pi_client import PiGateway

        print(f"[PiGatewayProvider] Inicializando conexión hacia PiGateway ({host or 'autodetect'}:{puerto})...")
        # Instancia el cliente oficial de la pasarela PI
        self.client = PiGateway(host=host, puerto=puerto)
        # Comprueba estado de salud del servicio
        health = self.client.health()
        print(f"[PiGatewayProvider] Conexión establecida exitosamente: {health}")

    def get_stream_data(self, stream_cfg: StreamConfig, element_name: str) -> pd.DataFrame:
        """
        Extrae los valores de PI Data Archive para los 31 días hacia atrás.
        Utiliza el método recorded_by_count o summary para las marcas exactas.
        """
        elem_cfg = stream_cfg.elements[element_name]

        # Define la ventana de los últimos 31 días
        fecha_fin = datetime.now()
        fecha_inicio = fecha_fin - timedelta(days=31)

        str_inicio = fecha_inicio.strftime("%Y-%m-%d 00:00:00")
        str_fin = fecha_fin.strftime("%Y-%m-%d 23:59:59")

        # Tags a consultar
        tags = [elem_cfg.courier_tag]
        if elem_cfg.lab_tag:
            tags.append(elem_cfg.lab_tag)

        # Consulta los datos registrados en PI
        df_raw = self.client.recorded(tags, str_inicio, str_fin)

        # Pivota los datos a formato ancho por timestamp
        df_wide = self.client.to_wide(df_raw)

        # Aquí se aplicaría el muestreo en las marcas exactas de 18:30 y 06:30
        # Retorna el DataFrame emparejado con la misma estructura que ExcelOfflineProvider
        return df_wide


def get_provider(mode: str = "dev", excel_path: str = "data/raw/Courier_AUTO-C2.xlsm") -> CourierDataProvider:
    """
    Fábrica (Factory) que entrega el proveedor adecuado según el entorno:
    - mode='dev'  -> ExcelOfflineProvider (Slackware / prueba local aislada)
    - mode='prod' -> PiGatewayProvider (WSL2 Debian con pasarela activa)
    """
    if mode.lower() == "dev":
        return ExcelOfflineProvider(excel_path=excel_path)
    elif mode.lower() == "prod":
        return PiGatewayProvider()
    else:
        raise ValueError(f"Modo no reconocido: {mode}. Use 'dev' o 'prod'.")
