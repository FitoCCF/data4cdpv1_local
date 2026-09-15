# -*- coding: utf-8 -*-
"""
scripts/courier_excel_clone/charts.py
=====================================
Generador de gráficas idénticas a las hojas de 'Courier_AUTO-C2.xlsm':
1. Gráf. Cu-Mo: Series temporales Courier vs Lab para Cu y Mo (Cobre y Moly).
2. Graf. Fe-Zn-Ox: Series temporales para Fe, Zn, Ox e Ins.
3. Graf1: Dispersión 1:1 con bandas de tolerancia metalúrgica.
4. Graf2: Cartas de error residual (Diferencia turno a turno).
5. Graf3: Gráficos circulares de porcentaje de conformidad (Aceptable vs Fuera de rango).
6. DistrN: Histogramas de frecuencias de error y curva normal gaussiana teórica.

No incluye ningún cálculo ajeno a lo que muestra el Excel original.
Renderizado sin interfaz gráfica (headless Agg) exportado directamente a Base64.
"""

import base64
import io
from typing import Dict, Any, List
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm


def _fig_to_base64(fig) -> str:
    """Convierte una figura Matplotlib en string base64 PNG y libera la memoria."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{img_b64}"


def render_time_series(shifts: List[str], cour: np.ndarray, lab: np.ndarray, title: str, elem: str) -> str:
    """
    Gráfica de series de tiempo (Línea Courier vs Línea Lab) equivalente a 'Gráf. Cu-Mo' y 'Graf. Fe-Zn-Ox'.
    """
    fig, ax = plt.subplots(figsize=(6.8, 3.8), dpi=100)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    x = np.arange(len(shifts))
    
    # Máscaras para ignorar NaNs
    mask_c = ~np.isnan(cour)
    mask_l = ~np.isnan(lab)

    if np.any(mask_c):
        ax.plot(x[mask_c], cour[mask_c], color="#1F4E79", marker="o", markersize=3,
                linewidth=1.4, label="COURIER", alpha=0.9)
    if np.any(mask_l):
        ax.plot(x[mask_l], lab[mask_l], color="#C00000", marker="s", markersize=3,
                linewidth=1.4, linestyle="--", label="LABORATORIO", alpha=0.9)

    ax.set_title(title, fontsize=9.5, fontweight="bold", pad=8, color="#262626")
    ax.set_xlabel("Turnos (Últimos 31 Días)", fontsize=8, labelpad=4)
    ax.set_ylabel(f"Ley ({elem})", fontsize=8, labelpad=4)

    # Etiquetas X espaciadas
    step = max(1, len(shifts) // 8)
    ax.set_xticks(x[::step])
    ax.set_xticklabels([shifts[i] for i in x[::step]], rotation=30, ha="right", fontsize=7.5)
    ax.tick_params(axis="y", labelsize=8)

    ax.grid(True, linestyle=":", color="#D9D9D9", alpha=0.8)
    ax.legend(loc="best", fontsize=8, framealpha=0.9, edgecolor="#B0B0B0")

    plt.tight_layout()
    return _fig_to_base64(fig)


def render_scatter_1to1(lab: np.ndarray, cour: np.ndarray, tol: float, title: str, elem: str) -> str:
    """
    Gráfica de dispersión 1:1 con bandas de tolerancia superior e inferior ('Graf1_Cu_Mo').
    """
    fig, ax = plt.subplots(figsize=(6.8, 3.8), dpi=100)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    mask = (~np.isnan(lab)) & (~np.isnan(cour))
    x_valid = lab[mask]
    y_valid = cour[mask]

    if len(x_valid) > 0:
        min_v = min(np.min(x_valid), np.min(y_valid)) * 0.9
        max_v = max(np.max(x_valid), np.max(y_valid)) * 1.1
        line_ref = np.linspace(min_v, max_v, 100)

        # Recta 1:1 ideal
        ax.plot(line_ref, line_ref, color="#002060", linewidth=1.3, label="1:1 (Ideal)")
        # Límites de tolerancia
        ax.plot(line_ref, line_ref * (1.0 + tol), color="#C00000", linestyle="--",
                linewidth=1.1, label=f"+{tol*100:.1f}% Tol. Sup")
        ax.plot(line_ref, line_ref * (1.0 - tol), color="#C00000", linestyle=":",
                linewidth=1.1, label=f"-{tol*100:.1f}% Tol. Inf")

        # Puntos de dispersión
        ax.scatter(x_valid, y_valid, color="#2E75B6", edgecolors="#002060", s=32,
                   alpha=0.8, label=f"Turnos (N={len(x_valid)})", zorder=4)

        ax.set_xlim(min_v, max_v)
        ax.set_ylim(min_v, max_v)

    ax.set_title(f"GRAFICA DE AJUSTE: {title}", fontsize=9, fontweight="bold", pad=8, color="#262626")
    ax.set_xlabel(f"Laboratorio ({elem})", fontsize=8, labelpad=4)
    ax.set_ylabel(f"Courier ({elem})", fontsize=8, labelpad=4)
    ax.tick_params(labelsize=8)
    ax.grid(True, linestyle=":", color="#D9D9D9", alpha=0.8)
    ax.legend(loc="upper left", fontsize=7.5, framealpha=0.9, edgecolor="#B0B0B0")

    plt.tight_layout()
    return _fig_to_base64(fig)


def render_residual_chart(shifts: List[str], dif: np.ndarray, title: str, elem: str) -> str:
    """
    Carta de error residual turno a turno ('Graf2_Cu_Mo').
    Diferencia = Lab - Courier
    """
    fig, ax = plt.subplots(figsize=(6.8, 3.8), dpi=100)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    x = np.arange(len(shifts))
    mask = ~np.isnan(dif)

    if np.any(mask):
        colors = ["#C00000" if v < 0 else "#1F4E79" for v in dif[mask]]
        ax.bar(x[mask], dif[mask], color=colors, width=0.7, alpha=0.85, edgecolor="#595959", linewidth=0.5)
        ax.axhline(0, color="#000000", linewidth=1.0, linestyle="-")

    ax.set_title(f"GRAFICA ERROR RESIDUAL: {title}", fontsize=9, fontweight="bold", pad=8, color="#262626")
    ax.set_xlabel("Turnos (Últimos 31 Días)", fontsize=8, labelpad=4)
    ax.set_ylabel(f"Diferencia Lab - Cour ({elem})", fontsize=8, labelpad=4)

    step = max(1, len(shifts) // 8)
    ax.set_xticks(x[::step])
    ax.set_xticklabels([shifts[i] for i in x[::step]], rotation=30, ha="right", fontsize=7.5)
    ax.tick_params(axis="y", labelsize=8)
    ax.grid(True, linestyle=":", color="#D9D9D9", alpha=0.8)

    plt.tight_layout()
    return _fig_to_base64(fig)


def render_conformity_pie(n_acep: int, n_fuera: int, title: str, tol: float) -> str:
    """
    Gráfico circular de porcentaje de conformidad ('Graf3_Cu_Mo').
    Aceptable (Verde) vs Fuera de rango (Rojo).
    """
    fig, ax = plt.subplots(figsize=(5.5, 3.8), dpi=100)
    fig.patch.set_facecolor("#FFFFFF")

    total = n_acep + n_fuera
    if total > 0:
        sizes = [n_acep, n_fuera]
        labels = [f"Aceptable (<= {tol*100:.0f}%)\n{n_acep} ({n_acep/total*100:.1f}%)",
                  f"Fuera de rango\n{n_fuera} ({n_fuera/total*100:.1f}%)"]
        colors = ["#548235", "#C00000"]
        explode = (0.05, 0)

        ax.pie(sizes, explode=explode, labels=labels, colors=colors, autopct="",
               startangle=140, textprops={"fontsize": 8, "fontweight": "bold"},
               wedgeprops={"edgecolor": "#FFFFFF", "linewidth": 1.5})
    else:
        ax.text(0.5, 0.5, "Sin datos válidos", ha="center", va="center", fontsize=9)

    ax.set_title(f"DIFERENCIA: {title}", fontsize=9, fontweight="bold", pad=8, color="#262626")
    plt.tight_layout()
    return _fig_to_base64(fig)


def render_normal_distribution(dif: np.ndarray, title: str, elem: str) -> str:
    """
    Histograma de frecuencia con curva gaussiana teórica superpuesta ('DistrN_Cu').
    """
    fig, ax = plt.subplots(figsize=(6.8, 3.8), dpi=100)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    valid_dif = dif[~np.isnan(dif)]
    if len(valid_dif) > 2:
        mu = np.mean(valid_dif)
        sigma = np.std(valid_dif, ddof=1)

        # Histograma
        n, bins, patches = ax.hist(valid_dif, bins=15, density=True, color="#2E75B6",
                                   edgecolor="#1F4E79", alpha=0.7, label="Frecuencia Empírica")

        # Curva normal teórica
        if sigma > 1e-6:
            x_norm = np.linspace(min(valid_dif) * 1.2, max(valid_dif) * 1.2, 100)
            y_norm = norm.pdf(x_norm, mu, sigma)
            ax.plot(x_norm, y_norm, color="#C00000", linewidth=1.6, label=f"Gauss Teórica (μ={mu:.3f}, σ={sigma:.3f})")

        ax.axvline(0, color="#000000", linestyle="--", linewidth=1.0, label="Cero (Sin sesgo)")

    ax.set_title(f"DISTRIBUCION NORMAL: {title}", fontsize=9, fontweight="bold", pad=8, color="#262626")
    ax.set_xlabel(f"Error Residual Lab - Cour ({elem})", fontsize=8, labelpad=4)
    ax.set_ylabel("Densidad de Probabilidad", fontsize=8, labelpad=4)
    ax.tick_params(labelsize=8)
    ax.grid(True, linestyle=":", color="#D9D9D9", alpha=0.8)
    ax.legend(loc="best", fontsize=7.5, framealpha=0.9, edgecolor="#B0B0B0")

    plt.tight_layout()
    return _fig_to_base64(fig)
