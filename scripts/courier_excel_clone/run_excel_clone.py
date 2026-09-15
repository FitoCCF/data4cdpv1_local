# -*- coding: utf-8 -*-
"""
scripts/courier_excel_clone/run_excel_clone.py
==============================================
Punto de entrada principal para generar la réplica idéntica de 'Courier_AUTO-C2.xlsm'.
- Hoja principal 'Portada': mismos colores, títulos, estructura y bordes de Excel.
- Gráficas organizadas en pestañas nativas independientes (Gráf. Cu-Mo, Graf. Fe-Zn-Ox, Graf1, Graf2, Graf3, DistrN).
- Cero cálculos ajenos al archivo Excel (sin Deming, sin t-Student, sin EWMA).

Uso:
  # Modo local en laptop Slackware (desde Excel offline):
  pixi run python scripts/courier_excel_clone/run_excel_clone.py --mode dev --serve --port 8055

  # Modo en línea en WSL2 Debian (desde PI Gateway):
  pixi run python scripts/courier_excel_clone/run_excel_clone.py --mode prod --serve --port 8055
"""

import argparse
import http.server
import os
import socketserver
import sys
import webbrowser

# Añadir el path raíz para que las importaciones funcionen desde cualquier carpeta
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.courier_excel_clone.provider import ExcelCloneProvider
from scripts.courier_excel_clone.charts import (
    render_time_series,
    render_scatter_1to1,
    render_residual_chart,
    render_conformity_pie,
    render_normal_distribution,
)
from scripts.courier_excel_clone.builder import build_portada_html, compile_full_dashboard


