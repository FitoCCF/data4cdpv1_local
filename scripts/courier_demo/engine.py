# -*- coding: utf-8 -*-
"""
scripts/courier_demo/engine.py
==============================
Motor analítico, metalúrgico y metrológico para la comparación Courier vs Laboratorio.

Funcionalidades implementadas:
1. Limpieza y filtrado por umbrales mínimos físicos (Physical Cutoffs).
2. Métricas de diferencia, error relativo porcentual y clasificación de tolerancias.
3. Prueba formal t de Student de Welch (con p-valor exacto, IC 95%, asimetría y curtosis).
4. Motor de Recalibración con Fundamento Matemático:
   - Regresión de Deming (Errors-in-Variables).
   - Descomposición de Deriva (Offset vs Ganancia).
   - Filtro Dinámico EWMA de sesgo para amortiguar ruido de turno.
   - Prescripción matemática de factores de corrección (K_gain y K_offset).

Código explícito, modular y comentado paso a paso.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from scripts.courier_demo.config import ElementConfig, StreamConfig


@dataclass
class TTestResult:
    """Estructura que almacena los resultados de la prueba t de Student."""
    n_obs: int                # Número de pares de turnos válidos
    mean_lab: float           # Media muestral de Laboratorio
    mean_cour: float          # Media muestral de Courier
    mean_dif: float           # Media del sesgo (Lab - Courier)
    std_dif: float            # Desviación estándar de las diferencias
    t_stat: float             # Estadístico t calculado
    p_value: float            # p-valor bilateral exacto
    t_crit_90: float          # Valor crítico t al 90% (alfa = 0.10)
    t_crit_95: float          # Valor crítico t al 95% (alfa = 0.05)
    t_crit_99: float          # Valor crítico t al 99% (alfa = 0.01)
    status_95: str            # 'Aceptado' (calibrado) o 'Rechazado' (sesgo)
    ci_95_lower: float        # Límite inferior del Intervalo de Confianza 95%
    ci_95_upper: float        # Límite superior del Intervalo de Confianza 95%
    skewness: float           # Coeficiente de Asimetría
    kurtosis: float           # Coeficiente de Curtosis


@dataclass
class CalibrationPrescription:
    """Estructura que prescribe la recalibración matemática óptima del Courier."""
    should_calibrate: bool    # Booleano: True si se recomienda calibrar, False si no tocar
    diagnosis: str            # Diagnóstico ('CALIBRADO', 'DERIVA_OFFSET', 'DERIVA_GANANCIA', 'DERIVA_COMBINADA')
    recommendation_text: str  # Explicación detallada para el metalurgista
    deming_slope: float       # Pendiente insesgada de Deming (Factor K_gain)
    deming_intercept: float   # Intercepto insesgado de Deming (Factor K_offset)
    r_squared: float          # Coeficiente de determinación r2
    ewma_current_bias: float  # Sesgo suavizado actual por filtro EWMA
    formula_str: str          # Representación en texto de la corrección sugerida


class CourierComparisonEngine:
    """
    Motor matemático que procesa los pares de datos temporales
    y genera todas las métricas estadísticas y metalúrgicas.
    """

    def __init__(self, stream_cfg: StreamConfig, elem_cfg: ElementConfig):
        self.stream_cfg = stream_cfg
        self.elem_cfg = elem_cfg

    def process_dataframe(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Toma el DataFrame crudo del proveedor y aplica:
        1. Filtro de corte mínimo físico (cutoff_min).
        2. Diferencia (Bias) = val_lab - val_cour.
        3. Error porcentual relativo = (|Dif| / val_lab) * 100.
        4. Clasificación de calidad: 'Aceptable', 'Regular', 'Malo'.
        """
        # Copiamos el DataFrame para no mutar el original
        df = df_raw.copy()

        # ----------------------------------------------------------------------
        # Paso 1: Aplicación del umbral de corte mínimo físico
        # Si la ley del Courier es menor que cutoff_min, la medición se invalida
        # (indica agua de lavado o detención de celdas/tuberías).
        # ----------------------------------------------------------------------
        cutoff = self.elem_cfg.cutoff_min
        df["is_valid"] = (
            df["val_cour"].notna()
            & df["val_lab"].notna()
            & (df["val_cour"] >= cutoff)
            & (df["val_lab"] > 0)
        )

        # ----------------------------------------------------------------------
        # Paso 2: Cálculo de diferencia absoluta y sesgo
        # Dif = Lab - Courier
        # ----------------------------------------------------------------------
        df["dif"] = np.where(df["is_valid"], df["val_lab"] - df["val_cour"], np.nan)
        df["abs_dif"] = np.abs(df["dif"])

        # ----------------------------------------------------------------------
        # Paso 3: Cálculo del error relativo porcentual
        # %Error = (|Dif| / Lab) * 100
        # ----------------------------------------------------------------------
        df["pct_error"] = np.where(
            df["is_valid"], (df["abs_dif"] / df["val_lab"]) * 100.0, np.nan
        )

        # ----------------------------------------------------------------------
        # Paso 4: Clasificación por bandas de tolerancia metalúrgica
        # - Aceptable: Error <= Tolerancia base (ej. <= 11%)
        # - Regular:   Tolerancia base < Error <= 2 * Tolerancia base
        # - Malo:      Error > 2 * Tolerancia base
        # ----------------------------------------------------------------------
        tol_pct = self.elem_cfg.tolerance * 100.0
        condiciones = [
            (~df["is_valid"]),
            (df["pct_error"] <= tol_pct),
            (df["pct_error"] <= tol_pct * 2.0),
        ]
        etiquetas = ["Sin Dato / Corte", "Aceptable", "Regular"]
        df["status"] = np.select(condiciones, etiquetas, default="Malo")

        return df

    def compute_welch_t_test(self, df_processed: pd.DataFrame) -> Optional[TTestResult]:
        """
        Calcula la prueba t de Student de Welch para diferencia de medias
        reproduciendo con exactitud la lógica de las hojas 'Sta_Cu' y 'Sta_Mo'.
        """
        # Filtra solo las filas válidas que pasaron el corte
        valid_df = df_processed[df_processed["is_valid"]].dropna(subset=["val_cour", "val_lab", "dif"])
        n = len(valid_df)

        # Se requiere un mínimo de 5 observaciones para validez estadística
        if n < 5:
            return None

        # Medias muestrales
        mean_lab = float(valid_df["val_lab"].mean())
        mean_cour = float(valid_df["val_cour"].mean())
        mean_dif = float(valid_df["dif"].mean())

        # Varianzas muestrales insesgadas (ddof=1)
        var_lab = float(valid_df["val_lab"].var(ddof=1))
        var_cour = float(valid_df["val_cour"].var(ddof=1))
        var_dif = float(valid_df["dif"].var(ddof=1))
        std_dif = math.sqrt(var_dif) if var_dif > 0 else 1e-9

        # ----------------------------------------------------------------------
        # Estadístico t calculado (Fórmula exacta celda E49 en Sta_Cu):
        # t = (Mean_Lab - Mean_Courier) / sqrt(Var_Lab/N + Var_Courier/N)
        # ----------------------------------------------------------------------
        denom = math.sqrt((var_lab / n) + (var_cour / n))
        t_stat = (mean_lab - mean_cour) / denom if denom > 0 else 0.0

        # Grados de libertad usados en la plantilla Excel (nu = n - 1)
        df_deg = n - 1

        # Valores críticos de dos colas para alfa = 0.10, 0.05, 0.01
        t_crit_90 = float(stats.t.ppf(1.0 - 0.10 / 2.0, df_deg))
        t_crit_95 = float(stats.t.ppf(1.0 - 0.05 / 2.0, df_deg))
        t_crit_99 = float(stats.t.ppf(1.0 - 0.01 / 2.0, df_deg))

        # p-valor bilateral exacto: P(|T| >= |t|)
        p_val = float(2.0 * stats.t.sf(abs(t_stat), df_deg))

        # Regla de decisión al 95% (alfa = 0.05):
        # Si |t| <= t_crit o p > 0.05 -> Aceptado (no hay sesgo significativo)
        status_95 = "Aceptado" if abs(t_stat) <= t_crit_95 else "Rechazado"

        # Intervalo de confianza al 95% del sesgo medio
        error_estandar = std_dif / math.sqrt(n)
        margen_ic = t_crit_95 * error_estandar
        ci_lower = mean_dif - margen_ic
        ci_upper = mean_dif + margen_ic

        # Asimetría y Curtosis
        skew_val = float(stats.skew(valid_df["dif"]))
        kurt_val = float(stats.kurtosis(valid_df["dif"]))

        return TTestResult(
            n_obs=n,
            mean_lab=mean_lab,
            mean_cour=mean_cour,
            mean_dif=mean_dif,
            std_dif=std_dif,
            t_stat=t_stat,
            p_value=p_val,
            t_crit_90=t_crit_90,
            t_crit_95=t_crit_95,
            t_crit_99=t_crit_99,
            status_95=status_95,
            ci_95_lower=ci_lower,
            ci_95_upper=ci_upper,
            skewness=skew_val,
            kurtosis=kurt_val,
        )

    def compute_deming_regression(
        self, df_processed: pd.DataFrame, lambda_ratio: float = 1.0
    ) -> Tuple[float, float, float]:
        """
        Regresión de Deming (Errors-in-Variables) para estimar la relación funcional real:
        Ley_Lab = alpha + beta * Ley_Courier

        lambda_ratio: Relación de varianzas de error (Var_Lab / Var_Courier).
        Por defecto 1.0 (ambos instrumentos tienen similar variabilidad relativa de error).

        Retorna: (pendiente beta, intercepto alpha, r2)
        """
        valid_df = df_processed[df_processed["is_valid"]].dropna(subset=["val_cour", "val_lab"])
        if len(valid_df) < 5:
            return 1.0, 0.0, 0.0

        x = valid_df["val_cour"].to_numpy()  # Courier
        y = valid_df["val_lab"].to_numpy()   # Laboratorio

        x_bar = np.mean(x)
        y_bar = np.mean(y)

        # Varianzas y covarianzas muestrales
        s_xx = np.var(x, ddof=1)
        s_yy = np.var(y, ddof=1)
        s_xy = np.cov(x, y, ddof=1)[0, 1]

        if s_xy == 0 or s_xx == 0:
            return 1.0, 0.0, 0.0

        # Fórmula analítica de la pendiente de Deming (beta):
        # beta = [ (s_yy - lambda * s_xx) + sqrt( (s_yy - lambda * s_xx)^2 + 4 * lambda * s_xy^2 ) ] / (2 * s_xy)
        discriminante = (s_yy - lambda_ratio * s_xx) ** 2 + 4.0 * lambda_ratio * (s_xy ** 2)
        beta_deming = ((s_yy - lambda_ratio * s_xx) + math.sqrt(discriminante)) / (2.0 * s_xy)

        # Intercepto de Deming (alpha):
        # alpha = y_bar - beta * x_bar
        alpha_deming = y_bar - beta_deming * x_bar

        # Coeficiente de determinación de Pearson (r^2)
        r_val, _ = stats.pearsonr(x, y)
        r_squared = float(r_val ** 2)

        return float(beta_deming), float(alpha_deming), float(r_squared)

    def compute_ewma_bias(self, df_processed: pd.DataFrame, alpha_ewma: float = 0.20) -> float:
        """
        Filtro de Media Móvil Exponencialmente Ponderada (EWMA).
        Rastrea la deriva temporal real del sesgo suavizando el ruido aleatorio del turno.
        alpha_ewma = 0.20 equivale a una constante de tiempo de aproximadamente 5 turnos.
        """
        valid_df = df_processed[df_processed["is_valid"]].dropna(subset=["dif"])
        if len(valid_df) == 0:
            return 0.0

        dif_series = valid_df["dif"]
        # Aplica EWMA con ponderación exponencial
        ewma_series = dif_series.ewm(alpha=alpha_ewma, adjust=False).mean()
        # Retorna el valor más reciente del sesgo filtrado
        return float(ewma_series.iloc[-1])

    def prescribe_calibration(self, df_processed: pd.DataFrame) -> CalibrationPrescription:
        """
        Gatillo de Decisión y Prescripción Matemática de Calibración:
        1. Evalúa si el sesgo es estadísticamente significativo con la prueba t.
        2. Si no es significativo (p > 0.05), PROHÍBE calibrar para evitar el efecto Deming.
        3. Si es significativo (p <= 0.05), calcula los factores Deming (K_gain, K_offset).
        """
        t_res = self.compute_welch_t_test(df_processed)
        slope, intercept, r2 = self.compute_deming_regression(df_processed)
        current_ewma = self.compute_ewma_bias(df_processed)

        # Caso sin datos suficientes
        if t_res is None or t_res.n_obs < 5:
            return CalibrationPrescription(
                should_calibrate=False,
                diagnosis="DATOS_INSUFICIENTES",
                recommendation_text="No hay suficientes turnos válidos para evaluar la calibración.",
                deming_slope=1.0,
                deming_intercept=0.0,
                r_squared=0.0,
                ewma_current_bias=0.0,
                formula_str="Sin cambio sugerido",
            )

        # Umbral de tolerancia de la corriente
        tol_rel = self.elem_cfg.tolerance

        # Condición 1: ¿El sesgo es estadísticamente indistinguible de cero?
        # Hipótesis t aceptada al 95% (p > 0.05) Y sesgo promedio dentro de un tercio de tolerancia
        if t_res.p_value > 0.05:
            return CalibrationPrescription(
                should_calibrate=False,
                diagnosis="CALIBRADO",
                recommendation_text=(
                    f"ESTADO ÓPTIMO: No se observa sesgo sistemático (p-valor={t_res.p_value:.3f} > 0.05). "
                    f"La diferencia observada ({t_res.mean_dif:+.4f}%) es atribuible a variabilidad "
                    f"aleatoria de muestreo. NO MODIFICAR las ecuaciones del Courier."
                ),
                deming_slope=slope,
                deming_intercept=intercept,
                r_squared=r2,
                ewma_current_bias=current_ewma,
                formula_str="Mantener ecuación actual (No calibrar)",
            )

        # Condición 2: Sesgo sistemático comprobado (p <= 0.05).
        # Descomposición de la deriva:
        desvio_pendiente = abs(slope - 1.0)
        # Tolerancia en pendiente: desvío mayor al 3% indica deriva de ganancia
        hay_deriva_ganancia = desvio_pendiente > 0.03

        # Tolerancia en intercepto: sesgo mayor al 3% de la ley media
        umbral_offset = 0.03 * t_res.mean_lab
        hay_deriva_offset = abs(intercept) > umbral_offset

        if hay_deriva_offset and not hay_deriva_ganancia:
            diagnostico = "DERIVA_OFFSET"
            explicacion = (
                f"DERIVA DE CERO DETECTADA (p-valor={t_res.p_value:.4f}): "
                f"La pendiente es estable (b={slope:.3f} ~ 1.0), pero existe un desplazamiento "
                f"constante de {intercept:+.4f}%. Recomendación: Ajustar únicamente el término de CERO (Offset)."
            )
            formula_sugerida = f"Ley_Nueva = Ley_Courier + ({intercept:+.4f})"

        elif hay_deriva_ganancia and not hay_deriva_offset:
            diagnostico = "DERIVA_GANANCIA"
            explicacion = (
                f"DERIVA DE SENSIBILIDAD DETECTADA (p-valor={t_res.p_value:.4f}): "
                f"El intercepto es cercano a cero ({intercept:+.4f}%), pero la pendiente "
                f"se ha desviado a {slope:.3f}. Recomendación: Multiplicar la ganancia por {slope:.4f}."
            )
            formula_sugerida = f"Ley_Nueva = {slope:.4f} * Ley_Courier"

        else:
            diagnostico = "DERIVA_COMBINADA"
            explicacion = (
                f"DERIVA INTEGRAL / CAMBIO DE MATRIZ (p-valor={t_res.p_value:.4f}): "
                f"Se detecta sesgo tanto en ganancia (b={slope:.3f}) como en offset (a={intercept:+.4f}%). "
                f"Recomendación: Aplicar la transformación lineal completa de Deming."
            )
            formula_sugerida = f"Ley_Nueva = {slope:.4f} * Ley_Courier + ({intercept:+.4f})"

        return CalibrationPrescription(
            should_calibrate=True,
            diagnosis=diagnostico,
            recommendation_text=explicacion,
            deming_slope=slope,
            deming_intercept=intercept,
            r_squared=r2,
            ewma_current_bias=current_ewma,
            formula_str=formula_sugerida,
        )
