# -*- coding: utf-8 -*-
"""
scripts/courier_demo/dashboard.py
=================================
Generador y servidor del Dashboard Interactivo de Aseguramiento Metrológico:
- Genera un archivo HTML5 autocontenido (con CSS responsivo y moderno).
- Muestra el Semáforo de Estado y las Prescripciones Matemáticas de Calibración.
- Permite servir el dashboard mediante el servidor HTTP estándar de Python.
- Totalmente compatible con Slackware Linux y WSL2 Debian.

Código explícito y documentado en su totalidad.
"""

import base64
import http.server
import os
import socketserver
from typing import Dict, List
import pandas as pd

from scripts.courier_demo.config import STREAMS_COBRE, STREAMS_MOLY, StreamConfig
from scripts.courier_demo.engine import (
    CourierComparisonEngine,
    TTestResult,
    CalibrationPrescription,
)
from scripts.courier_demo.provider import CourierDataProvider, get_provider
from scripts.courier_demo.report import CourierChartGenerator


class CourierDashboardBuilder:
    """
    Construye la página HTML del Dashboard compilando todos los resultados analíticos,
    estadísticas de t-Student, prescripciones de Deming y gráficos embebidos.
    """

    def __init__(self, provider: CourierDataProvider, output_dir: str = "scripts/courier_demo/output"):
        self.provider = provider
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.chart_gen = CourierChartGenerator(output_dir=self.output_dir)

    def _img_to_base64(self, img_path: str) -> str:
        """Convierte una imagen PNG en una cadena base64 para embeberla directamente en el HTML."""
        if not os.path.exists(img_path):
            return ""
        with open(img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    def build_dashboard(self) -> str:
        """
        Ejecuta el análisis sobre todas las corrientes (Cobre y Moly)
        y compila el archivo HTML final 'dashboard.html'.
        """
        print("[CourierDashboardBuilder] Procesando corrientes de Planta de Cobre...")
        cobre_cards = self._process_plant_streams(STREAMS_COBRE, "Cobre")

        print("[CourierDashboardBuilder] Procesando corrientes de Planta de Molibdeno...")
        moly_cards = self._process_plant_streams(STREAMS_MOLY, "Moly")

        html_content = self._render_html(cobre_cards, moly_cards)

        output_path = os.path.join(self.output_dir, "dashboard.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"[CourierDashboardBuilder] Dashboard generado exitosamente en: {output_path}")
        return output_path

    def _process_plant_streams(self, streams_dict: Dict[str, StreamConfig], plant_name: str) -> List[Dict]:
        """Procesa cada corriente y elemento de una planta y retorna sus tarjetas de datos."""
        cards = []
        for s_id, s_cfg in streams_dict.items():
            for elem_name, e_cfg in s_cfg.elements.items():
                engine = CourierComparisonEngine(s_cfg, e_cfg)
                df_raw = self.provider.get_stream_data(s_cfg, elem_name)
                df_proc = engine.process_dataframe(df_raw)

                t_res = engine.compute_welch_t_test(df_proc)
                presc = engine.prescribe_calibration(df_proc)

                # Genera el panel de 4 gráficos en PNG
                img_path = self.chart_gen.generate_stream_element_plots(
                    s_cfg, e_cfg, df_proc, t_res, presc
                )
                img_b64 = self._img_to_base64(img_path)

                # Calcula porcentajes de conformidad
                valid_df = df_proc[df_proc["is_valid"]]
                total_valid = len(valid_df)
                if total_valid > 0:
                    pct_acept = (valid_df["status"] == "Aceptable").sum() / total_valid * 100.0
                    pct_regul = (valid_df["status"] == "Regular").sum() / total_valid * 100.0
                    pct_malo = (valid_df["status"] == "Malo").sum() / total_valid * 100.0
                else:
                    pct_acept, pct_regul, pct_malo = 0.0, 0.0, 0.0

                cards.append({
                    "stream_name": s_cfg.name,
                    "element": elem_name,
                    "plant": plant_name,
                    "cutoff_min": e_cfg.cutoff_min,
                    "tolerance": e_cfg.tolerance * 100.0,
                    "t_res": t_res,
                    "presc": presc,
                    "pct_acept": pct_acept,
                    "pct_regul": pct_regul,
                    "pct_malo": pct_malo,
                    "total_valid": total_valid,
                    "img_b64": img_b64,
                })
        return cards

    def _render_html(self, cobre_cards: List[Dict], moly_cards: List[Dict]) -> str:
        """Genera el código HTML5 con CSS moderno autocontenido."""

        def render_card(c: Dict) -> str:
            t = c["t_res"]
            p = c["presc"]

            # Define color de insignia según diagnóstico
            if p.diagnosis == "CALIBRADO":
                badge_class = "badge-success"
                badge_text = "CALIBRADO (EN ESPECIFICACIÓN)"
                box_class = "box-success"
            elif "OFFSET" in p.diagnosis or "GANANCIA" in p.diagnosis:
                badge_class = "badge-warning"
                badge_text = f"ADVERTENCIA: {p.diagnosis}"
                box_class = "box-warning"
            else:
                badge_class = "badge-danger"
                badge_text = f"ACCION CRITICA: {p.diagnosis}"
                box_class = "box-danger"

            # Formatea métricas t-Student
            if t:
                n_str = str(t.n_obs)
                mean_lab_str = f"{t.mean_lab:.4f}%"
                mean_cour_str = f"{t.mean_cour:.4f}%"
                dif_str = f"{t.mean_dif:+.4f}%"
                t_stat_str = f"{t.t_stat:.3f}"
                pval_str = f"{t.p_value:.4f}"
                ci_str = f"[{t.ci_95_lower:+.4f}%, {t.ci_95_upper:+.4f}%]"
                decision_str = t.status_95
                skew_str = f"{t.skewness:.2f}"
                kurt_str = f"{t.kurtosis:.2f}"
            else:
                n_str = mean_lab_str = mean_cour_str = dif_str = t_stat_str = pval_str = ci_str = decision_str = skew_str = kurt_str = "N/A"

            return f"""
            <div class="card">
                <div class="card-header">
                    <div>
                        <span class="stream-title">{c['stream_name']} - {c['element']}</span>
                        <span class="plant-tag">{c['plant']}</span>
                    </div>
                    <span class="badge {badge_class}">{badge_text}</span>
                </div>

                <div class="card-body">
                    <!-- Caja de Prescripción Matemática de Calibración -->
                    <div class="prescription-box {box_class}">
                        <h4>Recomendación Metrológica:</h4>
                        <p class="prescription-text">{p.recommendation_text}</p>
                        <div class="formula-banner">
                            <span class="formula-label">Ecuación Sugerida:</span>
                            <code>{p.formula_str}</code>
                        </div>
                        <div class="deming-details">
                            <span>Pendiente Deming (&beta;): <strong>{p.deming_slope:.4f}</strong></span>
                            <span>Intercepto Deming (&alpha;): <strong>{p.deming_intercept:+.4f}</strong></span>
                            <span>R&sup2;: <strong>{p.r_squared:.3f}</strong></span>
                            <span>Sesgo EWMA actual: <strong>{p.ewma_current_bias:+.4f}%</strong></span>
                        </div>
                    </div>

                    <!-- Tabla de Validación t de Student -->
                    <div class="stats-grid">
                        <div class="stat-item">
                            <span class="stat-lbl">Turnos Evaluados</span>
                            <span class="stat-val">{n_str}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-lbl">Media Lab</span>
                            <span class="stat-val">{mean_lab_str}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-lbl">Media Courier</span>
                            <span class="stat-val">{mean_cour_str}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-lbl">Sesgo Medio (&Delta;)</span>
                            <span class="stat-val { 'text-danger' if t and abs(t.mean_dif) > 0.05 else 'text-success'}">{dif_str}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-lbl">Estadístico t</span>
                            <span class="stat-val">{t_stat_str}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-lbl">p-valor (2 colas)</span>
                            <span class="stat-val { 'text-danger' if t and t.p_value <= 0.05 else 'text-success'}">{pval_str}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-lbl">Decisión t (95%)</span>
                            <span class="stat-val">{decision_str}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-lbl">IC 95% Sesgo</span>
                            <span class="stat-val">{ci_str}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-lbl">Conformidad Base</span>
                            <span class="stat-val text-success">{c['pct_acept']:.1f}%</span>
                        </div>
                    </div>

                    <!-- Gráficos de 4 cuadrantes embebidos -->
                    <div class="chart-container">
                        <img src="{c['img_b64']}" alt="Gráficas Metrológicas {c['stream_name']} - {c['element']}" loading="lazy"/>
                    </div>
                </div>
            </div>
            """

        cobre_html = "\n".join([render_card(c) for c in cobre_cards])
        moly_html = "\n".join([render_card(c) for c in moly_cards])

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Metrológico: Courier C2 vs Laboratorio Químico</title>
    <style>
        :root {{
            --bg-color: #0d1117;
            --surface-color: #161b22;
            --surface-border: #30363d;
            --text-main: #c9d1d9;
            --text-bright: #f0f6fc;
            --text-muted: #8b949e;
            --accent-blue: #58a6ff;
            --accent-green: #238636;
            --accent-yellow: #d29922;
            --accent-red: #da3633;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: var(--font-family);
            margin: 0;
            padding: 20px;
        }}
        header {{
            border-bottom: 1px solid var(--surface-border);
            padding-bottom: 15px;
            margin-bottom: 25px;
        }}
        h1 {{
            color: var(--text-bright);
            font-size: 24px;
            margin: 0 0 8px 0;
        }}
        .subtitle {{
            color: var(--text-muted);
            font-size: 14px;
        }}
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }}
        .tab-btn {{
            background-color: var(--surface-color);
            border: 1px solid var(--surface-border);
            color: var(--text-main);
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        .tab-btn.active {{
            background-color: #1f6feb;
            color: white;
            border-color: #388bfd;
        }}
        .card {{
            background-color: var(--surface-color);
            border: 1px solid var(--surface-border);
            border-radius: 8px;
            margin-bottom: 30px;
            overflow: hidden;
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            background-color: rgba(255, 255, 255, 0.02);
            border-bottom: 1px solid var(--surface-border);
        }}
        .stream-title {{
            font-size: 18px;
            font-weight: 700;
            color: var(--text-bright);
            margin-right: 12px;
        }}
        .plant-tag {{
            background-color: #21262d;
            color: var(--accent-blue);
            font-size: 12px;
            padding: 3px 8px;
            border-radius: 12px;
            border: 1px solid #30363d;
        }}
        .card-body {{
            padding: 20px;
        }}
        .badge {{
            padding: 5px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}
        .badge-success {{ background-color: rgba(35, 134, 54, 0.2); color: #3fb950; border: 1px solid #238636; }}
        .badge-warning {{ background-color: rgba(210, 153, 34, 0.2); color: #e3b341; border: 1px solid #d29922; }}
        .badge-danger  {{ background-color: rgba(218, 54, 51, 0.2); color: #f85149; border: 1px solid #da3633; }}

        .prescription-box {{
            padding: 16px;
            border-radius: 6px;
            margin-bottom: 20px;
        }}
        .box-success {{ background-color: rgba(35, 134, 54, 0.1); border-left: 4px solid #238636; }}
        .box-warning {{ background-color: rgba(210, 153, 34, 0.1); border-left: 4px solid #d29922; }}
        .box-danger  {{ background-color: rgba(218, 54, 51, 0.1); border-left: 4px solid #da3633; }}

        .prescription-box h4 {{
            margin: 0 0 8px 0;
            font-size: 14px;
            color: var(--text-bright);
        }}
        .prescription-text {{
            font-size: 13px;
            line-height: 1.5;
            margin: 0 0 12px 0;
        }}
        .formula-banner {{
            background-color: #0d1117;
            padding: 10px 14px;
            border-radius: 6px;
            border: 1px solid var(--surface-border);
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .formula-label {{ font-size: 12px; color: var(--text-muted); font-weight: 600; }}
        .formula-banner code {{
            font-family: monospace;
            font-size: 14px;
            color: var(--accent-blue);
            font-weight: 700;
        }}
        .deming-details {{
            display: flex;
            gap: 20px;
            font-size: 12px;
            color: var(--text-muted);
        }}
        .deming-details strong {{ color: var(--text-main); }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }}
        .stat-item {{
            background-color: #0d1117;
            border: 1px solid var(--surface-border);
            border-radius: 6px;
            padding: 10px;
            display: flex;
            flex-direction: column;
        }}
        .stat-lbl {{ font-size: 11px; color: var(--text-muted); margin-bottom: 4px; }}
        .stat-val {{ font-size: 14px; font-weight: 700; color: var(--text-bright); }}
        .text-success {{ color: #3fb950; }}
        .text-danger {{ color: #f85149; }}

        .chart-container {{
            border: 1px solid var(--surface-border);
            border-radius: 6px;
            overflow: hidden;
            background-color: #ffffff;
        }}
        .chart-container img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
    </style>
</head>
<body>
    <header>
        <h1>Aseguramiento Metrológico y Calibración Courier C2</h1>
        <div class="subtitle">Concentradora Toquepala (Southern Peru) &mdash; Reemplazo de Courier_AUTO-C2.xlsm con Validación t-Student y Regresión de Deming</div>
    </header>

    <div class="tabs">
        <button class="tab-btn active" onclick="showTab('cobre')">Planta Cobre C2</button>
        <button class="tab-btn" onclick="showTab('moly')">Planta Molibdeno C2</button>
    </div>

    <div id="tab-cobre" class="tab-content active">
        {cobre_html}
    </div>

    <div id="tab-moly" class="tab-content">
        {moly_html}
    </div>

    <script>
        function showTab(plant) {{
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

            if (plant === 'cobre') {{
                document.querySelectorAll('.tab-btn')[0].classList.add('active');
                document.getElementById('tab-cobre').classList.add('active');
            }} else {{
                document.querySelectorAll('.tab-btn')[1].classList.add('active');
                document.getElementById('tab-moly').classList.add('active');
            }}
        }}
    </script>
</body>
</html>
"""


def serve_dashboard(html_dir: str = "scripts/courier_demo/output", port: int = 8050):
    """
    Inicia un servidor HTTP ligero estándar de Python en el puerto indicado.
    Permite abrir el dashboard desde cualquier navegador web en http://localhost:8050/dashboard.html.
    """
    os.chdir(html_dir)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"\n[HTTP Server] Servidor activo en: http://localhost:{port}/dashboard.html")
        print("[HTTP Server] Presione Ctrl+C para detener el servidor.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[HTTP Server] Servidor detenido.")
