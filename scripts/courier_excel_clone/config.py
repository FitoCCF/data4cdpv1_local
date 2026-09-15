# -*- coding: utf-8 -*-
"""
scripts/courier_excel_clone/config.py
=====================================
Constantes, colores institucionales de Excel, metadatos y definiciones de flujos
para replicar exactamente el libro 'Courier_AUTO-C2.xlsm'.
No incluye ningún cálculo ajeno a lo que muestra el archivo Excel.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


# ==============================================================================
# PALETA DE COLORES EXACTA DE EXCEL (Según Índices de Paleta Clásica)
# ==============================================================================
COLOR_EXCEL_GRAY_HEADER = "#C0C0C0"      # Índice 22: Gris/Plata (Encabezados de sección)
COLOR_EXCEL_CYAN_SUB = "#CCFFFF"         # Índice 41: Cian Claro (Diferencia-%Dif., Horas, Guardia)
COLOR_EXCEL_YELLOW_ELEM = "#FFFF99"      # Índice 43: Amarillo Claro (%Cu, %Mo, %Fe, %Zn, etc.)
COLOR_EXCEL_PEACH_REC = "#FFCC99"        # Índice 47: Durazno Claro (Recuperación Cu, Mo)
COLOR_EXCEL_RED_DIF = "#FF0000"          # Texto Rojo para valores de Diferencia (Lab - Courier)
COLOR_EXCEL_GRID = "#C0C0C0"             # Borde de celdas de Excel
COLOR_EXCEL_BG = "#FFFFFF"               # Fondo blanco de celdas de datos

# Títulos exactos del archivo Excel
TITLE_COBRE = "Comparación Courier Planta de Cobre C2 - Laboratorio"
TITLE_MOLY = "Comparación Courier Planta de Moly C2 - Laboratorio"
LABEL_DIF_PCT = "Diferencia-%Dif."
LABEL_STD_DEV = "DIFERENCIA LABORATORIO vs COURIER - DESVIACION ESTANDAR (%)"
LABEL_ULTIMOS_31 = "ULTIMOS 31 DIAS"


# ==============================================================================
# CONFIGURACIÓN DE ELEMENTOS Y TOLERANCIAS DEL EXCEL
# ==============================================================================
@dataclass
class ElementDef:
    element: str          # '%Cu', '%Mo', '%Fe', '%Zn', '%Ins', '%Ox'
    courier_tag: str      # Tag de Courier en PI
    lab_tag: Optional[str]# Tag de Laboratorio en PI
    tolerance: float      # Tolerancia metalúrgica T_base (ej. 0.11 para 11%)
    decimals: int         # Decimales a mostrar en tabla


@dataclass
class StreamDef:
    stream_id: str
    name: str             # Título tal como aparece en Portada
    plant: str            # 'Cobre' o 'Moly'
    elements: Dict[str, ElementDef]


# Definición exacta para Planta Cobre C2
STREAMS_COBRE: Dict[str, StreamDef] = {
    "alim_rougher": StreamDef(
        stream_id="alim_rougher",
        name="Alimentación Rougher Promedio",
        plant="Cobre",
        elements={
            "%Cu": ElementDef("%Cu", "_7100_AIP_HPRO_CU_CAL", "7100AIP012MAN", 0.11, 3),
            "%Mo": ElementDef("%Mo", "_7100_AIP_HPRO_MO_CAL", "7100AIP014MAN", 0.11, 3),
            "%Fe": ElementDef("%Fe", "AIP_7100_HPRO_FE_CAL", "7100AIP011MAN", 0.11, 3),
            "%Zn": ElementDef("%Zn", "AIP_7100_HPRO_ZN_CAL", "7100AIP013MAN", 0.11, 3),
            "%Ox": ElementDef("%Ox", "", None, 0.11, 3),
        }
    ),
    "cola_final": StreamDef(
        stream_id="cola_final",
        name="Cola Final",
        plant="Cobre",
        elements={
            "%Cu": ElementDef("%Cu", "_7100_AIP_ROT_CU_CAL", "7100AIP032MAN", 0.20, 3),
            "%Mo": ElementDef("%Mo", "_7100_AIP_ROT_MO_CAL", "7100AIP034MAN", 0.20, 3),
            "%Fe": ElementDef("%Fe", "_7100_AIP_ROT_FE_CAL", "7100AIP031MAN", 0.20, 3),
        }
    ),
    "conc_final": StreamDef(
        stream_id="conc_final",
        name="Concentrado Final",
        plant="Cobre",
        elements={
            "%Cu": ElementDef("%Cu", "_7100_AIP_CONC_CU_CAL", "7100AIP102MAN", 0.06, 2),
            "%Mo": ElementDef("%Mo", "_7100_AIP_CONC_MO_CAL", "7100AIP104MAN", 0.06, 3),
            "%Fe": ElementDef("%Fe", "_7100_AIP_CONC_FE_CAL", "7100AIP101MAN", 0.06, 2),
            "%Ins": ElementDef("%Ins", "_7100_ai_10_7_abb", "7100AIP103MAN", 0.10, 2),
            "%Ox": ElementDef("%Ox", "", None, 0.06, 3),
        }
    ),
}

# Definición exacta para Planta Molibdeno C2
STREAMS_MOLY: Dict[str, StreamDef] = {
    "alim_rougher_moly": StreamDef(
        stream_id="alim_rougher_moly",
        name="Alimentación Rougher",
        plant="Moly",
        elements={
            "%Cu": ElementDef("%Cu", "AIP_6290_ALIM_CU_CAL", "6290AIP1DMAN", 0.11, 3),
            "%Mo": ElementDef("%Mo", "AIP_6290_ALIM_MO_CAL", "6290AIP1AMAN", 0.11, 3),
            "%Fe": ElementDef("%Fe", "AIP_6290_ALIM_FE_CAL", "6290AIP1FMAN", 0.11, 3),
        }
    ),
    "cola_rougher_moly": StreamDef(
        stream_id="cola_rougher_moly",
        name="Cola Rougher Promedio",
        plant="Moly",
        elements={
            "%Cu": ElementDef("%Cu", "AIP_6290_RELA_CU_CAL", "6290AIP2DMAN", 0.05, 3),
            "%Mo": ElementDef("%Mo", "AIP_6290_RELA_MO_CAL", "6290AIP2AMAN", 0.10, 3),
            "%Fe": ElementDef("%Fe", "AIP_6290_RELA_FE_CAL", "6290AIP2FMAN", 0.10, 3),
        }
    ),
    "conc_final_moly": StreamDef(
        stream_id="conc_final_moly",
        name="Concentrado Ultima limpieza",
        plant="Moly",
        elements={
            "%Cu": ElementDef("%Cu", "AIP_6290_CONC_CU_CAL", "6290AIP3DMAN", 0.05, 3),
            "%Mo": ElementDef("%Mo", "AIP_6290_CONC_MO_CAL", "6290AIP3AMAN", 0.025, 2),
            "%Fe": ElementDef("%Fe", "AIP_6290_CONC_FE_CAL", "6290AIP3FMAN", 0.05, 3),
            "%Ins": ElementDef("%Ins", "AI_6290_8_ins_ABB", "6290AIP3EMAN", 0.05, 2),
            "%Ox": ElementDef("%Ox", "", None, 0.05, 3),
        }
    ),
}

# Flujos intermedios monitoreados en Portada
INTERMEDIATE_STREAMS_COBRE = [
    ("REBOSE HIDROCICLONES L1", "_7100_ai_01_2_CAL", "_7100_ai_01_4_CAL"),
    ("REBOSE HIDROCICLONES L2", "_7100_ai_02_2_CAL", "_7100_ai_02_4_CAL"),
    ("RELAVE FINAL", "_7100_AIQ_ROT_CU_CAL", "_7100_AIQ_ROT_MO_CAL"),
    ("RELAVE AGOTATIVO L1", "_7100_AIQ_RAG1_CU_CAL", "_7100_AIQ_RAG1_MO_CAL"),
    ("RELAVE AGOTATIVO L2", "_7100_AIQ_RAG2_CU_CAL", "_7100_AIQ_RAG2_MO_CAL"),
    ("CONCENTRADO 2DA LIMPIEZA L1", "_7100_AIQ_CLIM1_CU_CAL", "_7100_AIQ_CLIM1_MO_CAL"),
    ("CONCENTRADO 2DA LIMPIEZA L2", "_7100_AIQ_CLIM2_CU_CAL", "_7100_AIQ_CLIM2_MO_CAL"),
    ("CONCENTRADO COLECTIVO", "_7100_AIQ_CONC_CU_CAL", "_7100_AIQ_CONC_MO_CAL"),
    ("CONCENTRADO PRIMARIO L1", "_7100_AIQ_CPRIM1_CU_CAL", "_7100_AIQ_CPRIM1_MO_CAL"),
    ("CONCENTRADO PRIMARIO L2", "_7100_AIQ_CPRIM2_CU_CAL", "_7100_AIQ_CPRIM2_MO_CAL"),
]

INTERMEDIATE_STREAMS_MOLY = [
    ("ALIM. ROUGHER", "", ""),
    ("CONC. 8VA LIMPIEZA", "AIQ_6290_CONC_CU_CAL", "AIQ_6290_CONC_MO_CAL"),
]
