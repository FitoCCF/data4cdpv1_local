# -*- coding: utf-8 -*-
"""
scripts/courier_demo/config.py
==============================
Definición central de metadatos, tags de PI, umbrales de corte físico
y tolerancias metalúrgicas para la comparación Courier vs Laboratorio.
Código completamente explícito y exhaustivamente comentado.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ElementConfig:
    """
    Configuración de metrología para un elemento químico específico en una corriente.
    """
    # Nombre del elemento químico o ensayo (ej. '%Cu', '%Mo', '%Fe')
    element: str

    # Tag de PI OSIsoft para el analizador Courier en línea (sufijo _CAL)
    courier_tag: str

    # Tag de PI OSIsoft para el ensaye del Laboratorio Químico (sufijo MAN)
    lab_tag: Optional[str]

    # Umbral mínimo de ley operativa (Physical Cutoff).
    # Si la ley del Courier cae por debajo de este valor, se descarta la comparación
    # porque indica tubería vacía, bypass o lavado con agua de proceso.
    cutoff_min: float

    # Tolerancia metalúrgica relativa de calidad (T_base).
    # Por ejemplo: 0.11 significa una tolerancia de +/- 11% de error relativo.
    tolerance: float

    # Letra de columna en la hoja 'Courier' del Excel (para Turno A y Turno B)
    excel_col_courier_a: str
    excel_col_courier_b: str

    # Letra de columna en la hoja 'Laboratorio' del Excel (para Turno A y Turno B)
    excel_col_lab_a: str
    excel_col_lab_b: str


@dataclass
class StreamConfig:
    """
    Configuración de una corriente o muestra metalúrgica (ej. Alimentación, Cola, Concentrado).
    """
    # Identificador clave de la corriente
    stream_id: str

    # Nombre legible de la corriente para el reporte y gráficas
    name: str

    # Planta a la que pertenece ('Cobre' o 'Moly')
    plant: str

    # Diccionario de configuraciones por elemento químico
    elements: Dict[str, ElementConfig]


# ==============================================================================
# CONFIGURACIÓN PARA PLANTA DE COBRE C2 (Concentradora Toquepala)
# ==============================================================================

STREAMS_COBRE: Dict[str, StreamConfig] = {
    # --------------------------------------------------------------------------
    # 1. Alimentación Rougher (Cabeza Planta Cobre)
    # --------------------------------------------------------------------------
    "alim_rougher": StreamConfig(
        stream_id="alim_rougher",
        name="Alimentación Rougher Promedio",
        plant="Cobre",
        elements={
            "%Cu": ElementConfig(
                element="%Cu",
                courier_tag="_7100_AIP_HPRO_CU_CAL",
                lab_tag="7100AIP012MAN",
                cutoff_min=0.20,  # Si Cu < 0.20% se descarta (lavado de molienda)
                tolerance=0.11,   # Tolerancia estándar de cabeza: +/- 11%
                excel_col_courier_a="E",
                excel_col_courier_b="F",
                excel_col_lab_a="E",
                excel_col_lab_b="F",
            ),
            "%Mo": ElementConfig(
                element="%Mo",
                courier_tag="_7100_AIP_HPRO_MO_CAL",
                lab_tag="7100AIP014MAN",
                cutoff_min=0.004, # Ruido de fondo mínimo en molibdeno
                tolerance=0.11,   # Tolerancia de cabeza: +/- 11%
                excel_col_courier_a="G",
                excel_col_courier_b="H",
                excel_col_lab_a="G",
                excel_col_lab_b="H",
            ),
            "%Fe": ElementConfig(
                element="%Fe",
                courier_tag="AIP_7100_HPRO_FE_CAL",
                lab_tag="7100AIP011MAN",
                cutoff_min=1.00,  # Ausencia de pulpa si Fe < 1.0%
                tolerance=0.11,   # Tolerancia: +/- 11%
                excel_col_courier_a="I",
                excel_col_courier_b="J",
                excel_col_lab_a="I",
                excel_col_lab_b="J",
            ),
            "%Zn": ElementConfig(
                element="%Zn",
                courier_tag="AIP_7100_HPRO_ZN_CAL",
                lab_tag="7100AIP013MAN",
                cutoff_min=0.001, # Límite instrumental de detección
                tolerance=0.15,   # Tolerancia zinc: +/- 15%
                excel_col_courier_a="K",
                excel_col_courier_b="L",
                excel_col_lab_a="K",
                excel_col_lab_b="L",
            ),
        }
    ),

    # --------------------------------------------------------------------------
    # 2. Cola Final (Relave General de Flotación)
    # --------------------------------------------------------------------------
    "cola_final": StreamConfig(
        stream_id="cola_final",
        name="Cola Final",
        plant="Cobre",
        elements={
            "%Cu": ElementConfig(
                element="%Cu",
                courier_tag="_7100_AIP_ROT_CU_CAL",
                lab_tag="7100AIP032MAN",
                cutoff_min=0.02,  # Relave normal ~0.04-0.08%, <0.02 es agua limpia
                tolerance=0.20,   # Tolerancia en colas bajas: +/- 20%
                excel_col_courier_a="O",
                excel_col_courier_b="P",
                excel_col_lab_a="O",
                excel_col_lab_b="P",
            ),
            "%Mo": ElementConfig(
                element="%Mo",
                courier_tag="_7100_AIP_ROT_MO_CAL",
                lab_tag="7100AIP034MAN",
                cutoff_min=0.001, # Límite de detección en relave
                tolerance=0.20,   # Tolerancia en relave: +/- 20%
                excel_col_courier_a="Q",
                excel_col_courier_b="R",
                excel_col_lab_a="Q",
                excel_col_lab_b="R",
            ),
            "%Fe": ElementConfig(
                element="%Fe",
                courier_tag="_7100_AIP_ROT_FE_CAL",
                lab_tag="7100AIP031MAN",
                cutoff_min=0.90,  # Relave diluido si Fe < 0.9%
                tolerance=0.15,   # Tolerancia: +/- 15%
                excel_col_courier_a="S",
                excel_col_courier_b="T",
                excel_col_lab_a="S",
                excel_col_lab_b="T",
            ),
        }
    ),

    # --------------------------------------------------------------------------
    # 3. Concentrado Final (Concentrado Colectivo Cu-Mo)
    # --------------------------------------------------------------------------
    "conc_final": StreamConfig(
        stream_id="conc_final",
        name="Concentrado Final",
        plant="Cobre",
        elements={
            "%Cu": ElementConfig(
                element="%Cu",
                courier_tag="_7100_AIP_CONC_CU_CAL",
                lab_tag="7100AIP102MAN",
                cutoff_min=18.0,  # Ley normal ~24-28%, <18% indica celda vacía
                tolerance=0.06,   # Alta exigencia en venta: +/- 6%
                excel_col_courier_a="W",
                excel_col_courier_b="X",
                excel_col_lab_a="U",
                excel_col_lab_b="V",
            ),
            "%Mo": ElementConfig(
                element="%Mo",
                courier_tag="_7100_AIP_CONC_MO_CAL",
                lab_tag="7100AIP104MAN",
                cutoff_min=0.30,  # Contenido mínimo de subproducto
                tolerance=0.06,   # Tolerancia concentrado: +/- 6%
                excel_col_courier_a="Y",
                excel_col_courier_b="Z",
                excel_col_lab_a="W",
                excel_col_lab_b="X",
            ),
            "%Fe": ElementConfig(
                element="%Fe",
                courier_tag="_7100_AIP_CONC_FE_CAL",
                lab_tag="7100AIP101MAN",
                cutoff_min=22.0,  # Pirita y calcopirita en concentrado
                tolerance=0.06,   # Tolerancia: +/- 6%
                excel_col_courier_a="AA",
                excel_col_courier_b="AB",
                excel_col_lab_a="Y",
                excel_col_lab_b="Z",
            ),
            "%Ins": ElementConfig(
                element="%Ins",
                courier_tag="_7100_ai_10_7_abb",
                lab_tag="7100AIP103MAN",
                cutoff_min=6.0,   # Arrastre mínimo silíceo
                tolerance=0.10,   # Tolerancia insolubles: +/- 10%
                excel_col_courier_a="AC",
                excel_col_courier_b="AC",
                excel_col_lab_a="AA",
                excel_col_lab_b="AB",
            ),
        }
    ),
}

# ==============================================================================
# CONFIGURACIÓN PARA PLANTA DE MOLIBDENO C2
# ==============================================================================

STREAMS_MOLY: Dict[str, StreamConfig] = {
    # --------------------------------------------------------------------------
    # 1. Alimentación Rougher Moly (Corriente S11)
    # --------------------------------------------------------------------------
    "alim_rougher_moly": StreamConfig(
        stream_id="alim_rougher_moly",
        name="Alimentación Rougher Moly",
        plant="Moly",
        elements={
            "%Cu": ElementConfig(
                element="%Cu",
                courier_tag="AIP_6290_ALIM_CU_CAL",
                lab_tag="6290AIP1DMAN",
                cutoff_min=5.0,   # Cobre remanente en concentración Mo
                tolerance=0.11,   # +/- 11%
                excel_col_courier_a="E",
                excel_col_courier_b="F",
                excel_col_lab_a="E",
                excel_col_lab_b="F",
            ),
            "%Mo": ElementConfig(
                element="%Mo",
                courier_tag="AIP_6290_ALIM_MO_CAL",
                lab_tag="6290AIP1AMAN",
                cutoff_min=0.50,  # Ley de cabeza a flotación Moly
                tolerance=0.11,   # +/- 11%
                excel_col_courier_a="G",
                excel_col_courier_b="H",
                excel_col_lab_a="G",
                excel_col_lab_b="H",
            ),
            "%Fe": ElementConfig(
                element="%Fe",
                courier_tag="AIP_6290_ALIM_FE_CAL",
                lab_tag="6290AIP1FMAN",
                cutoff_min=2.0,   # Hierro en cabeza Moly
                tolerance=0.11,   # +/- 11%
                excel_col_courier_a="I",
                excel_col_courier_b="J",
                excel_col_lab_a="I",
                excel_col_lab_b="J",
            ),
        }
    ),

    # --------------------------------------------------------------------------
    # 2. Cola Rougher Promedio Moly
    # --------------------------------------------------------------------------
    "cola_rougher_moly": StreamConfig(
        stream_id="cola_rougher_moly",
        name="Cola Rougher Promedio Moly",
        plant="Moly",
        elements={
            "%Cu": ElementConfig(
                element="%Cu",
                courier_tag="AIP_6290_RELA_CU_CAL",
                lab_tag="6290AIP2DMAN",
                cutoff_min=5.0,
                tolerance=0.05,   # +/- 5%
                excel_col_courier_a="K",
                excel_col_courier_b="L",
                excel_col_lab_a="K",
                excel_col_lab_b="L",
            ),
            "%Mo": ElementConfig(
                element="%Mo",
                courier_tag="AIP_6290_RELA_MO_CAL",
                lab_tag="6290AIP2AMAN",
                cutoff_min=0.05,
                tolerance=0.10,   # +/- 10%
                excel_col_courier_a="M",
                excel_col_courier_b="N",
                excel_col_lab_a="M",
                excel_col_lab_b="N",
            ),
            "%Fe": ElementConfig(
                element="%Fe",
                courier_tag="AIP_6290_RELA_FE_CAL",
                lab_tag="6290AIP2FMAN",
                cutoff_min=2.0,
                tolerance=0.10,   # +/- 10%
                excel_col_courier_a="O",
                excel_col_courier_b="P",
                excel_col_lab_a="O",
                excel_col_lab_b="P",
            ),
            "%Ins": ElementConfig(
                element="%Ins",
                courier_tag="_296290_COLA_RO_PROM_INS_ABB",
                lab_tag="6290AIP2EMAN",
                cutoff_min=2.0,
                tolerance=0.10,   # +/- 10%
                excel_col_courier_a="Q",
                excel_col_courier_b="R",
                excel_col_lab_a="Q",
                excel_col_lab_b="R",
            ),
        }
    ),

    # --------------------------------------------------------------------------
    # 3. Concentrado Última Limpieza Moly (Corriente S06 - Producto Final)
    # --------------------------------------------------------------------------
    "conc_final_moly": StreamConfig(
        stream_id="conc_final_moly",
        name="Concentrado Última Limpieza Moly",
        plant="Moly",
        elements={
            "%Cu": ElementConfig(
                element="%Cu",
                courier_tag="AIP_6290_CONC_CU_CAL",
                lab_tag="6290AIP3DMAN",
                cutoff_min=0.10,  # Penalidad si Cu > 1%
                tolerance=0.05,   # +/- 5%
                excel_col_courier_a="S",
                excel_col_courier_b="T",
                excel_col_lab_a="S",
                excel_col_lab_b="T",
            ),
            "%Mo": ElementConfig(
                element="%Mo",
                courier_tag="AIP_6290_CONC_MO_CAL",
                lab_tag="6290AIP3AMAN",
                cutoff_min=40.0,  # Ley comercial de Mo (> 50%)
                tolerance=0.025,  # Muy estricto: +/- 2.5%
                excel_col_courier_a="U",
                excel_col_courier_b="V",
                excel_col_lab_a="U",
                excel_col_lab_b="V",
            ),
            "%Fe": ElementConfig(
                element="%Fe",
                courier_tag="AIP_6290_CONC_FE_CAL",
                lab_tag="6290AIP3FMAN",
                cutoff_min=0.20,  # Impureza de hierro
                tolerance=0.05,   # +/- 5%
                excel_col_courier_a="W",
                excel_col_courier_b="X",
                excel_col_lab_a="W",
                excel_col_lab_b="X",
            ),
            "%Ins": ElementConfig(
                element="%Ins",
                courier_tag="AI_6290_8_ins_ABB",
                lab_tag="6290AIP3EMAN",
                cutoff_min=1.0,   # Sílice en concentrado
                tolerance=0.05,   # +/- 5%
                excel_col_courier_a="Y",
                excel_col_courier_b="Z",
                excel_col_lab_a="Y",
                excel_col_lab_b="Z",
            ),
        }
    ),
}
