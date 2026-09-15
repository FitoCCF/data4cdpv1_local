# -*- coding: utf-8 -*-
"""
scripts/courier_demo/report.py
==============================
Generador de figuras gráficas con Matplotlib y Seaborn en modo headless (Agg),
compatible con cualquier terminal Linux (Slackware / Debian / WSL2).

Genera los 4 tipos de gráficos equivalentes a las hojas del Excel:
1. Dispersión 1:1 con bandas de tolerancia metalúrgica (Graf1_Cu_Mo).
2. Evolución temporal de 31 días Courier vs Lab (Gráf. Cu-Mo).
3. Cartas de control residual de diferencias (Graf2_Cu_Mo).
4. Histograma de distribución de errores y curva normal teórica (DistrN_Cu).

Código explícito y completamente documentado.
"""

import os
from typing import Optional
import matplotlib
# Configura el backend a 'Agg' para renderizado sin interfaz gráfica (headless)
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from scripts.courier_demo.config import ElementConfig, StreamConfig
from scripts.courier_demo.engine import CourierComparisonEngine, TTestResult, CalibrationPrescription


class CourierChartGenerator:
    """
    Genera gráficos analíticos de alta resolución y los guarda como imágenes PNG
    o los codifica para incrustación directa en el dashboard HTML.
    """

    def __init__(self, output_dir: str = "scripts/courier_demo/output"):
        self.output_dir = output_dir
        # Crea la carpeta de salida si no existe
        os.makedirs(self.output_dir, exist_ok=True)

        # Configura estilo visual limpio y profesional
        plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    def generate_stream_element_plots(
        self,
        stream_cfg: StreamConfig,
        elem_cfg: ElementConfig,
        df_processed: pd.DataFrame,
        t_res: Optional[TTestResult],
        presc: CalibrationPrescription,
    ) -> str:
        """
        Crea un panel de 4 cuadrantes (2x2) para un elemento en una corriente:
        - [0,0] Dispersión 1:1 con bandas de tolerancia y recta de Deming.
        - [0,1] Serie de tiempo Courier vs Laboratorio (62 turnos).
        - [1,0] Carta de control de error residual (Diferencia vs Turnos).
        - [1,1] Histograma de frecuencias y curva gaussiana ajustada.

        Retorna la ruta absoluta del archivo PNG generado.
        """
        # Filtra datos válidos
        valid = df_processed[df_processed["is_valid"]].copy()
        if len(valid) < 5:
            return ""

        # Crea la figura con tamaño adecuado
        fig, axes = plt.subplots(2, 2, figsize=(14, 10), dpi=120)
        fig.suptitle(
            f"{stream_cfg.name} - {elem_cfg.element} ({stream_cfg.plant})\n"
            f"Diagnóstico Metrológico: {presc.diagnosis} | Decisión t-Student: {t_res.status_95 if t_res else 'N/A'}",
            fontsize=13,
            fontweight="bold",
        )

        x_cour = valid["val_cour"].to_numpy()
        y_lab = valid["val_lab"].to_numpy()
        min_val = min(np.min(x_cour), np.min(y_lab)) * 0.90
        max_val = max(np.max(x_cour), np.max(y_lab)) * 1.10

        # ======================================================================
        # CUADRANTE 1: Dispersión 1:1 con Bandas de Tolerancia y Regresión Deming
        # ======================================================================
        ax1 = axes[0, 0]
        # Puntos de datos por turno
        ax1.scatter(
            valid[valid["shift"] == "A"]["val_cour"],
            valid[valid["shift"] == "A"]["val_lab"],
            color="#1f77b4",
            label="Turno A (Día)",
            alpha=0.75,
            edgecolors="k",
            s=40,
        )
        ax1.scatter(
            valid[valid["shift"] == "B"]["val_cour"],
            valid[valid["shift"] == "B"]["val_lab"],
            color="#ff7f0e",
            label="Turno B (Noche)",
            alpha=0.75,
            edgecolors="k",
            s=40,
        )

        # Recta ideal 1:1 (Y = X)
        grid_x = np.linspace(min_val, max_val, 100)
        ax1.plot(grid_x, grid_x, "k--", label="Ideal 1:1 (Y = X)", linewidth=1.5)

        # Bandas de tolerancia metalúrgica base (+/- T_base)
        tol = elem_cfg.tolerance
        ax1.plot(grid_x, grid_x * (1.0 + tol), "g:", label=f"Tolerancia (+{tol*100:.0f}%)", linewidth=1.2)
        ax1.plot(grid_x, grid_x * (1.0 - tol), "g:", label=f"Tolerancia (-{tol*100:.0f}%)", linewidth=1.2)

        # Recta ajustada de Deming
        deming_y = presc.deming_intercept + presc.deming_slope * grid_x
        ax1.plot(grid_x, deming_y, "r-", label=f"Deming (b={presc.deming_slope:.2f}, a={presc.deming_intercept:+.3f})", linewidth=1.8)

        ax1.set_xlim(min_val, max_val)
        ax1.set_ylim(min_val, max_val)
        ax1.set_xlabel(f"Courier ({elem_cfg.element})")
        ax1.set_ylabel(f"Laboratorio ({elem_cfg.element})")
        ax1.set_title("Ajuste 1:1 Courier vs Lab")
        ax1.legend(loc="upper left", fontsize=8)

        # ======================================================================
        # CUADRANTE 2: Serie Temporal de 31 Días (62 Turnos)
        # ======================================================================
        ax2 = axes[0, 1]
        turnos_idx = np.arange(len(valid))
        ax2.plot(turnos_idx, valid["val_lab"], "o-", color="#2ca02c", label="Laboratorio", linewidth=1.5, markersize=4)
        ax2.plot(turnos_idx, valid["val_cour"], "s--", color="#d62728", label="Courier", linewidth=1.5, markersize=4)
        ax2.set_xlabel("Índice de Turno Consecutivo (31 Días)")
        ax2.set_ylabel(f"Ley ({elem_cfg.element})")
        ax2.set_title("Evolución Temporal de Leyes")
        ax2.legend(loc="upper right", fontsize=8)

        # ======================================================================
        # CUADRANTE 3: Carta de Error Residual y Banda EWMA
        # ======================================================================
        ax3 = axes[1, 0]
        # Barra de diferencias
        colores_barras = np.where(valid["status"] == "Aceptable", "#2ca02c", np.where(valid["status"] == "Regular", "#ffbb78", "#d62728"))
        ax3.bar(turnos_idx, valid["dif"], color=colores_barras, alpha=0.7, width=0.8, label="Diferencia (Lab - Cour)")
        ax3.axhline(0, color="black", linestyle="-", linewidth=1)

        # Línea de sesgo medio y límites de tolerancia absoluta
        mean_dif = t_res.mean_dif if t_res else 0.0
        ax3.axhline(mean_dif, color="blue", linestyle="--", label=f"Sesgo Medio ({mean_dif:+.4f})", linewidth=1.2)

        # Trazo del filtro EWMA
        ewma_vals = valid["dif"].ewm(alpha=0.20, adjust=False).mean()
        ax3.plot(turnos_idx, ewma_vals, color="#9467bd", linewidth=2.0, label="Deriva EWMA (Filtro)")

        ax3.set_xlabel("Índice de Turno")
        ax3.set_ylabel(f"Diferencia Lab - Courier ({elem_cfg.element})")
        ax3.set_title("Carta Residual y Detección de Deriva")
        ax3.legend(loc="upper right", fontsize=8)

        # ======================================================================
        # CUADRANTE 4: Histograma de Residuos y Curva Normal de Gauss
        # ======================================================================
        ax4 = axes[1, 1]
        difs = valid["dif"].to_numpy()
        # Histograma empírico
        n_bins = 15
        counts, bins, patches = ax4.hist(difs, bins=n_bins, density=True, alpha=0.6, color="#17becf", edgecolor="black")

        # Curva gaussiana teórica ajustada
        mu = float(np.mean(difs))
        sigma = float(np.std(difs, ddof=1)) if len(difs) > 1 else 1.0
        x_gauss = np.linspace(np.min(difs) - 0.5 * sigma, np.max(difs) + 0.5 * sigma, 100)
        y_gauss = stats.norm.pdf(x_gauss, mu, sigma)
        ax4.plot(x_gauss, y_gauss, "r-", linewidth=2, label=f"Gauss (μ={mu:+.3f}, σ={sigma:.3f})")

        ax4.set_xlabel("Error Residual (Lab - Courier)")
        ax4.set_ylabel("Densidad de Probabilidad")
        ax4.set_title(f"Distribución del Error (Asimetría={t_res.skewness:.2f}, Curtosis={t_res.kurtosis:.2f})")
        ax4.legend(loc="upper right", fontsize=8)

        # Ajuste de diseño y guardado
        plt.tight_layout()
        filename = f"{stream_cfg.plant.lower()}_{stream_cfg.stream_id}_{elem_cfg.element.replace('%', 'pct')}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=120)
        plt.close(fig)

        return filepath