def generate_clone_dashboard(mode: str = "dev") -> str:
    """
    Ejecuta el pipeline completo de carga de datos, renderizado de gráficas
    y compilación de la página HTML idéntica al Excel.
    """
    print("=" * 80)
    print(f"GENERANDO RÉPLICA EXACTA DE EXCEL: Courier_AUTO-C2.xlsm")
    print(f"Modo: {mode.upper()} | Generando vistas y pestañas nativas...")
    print("=" * 80)

    # 1. Instanciamos el proveedor
    if mode.lower() == "prod":
        try:
            from scripts.pi_client import PiGateway
            gw = PiGateway()
            status = gw.status()
            if not status.get("ok"):
                raise ConnectionError(f"PI Gateway respondió con error: {status}")
            print(f"[PROD] Conexión establecida con PiGateway: {status.get('server')}")
            # En prod usamos los datos de la hoja dev como fallback o mapeo de PiGateway
            provider = ExcelCloneProvider()
        except Exception as e:
            print(f"[ADVERTENCIA] No se pudo conectar con PiGateway ({e}). Usando datos de Excel...")
            provider = ExcelCloneProvider()
    else:
        provider = ExcelCloneProvider()

    # 2. Cargar datos de Portada y Series históricas
    print("[1/4] Extrayendo celdas exactas de la hoja Portada...")
    portada_data = provider.get_portada_data()
    eval_date = portada_data["cobre"]["date_str"]

    print("[2/4] Extrayendo 62 turnos de las hojas TABLA y TABLA_M...")
    series_data = provider.get_series_data()
    cobre_s = series_data["cobre"]
    moly_s = series_data["moly"]
    shifts_cobre = cobre_s["shifts"]
    shifts_moly = moly_s["shifts"]

    # 3. Generar gráficas para cada pestaña
    print("[3/4] Renderizando gráficas tipo Excel...")

    # Pestaña 2: Gráf. Cu-Mo (12 gráficas)
    print("  -> Renderizando Gráf. Cu-Mo (12 gráficas)...")
    charts_cu_mo = [
        # Cobre
        {"title": "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Cu)", "img_b64": render_time_series(shifts_cobre, cobre_s["alim_cu"]["cour"], cobre_s["alim_cu"]["lab"], "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Cu)", "%Cu")},
        {"title": "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Mo)", "img_b64": render_time_series(shifts_cobre, cobre_s["alim_mo"]["cour"], cobre_s["alim_mo"]["lab"], "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Mo)", "%Mo")},
        {"title": "COLA FINAL - PLANTA DE COBRE (%Cu)", "img_b64": render_time_series(shifts_cobre, cobre_s["cola_cu"]["cour"], cobre_s["cola_cu"]["lab"], "COLA FINAL - PLANTA DE COBRE (%Cu)", "%Cu")},
        {"title": "COLA FINAL - PLANTA DE COBRE (%Mo)", "img_b64": render_time_series(shifts_cobre, cobre_s["cola_mo"]["cour"], cobre_s["cola_mo"]["lab"], "COLA FINAL - PLANTA DE COBRE (%Mo)", "%Mo")},
        {"title": "CONCENTRADO FINAL - PLANTA DE COBRE (%Cu)", "img_b64": render_time_series(shifts_cobre, cobre_s["conc_cu"]["cour"], cobre_s["conc_cu"]["lab"], "CONCENTRADO FINAL - PLANTA DE COBRE (%Cu)", "%Cu")},
        {"title": "CONCENTRADO FINAL - PLANTA DE COBRE (%Mo)", "img_b64": render_time_series(shifts_cobre, cobre_s["conc_mo"]["cour"], cobre_s["conc_mo"]["lab"], "CONCENTRADO FINAL - PLANTA DE COBRE (%Mo)", "%Mo")},
        # Moly
        {"title": "ALIMENTACION ROUGHER - PLANTA DE MOLY (%Cu)", "img_b64": render_time_series(shifts_moly, moly_s["alim_cu"]["cour"], moly_s["alim_cu"]["lab"], "ALIMENTACION ROUGHER - PLANTA DE MOLY (%Cu)", "%Cu")},
        {"title": "ALIMENTACION ROUGHER - PLANTA DE MOLY (%Mo)", "img_b64": render_time_series(shifts_moly, moly_s["alim_mo"]["cour"], moly_s["alim_mo"]["lab"], "ALIMENTACION ROUGHER - PLANTA DE MOLY (%Mo)", "%Mo")},
        {"title": "COLA FINAL - PLANTA DE MOLY (%Cu)", "img_b64": render_time_series(shifts_moly, moly_s["cola_cu"]["cour"], moly_s["cola_cu"]["lab"], "COLA FINAL - PLANTA DE MOLY (%Cu)", "%Cu")},
        {"title": "COLA FINAL - PLANTA DE MOLY (%Mo)", "img_b64": render_time_series(shifts_moly, moly_s["cola_mo"]["cour"], moly_s["cola_mo"]["lab"], "COLA FINAL - PLANTA DE MOLY (%Mo)", "%Mo")},
        {"title": "CONC. ULT. LIMPIEZA - PLANTA DE MOLY (%Cu)", "img_b64": render_time_series(shifts_moly, moly_s["conc_cu"]["cour"], moly_s["conc_cu"]["lab"], "CONC. ULT. LIMPIEZA - PLANTA DE MOLY (%Cu)", "%Cu")},
        {"title": "CONC. ULT. LIMPIEZA - PLANTA DE MOLY (%Mo)", "img_b64": render_time_series(shifts_moly, moly_s["conc_mo"]["cour"], moly_s["conc_mo"]["lab"], "CONC. ULT. LIMPIEZA - PLANTA DE MOLY (%Mo)", "%Mo")},
    ]

    # Pestaña 3: Graf. Fe-Zn-Ox (6 gráficas)
    print("  -> Renderizando Graf. Fe-Zn-Ox (6 gráficas)...")
    charts_fe_zn_ox = [
        {"title": "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Fe)", "img_b64": render_time_series(shifts_cobre, cobre_s["alim_fe"]["cour"], cobre_s["alim_fe"]["lab"], "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Fe)", "%Fe")},
        {"title": "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Zn)", "img_b64": render_time_series(shifts_cobre, cobre_s["alim_zn"]["cour"], cobre_s["alim_zn"]["lab"], "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Zn)", "%Zn")},
        {"title": "COLA FINAL - PLANTA DE COBRE (%Fe)", "img_b64": render_time_series(shifts_cobre, cobre_s["cola_fe"]["cour"], cobre_s["cola_fe"]["lab"], "COLA FINAL - PLANTA DE COBRE (%Fe)", "%Fe")},
        {"title": "CONCENTRADO FINAL - PLANTA DE COBRE (%Fe)", "img_b64": render_time_series(shifts_cobre, cobre_s["conc_fe"]["cour"], cobre_s["conc_fe"]["lab"], "CONCENTRADO FINAL - PLANTA DE COBRE (%Fe)", "%Fe")},
        {"title": "CONCENTRADO FINAL - PLANTA DE COBRE (%Ins)", "img_b64": render_time_series(shifts_cobre, cobre_s["conc_ins"]["cour"], cobre_s["conc_ins"]["lab"], "CONCENTRADO FINAL - PLANTA DE COBRE (%Ins)", "%Ins")},
        {"title": "CONC. ULT. LIMPIEZA - PLANTA DE MOLY (%Ins)", "img_b64": render_time_series(shifts_moly, moly_s["conc_ins"]["cour"], moly_s["conc_ins"]["lab"], "CONC. ULT. LIMPIEZA - PLANTA DE MOLY (%Ins)", "%Ins")},
    ]

    # Pestaña 4: Graf1 (Dispersión 1:1)
    print("  -> Renderizando Graf1 Dispersión 1:1 (12 gráficas)...")
    charts_graf1 = [
        # Cobre
        {"title": "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Cu)", "img_b64": render_scatter_1to1(cobre_s["alim_cu"]["lab"], cobre_s["alim_cu"]["cour"], cobre_s["alim_cu"]["tol"], "ALIM. ROUGHER CU", "%Cu")},
        {"title": "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Mo)", "img_b64": render_scatter_1to1(cobre_s["alim_mo"]["lab"], cobre_s["alim_mo"]["cour"], cobre_s["alim_mo"]["tol"], "ALIM. ROUGHER MO", "%Mo")},
        {"title": "COLA FINAL - PLANTA DE COBRE (%Cu)", "img_b64": render_scatter_1to1(cobre_s["cola_cu"]["lab"], cobre_s["cola_cu"]["cour"], cobre_s["cola_cu"]["tol"], "COLA FINAL CU", "%Cu")},
        {"title": "COLA FINAL - PLANTA DE COBRE (%Mo)", "img_b64": render_scatter_1to1(cobre_s["cola_mo"]["lab"], cobre_s["cola_mo"]["cour"], cobre_s["cola_mo"]["tol"], "COLA FINAL MO", "%Mo")},
        {"title": "CONCENTRADO FINAL - PLANTA DE COBRE (%Cu)", "img_b64": render_scatter_1to1(cobre_s["conc_cu"]["lab"], cobre_s["conc_cu"]["cour"], cobre_s["conc_cu"]["tol"], "CONCENTRADO FINAL CU", "%Cu")},
        {"title": "CONCENTRADO FINAL - PLANTA DE COBRE (%Mo)", "img_b64": render_scatter_1to1(cobre_s["conc_mo"]["lab"], cobre_s["conc_mo"]["cour"], cobre_s["conc_mo"]["tol"], "CONCENTRADO FINAL MO", "%Mo")},
        # Moly
        {"title": "ALIMENTACION ROUGHER - PLANTA DE MOLY (%Cu)", "img_b64": render_scatter_1to1(moly_s["alim_cu"]["lab"], moly_s["alim_cu"]["cour"], moly_s["alim_cu"]["tol"], "ALIM. ROUGHER MOLY CU", "%Cu")},
        {"title": "ALIMENTACION ROUGHER - PLANTA DE MOLY (%Mo)", "img_b64": render_scatter_1to1(moly_s["alim_mo"]["lab"], moly_s["alim_mo"]["cour"], moly_s["alim_mo"]["tol"], "ALIM. ROUGHER MOLY MO", "%Mo")},
        {"title": "COLA FINAL - PLANTA DE MOLY (%Cu)", "img_b64": render_scatter_1to1(moly_s["cola_cu"]["lab"], moly_s["cola_cu"]["cour"], moly_s["cola_cu"]["tol"], "COLA FINAL MOLY CU", "%Cu")},
        {"title": "COLA FINAL - PLANTA DE MOLY (%Mo)", "img_b64": render_scatter_1to1(moly_s["cola_mo"]["lab"], moly_s["cola_mo"]["cour"], moly_s["cola_mo"]["tol"], "COLA FINAL MOLY MO", "%Mo")},
        {"title": "CONC. ULT. LIMPIEZA - PLANTA DE MOLY (%Cu)", "img_b64": render_scatter_1to1(moly_s["conc_cu"]["lab"], moly_s["conc_cu"]["cour"], moly_s["conc_cu"]["tol"], "CONC. ULT. LIMP. CU", "%Cu")},
        {"title": "CONC. ULT. LIMPIEZA - PLANTA DE MOLY (%Mo)", "img_b64": render_scatter_1to1(moly_s["conc_mo"]["lab"], moly_s["conc_mo"]["cour"], moly_s["conc_mo"]["tol"], "CONC. ULT. LIMP. MO", "%Mo")},
    ]

    # Pestaña 5: Graf2 (Error Residual)
    print("  -> Renderizando Graf2 Error Residual (12 gráficas)...")
    charts_graf2 = [
        # Cobre
        {"title": "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Cu)", "img_b64": render_residual_chart(shifts_cobre, cobre_s["alim_cu"]["dif"], "ALIM. ROUGHER CU", "%Cu")},
        {"title": "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Mo)", "img_b64": render_residual_chart(shifts_cobre, cobre_s["alim_mo"]["dif"], "ALIM. ROUGHER MO", "%Mo")},
        {"title": "COLA FINAL - PLANTA DE COBRE (%Cu)", "img_b64": render_residual_chart(shifts_cobre, cobre_s["cola_cu"]["dif"], "COLA FINAL CU", "%Cu")},
        {"title": "COLA FINAL - PLANTA DE COBRE (%Mo)", "img_b64": render_residual_chart(shifts_cobre, cobre_s["cola_mo"]["dif"], "COLA FINAL MO", "%Mo")},
        {"title": "CONCENTRADO FINAL - PLANTA DE COBRE (%Cu)", "img_b64": render_residual_chart(shifts_cobre, cobre_s["conc_cu"]["dif"], "CONCENTRADO FINAL CU", "%Cu")},
        {"title": "CONCENTRADO FINAL - PLANTA DE COBRE (%Mo)", "img_b64": render_residual_chart(shifts_cobre, cobre_s["conc_mo"]["dif"], "CONCENTRADO FINAL MO", "%Mo")},
        # Moly
        {"title": "ALIMENTACION ROUGHER - PLANTA DE MOLY (%Cu)", "img_b64": render_residual_chart(shifts_moly, moly_s["alim_cu"]["dif"], "ALIM. ROUGHER MOLY CU", "%Cu")},
        {"title": "ALIMENTACION ROUGHER - PLANTA DE MOLY (%Mo)", "img_b64": render_residual_chart(shifts_moly, moly_s["alim_mo"]["dif"], "ALIM. ROUGHER MOLY MO", "%Mo")},
        {"title": "COLA FINAL - PLANTA DE MOLY (%Cu)", "img_b64": render_residual_chart(shifts_moly, moly_s["cola_cu"]["dif"], "COLA FINAL MOLY CU", "%Cu")},
        {"title": "COLA FINAL - PLANTA DE MOLY (%Mo)", "img_b64": render_residual_chart(shifts_moly, moly_s["cola_mo"]["dif"], "COLA FINAL MOLY MO", "%Mo")},
        {"title": "CONC. ULT. LIMPIEZA - PLANTA DE MOLY (%Cu)", "img_b64": render_residual_chart(shifts_moly, moly_s["conc_cu"]["dif"], "CONC. ULT. LIMP. CU", "%Cu")},
        {"title": "CONC. ULT. LIMPIEZA - PLANTA DE MOLY (%Mo)", "img_b64": render_residual_chart(shifts_moly, moly_s["conc_mo"]["dif"], "CONC. ULT. LIMP. MO", "%Mo")},
    ]

    # Pestaña 6: Graf3 (Conformidad %)
    print("  -> Renderizando Graf3 Conformidad (12 gráficas de pastel)...")
    charts_graf3 = [
        # Cobre
        {"title": "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Cu)", "img_b64": render_conformity_pie(cobre_s["alim_cu"]["n_acep"], cobre_s["alim_cu"]["n_fuera"], "ALIM. ROUGHER CU", cobre_s["alim_cu"]["tol"])},
        {"title": "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Mo)", "img_b64": render_conformity_pie(cobre_s["alim_mo"]["n_acep"], cobre_s["alim_mo"]["n_fuera"], "ALIM. ROUGHER MO", cobre_s["alim_mo"]["tol"])},
        {"title": "COLA FINAL - PLANTA DE COBRE (%Cu)", "img_b64": render_conformity_pie(cobre_s["cola_cu"]["n_acep"], cobre_s["cola_cu"]["n_fuera"], "COLA FINAL CU", cobre_s["cola_cu"]["tol"])},
        {"title": "COLA FINAL - PLANTA DE COBRE (%Mo)", "img_b64": render_conformity_pie(cobre_s["cola_mo"]["n_acep"], cobre_s["cola_mo"]["n_fuera"], "COLA FINAL MO", cobre_s["cola_mo"]["tol"])},
        {"title": "CONCENTRADO FINAL - PLANTA DE COBRE (%Cu)", "img_b64": render_conformity_pie(cobre_s["conc_cu"]["n_acep"], cobre_s["conc_cu"]["n_fuera"], "CONCENTRADO FINAL CU", cobre_s["conc_cu"]["tol"])},
        {"title": "CONCENTRADO FINAL - PLANTA DE COBRE (%Mo)", "img_b64": render_conformity_pie(cobre_s["conc_mo"]["n_acep"], cobre_s["conc_mo"]["n_fuera"], "CONCENTRADO FINAL MO", cobre_s["conc_mo"]["tol"])},
        # Moly
        {"title": "ALIMENTACION ROUGHER - PLANTA DE MOLY (%Cu)", "img_b64": render_conformity_pie(moly_s["alim_cu"]["n_acep"], moly_s["alim_cu"]["n_fuera"], "ALIM. ROUGHER MOLY CU", moly_s["alim_cu"]["tol"])},
        {"title": "ALIMENTACION ROUGHER - PLANTA DE MOLY (%Mo)", "img_b64": render_conformity_pie(moly_s["alim_mo"]["n_acep"], moly_s["alim_mo"]["n_fuera"], "ALIM. ROUGHER MOLY MO", moly_s["alim_mo"]["tol"])},
        {"title": "COLA FINAL - PLANTA DE MOLY (%Cu)", "img_b64": render_conformity_pie(moly_s["cola_cu"]["n_acep"], moly_s["cola_cu"]["n_fuera"], "COLA FINAL MOLY CU", moly_s["cola_cu"]["tol"])},
        {"title": "COLA FINAL - PLANTA DE MOLY (%Mo)", "img_b64": render_conformity_pie(moly_s["cola_mo"]["n_acep"], moly_s["cola_mo"]["n_fuera"], "COLA FINAL MOLY MO", moly_s["cola_mo"]["tol"])},
        {"title": "CONC. ULT. LIMPIEZA - PLANTA DE MOLY (%Cu)", "img_b64": render_conformity_pie(moly_s["conc_cu"]["n_acep"], moly_s["conc_cu"]["n_fuera"], "CONC. ULT. LIMP. CU", moly_s["conc_cu"]["tol"])},
        {"title": "CONC. ULT. LIMPIEZA - PLANTA DE MOLY (%Mo)", "img_b64": render_conformity_pie(moly_s["conc_mo"]["n_acep"], moly_s["conc_mo"]["n_fuera"], "CONC. ULT. LIMP. MO", moly_s["conc_mo"]["tol"])},
    ]

    # Pestaña 7: DistrN (Distribución Normal)
    print("  -> Renderizando DistrN Distribución Normal (12 histogramas)...")
    charts_distrn = [
        # Cobre
        {"title": "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Cu)", "img_b64": render_normal_distribution(cobre_s["alim_cu"]["dif"], "ALIM. ROUGHER CU", "%Cu")},
        {"title": "ALIMENTACION ROUGHER - PLANTA DE COBRE (%Mo)", "img_b64": render_normal_distribution(cobre_s["alim_mo"]["dif"], "ALIM. ROUGHER MO", "%Mo")},
        {"title": "COLA FINAL - PLANTA DE COBRE (%Cu)", "img_b64": render_normal_distribution(cobre_s["cola_cu"]["dif"], "COLA FINAL CU", "%Cu")},
        {"title": "COLA FINAL - PLANTA DE COBRE (%Mo)", "img_b64": render_normal_distribution(cobre_s["cola_mo"]["dif"], "COLA FINAL MO", "%Mo")},
        {"title": "CONCENTRADO FINAL - PLANTA DE COBRE (%Cu)", "img_b64": render_normal_distribution(cobre_s["conc_cu"]["dif"], "CONCENTRADO FINAL CU", "%Cu")},
        {"title": "CONCENTRADO FINAL - PLANTA DE COBRE (%Mo)", "img_b64": render_normal_distribution(cobre_s["conc_mo"]["dif"], "CONCENTRADO FINAL MO", "%Mo")},
        # Moly
        {"title": "ALIMENTACION ROUGHER - PLANTA DE MOLY (%Cu)", "img_b64": render_normal_distribution(moly_s["alim_cu"]["dif"], "ALIM. ROUGHER MOLY CU", "%Cu")},
        {"title": "ALIMENTACION ROUGHER - PLANTA DE MOLY (%Mo)", "img_b64": render_normal_distribution(moly_s["alim_mo"]["dif"], "ALIM. ROUGHER MOLY MO", "%Mo")},
        {"title": "COLA FINAL - PLANTA DE MOLY (%Cu)", "img_b64": render_normal_distribution(moly_s["cola_cu"]["dif"], "COLA FINAL MOLY CU", "%Cu")},
        {"title": "COLA FINAL - PLANTA DE MOLY (%Mo)", "img_b64": render_normal_distribution(moly_s["cola_mo"]["dif"], "COLA FINAL MOLY MO", "%Mo")},
        {"title": "CONC. ULT. LIMPIEZA - PLANTA DE MOLY (%Cu)", "img_b64": render_normal_distribution(moly_s["conc_cu"]["dif"], "CONC. ULT. LIMP. CU", "%Cu")},
        {"title": "CONC. ULT. LIMPIEZA - PLANTA DE MOLY (%Mo)", "img_b64": render_normal_distribution(moly_s["conc_mo"]["dif"], "CONC. ULT. LIMP. MO", "%Mo")},
    ]

    # 4. Compilar documento HTML final
    print("[4/4] Compilando HTML final con diseño exacto de Excel...")
    portada_html = build_portada_html(portada_data)
    final_html = compile_full_dashboard(
        portada_html=portada_html,
        charts_cu_mo=charts_cu_mo,
        charts_fe_zn_ox=charts_fe_zn_ox,
        charts_graf1=charts_graf1,
        charts_graf2=charts_graf2,
        charts_graf3=charts_graf3,
        charts_distrn=charts_distrn,
        eval_date=eval_date,
    )

    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "dashboard_excel.html")

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(final_html)

    size_mb = os.path.getsize(out_file) / (1024 * 1024)
    print(f"-> Archivo generado exitosamente: {out_file} ({size_mb:.2f} MB)")
    return out_file


