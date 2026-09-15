# -*- coding: utf-8 -*-
"""
scripts/courier_demo/run_demo.py
================================
Punto de entrada principal para el Demo de Reemplazo y Recalibración del Courier C2.

Uso básico en laptop con Slackware (Modo DEV - Offline):
    pixi run python scripts/courier_demo/run_demo.py

Uso con servidor web local:
    pixi run python scripts/courier_demo/run_demo.py --serve --port 8050

Uso futuro en WSL2 Debian Linux (Modo PROD - Conectado a PI Gateway):
    pixi run python scripts/courier_demo/run_demo.py --mode prod

Código explícito y completamente comentado.
"""

import argparse
import os
import sys

# Asegura que el directorio raíz del proyecto esté en el PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scripts.courier_demo.config import STREAMS_COBRE, STREAMS_MOLY
from scripts.courier_demo.dashboard import CourierDashboardBuilder, serve_dashboard
from scripts.courier_demo.engine import CourierComparisonEngine
from scripts.courier_demo.provider import get_provider


def main():
    parser = argparse.ArgumentParser(
        description="Demo de Validación Metrológica y Recalibración Matemática Courier C2"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="dev",
        choices=["dev", "prod"],
        help="Modo de ejecución: 'dev' (offline con snapshot Excel) o 'prod' (online con PI Gateway)",
    )
    parser.add_argument(
        "--excel",
        type=str,
        default="data/raw/Courier_AUTO-C2.xlsm",
        help="Ruta al archivo Excel con datos históricos para modo dev",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Inicia un servidor HTTP local para ver el dashboard en el navegador",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8050,
        help="Puerto para el servidor HTTP local (por defecto 8050)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("DEMO: ASEGURAMIENTO METROLÓGICO Y RECALIBRACIÓN COURIER C2")
    print(f"Modo: {args.mode.upper()} | Entorno: {'Slackware (Offline)' if args.mode == 'dev' else 'WSL2 Debian (Online)'}")
    print("=" * 80)

    # 1. Instancia el proveedor de datos adecuado (OOP)
    provider = get_provider(mode=args.mode, excel_path=args.excel)

    # 2. Imprime resumen analítico en consola para Planta Cobre
    print("\n>>> ANÁLISIS DE PLANTA DE COBRE C2:")
    _print_plant_summary(provider, STREAMS_COBRE)

    # 3. Imprime resumen analítico en consola para Planta Moly
    print("\n>>> ANÁLISIS DE PLANTA DE MOLIBDENO C2:")
    _print_plant_summary(provider, STREAMS_MOLY)

    # 4. Construye el Dashboard interactivo HTML y genera los gráficos
    output_dir = os.path.join(project_root, "scripts/courier_demo/output")
    builder = CourierDashboardBuilder(provider=provider, output_dir=output_dir)
    dashboard_path = builder.build_dashboard()

    print("\n" + "=" * 80)
    print("EJECUCIÓN COMPLETADA EXITOSAMENTE")
    print(f"Archivo del Dashboard: {dashboard_path}")
    print("Puede abrir este archivo en cualquier navegador:")
    print(f"    xdg-open file://{os.path.abspath(dashboard_path)}")
    print("=" * 80)

    # 5. Si se solicitó --serve, levanta el servidor web local
    if args.serve:
        serve_dashboard(html_dir=output_dir, port=args.port)


def _print_plant_summary(provider, streams_dict):
    """Genera e imprime una tabla formateada en consola con los resultados."""
    header = (
        f"{'Corriente':<30} {'Elem':<5} {'N':>3} {'Lab':>8} {'Cour':>8} "
        f"{'Sesgo':>8} {'p-val':>7} {'t-Student':<10} {'Prescripción de Calibración'}"
    )
    print("-" * len(header))
    print(header)
    print("-" * len(header))

    for s_id, s_cfg in streams_dict.items():
        for elem_name, e_cfg in s_cfg.elements.items():
            engine = CourierComparisonEngine(s_cfg, e_cfg)
            df_raw = provider.get_stream_data(s_cfg, elem_name)
            df_proc = engine.process_dataframe(df_raw)

            t_res = engine.compute_welch_t_test(df_proc)
            presc = engine.prescribe_calibration(df_proc)

            if t_res:
                n_str = str(t_res.n_obs)
                lab_str = f"{t_res.mean_lab:.3f}"
                cour_str = f"{t_res.mean_cour:.3f}"
                dif_str = f"{t_res.mean_dif:+.4f}"
                pval_str = f"{t_res.p_value:.4f}"
                t_decision = t_res.status_95
            else:
                n_str = lab_str = cour_str = dif_str = pval_str = t_decision = "N/A"

            # Formatea recomendación resumida
            if presc.diagnosis == "CALIBRADO":
                rec_str = "OK (No calibrar)"
            else:
                rec_str = f"{presc.diagnosis}: {presc.formula_str}"

            print(
                f"{s_cfg.name:<30} {elem_name:<5} {n_str:>3} {lab_str:>8} {cour_str:>8} "
                f"{dif_str:>8} {pval_str:>7} {t_decision:<10} {rec_str}"
            )
    print("-" * len(header))


if __name__ == "__main__":
    main()