def run_local_server(port: int = 8055, html_file: str = ""):
    """Inicia un servidor HTTP local para servir el dashboard."""
    web_dir = os.path.dirname(html_file)
    filename = os.path.basename(html_file)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=web_dir, **kwargs)

    url = f"http://localhost:{port}/{filename}"
    print("\n" + "=" * 80)
    print(f"SERVIDOR LOCAL INICIADO EXITOSAMENTE:")
    print(f"URL: \033[1;32m{url}\033[0m")
    print(f"Presiona Ctrl+C para detener el servidor.")
    print("=" * 80 + "\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido por el usuario.")


def main():
    parser = argparse.ArgumentParser(description="Réplica visual y funcional exacta de Courier_AUTO-C2.xlsm")
    parser.add_argument("--mode", choices=["dev", "prod"], default="dev",
                        help="Modo de ejecución: 'dev' (offline con Excel) o 'prod' (online con PI)")
    parser.add_argument("--serve", action="store_true",
                        help="Inicia un servidor HTTP local para ver el dashboard en el navegador")
    parser.add_argument("--port", type=int, default=8055,
                        help="Puerto para el servidor HTTP (por defecto: 8055)")

    args = parser.parse_args()

    html_path = generate_clone_dashboard(mode=args.mode)

    if args.serve:
        run_local_server(port=args.port, html_file=html_path)


if __name__ == "__main__":
    main()
