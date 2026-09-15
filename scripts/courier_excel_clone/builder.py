# -*- coding: utf-8 -*-
"""
scripts/courier_excel_clone/builder.py
======================================
Compilador HTML que replica con precisión milimétrica la hoja 'Portada'
de 'Courier_AUTO-C2.xlsm' (colores, títulos, bordes, formatos) y ubica
las gráficas en pestañas separadas (Gráf. Cu-Mo, Graf. Fe-Zn-Ox, Graf1, Graf2, Graf3, DistrN).
No incluye ningún cálculo ajeno a lo que muestra el archivo Excel original.
"""

from typing import Dict, Any, List
from datetime import datetime


def _format_val(val, decimals: int = 3, is_pct: bool = False, is_dif: bool = False) -> str:
    """Formatea valores numéricos o texto 'Sin dato'."""
    if val is None or val == "" or val == "Sin dato":
        return "<span class='sin-dato'>Sin dato</span>"
    try:
        fval = float(val)
        txt = f"{fval:.{decimals}f}"
        if is_pct:
            txt += "%"
        if is_dif:
            return f"<span class='text-red'>{txt}</span>"
        return txt
    except (ValueError, TypeError):
        return str(val)


def build_portada_html(portada_data: Dict[str, Any]) -> str:
    """
    Genera el código HTML de las tablas de la hoja 'Portada' (Cobre y Moly).
    """
    cobre = portada_data["cobre"]
    moly = portada_data["moly"]

    html = []

    # ==========================================================================
    # SECCIÓN COBRE C2
    # ==========================================================================
    html.append(f"""
    <div class="excel-section">
        <!-- TÍTULO PRINCIPAL COBRE -->
        <table class="excel-table">
            <tr>
                <th colspan="13" class="excel-main-title">
                    {cobre['title']}
                    <span class="excel-date">Fecha: {cobre['date_str']}</span>
                </th>
            </tr>
        </table>
    """)

    # Tablas de Corrientes Principales Cobre
    for stream in cobre["streams"]:
        sname = stream["name"]
        elements = stream["elements"]

        html.append(f"""
        <table class="excel-table stream-table">
            <!-- NOMBRE DE LA CORRIENTE -->
            <tr class="row-stream-header">
                <td class="col-lbl-empty"></td>
                <td colspan="12" class="cell-stream-name">{sname}</td>
            </tr>
        """)

        # Agrupamos elementos de 3 en 3 (como en Excel: Cu, Mo, Fe / Zn, Ox)
        for chunk_idx in range(0, len(elements), 3):
            sub_elems = elements[chunk_idx:chunk_idx + 3]

            # Fila de nombres de elementos (Fondo Amarillo)
            html.append("<tr class='row-elem-header'><td class='col-lbl-empty'></td>")
            for elem in sub_elems:
                html.append(f"<td colspan='4' class='cell-elem-name'>{elem['name']}</td>")
            # Si hay menos de 3 elementos en la fila, rellenar celdas vacías
            rem = 3 - len(sub_elems)
            if rem > 0:
                html.append(f"<td colspan='{rem * 4}' class='cell-empty'></td>")
            html.append("</tr>")

            # Fila de Turnos (Turno A / Turno B)
            html.append("<tr class='row-turn-header'><td class='col-lbl-empty'></td>")
            for _ in sub_elems:
                html.append("<td colspan='2' class='cell-turn'>Turno A</td>")
                html.append("<td colspan='2' class='cell-turn'>Turno B</td>")
            if rem > 0:
                html.append(f"<td colspan='{rem * 4}' class='cell-empty'></td>")
            html.append("</tr>")

            # Fila de Columnas (Courier / Lab)
            html.append("<tr class='row-col-header'><td class='col-lbl-empty'></td>")
            for _ in sub_elems:
                html.append("<td class='cell-cour-lab'>Courier</td>")
                html.append("<td class='cell-cour-lab'>Lab</td>")
                html.append("<td class='cell-cour-lab'>Courier</td>")
                html.append("<td class='cell-cour-lab'>Lab</td>")
            if rem > 0:
                html.append(f"<td colspan='{rem * 4}' class='cell-empty'></td>")
            html.append("</tr>")

            # Fila de Valores
            html.append("<tr class='row-values'><td class='col-lbl-empty'></td>")
            for elem in sub_elems:
                dec = elem["dec"]
                c_a = _format_val(elem["turn_a"]["cour"], dec)
                l_a = _format_val(elem["turn_a"]["lab"], dec)
                c_b = _format_val(elem["turn_b"]["cour"], dec)
                l_b = _format_val(elem["turn_b"]["lab"], dec)
                html.append(f"<td class='cell-num'>{c_a}</td><td class='cell-num'>{l_a}</td>")
                html.append(f"<td class='cell-num'>{c_b}</td><td class='cell-num'>{l_b}</td>")
            if rem > 0:
                html.append(f"<td colspan='{rem * 4}' class='cell-empty'></td>")
            html.append("</tr>")

            # Fila de Diferencia-%Dif.
            html.append("<tr class='row-diff'><td class='cell-lbl-diff'>Diferencia-%Dif.</td>")
            for elem in sub_elems:
                dec = elem["dec"]
                d_a = _format_val(elem["dif_a"], dec, is_dif=True)
                p_a = _format_val(elem["pct_a"], 2, is_pct=True)
                d_b = _format_val(elem["dif_b"], dec, is_dif=True)
                p_b = _format_val(elem["pct_b"], 2, is_pct=True)
                html.append(f"<td class='cell-diff'>{d_a}</td><td class='cell-pct'>{p_a}</td>")
                html.append(f"<td class='cell-diff'>{d_b}</td><td class='cell-pct'>{p_b}</td>")
            if rem > 0:
                html.append(f"<td colspan='{rem * 4}' class='cell-empty'></td>")
            html.append("</tr>")

        html.append("</table><div class='table-spacer'></div>")

    # Tabla de Recuperación Cobre
    html.append("""
    <table class="excel-table recovery-table">
        <tr class="row-elem-header">
            <td class="col-lbl-empty"></td>
    """)
    for rec in cobre["recovery"]:
        html.append(f"<td colspan='4' class='cell-rec-header'>{rec['name']}</td>")
    html.append("<td colspan='4' class='cell-empty'></td></tr>")

    html.append("<tr class='row-turn-header'><td class='col-lbl-empty'></td>")
    for _ in cobre["recovery"]:
        html.append("<td colspan='2' class='cell-turn'>Turno A</td><td colspan='2' class='cell-turn'>Turno B</td>")
    html.append("<td colspan='4' class='cell-empty'></td></tr>")

    html.append("<tr class='row-col-header'><td class='col-lbl-empty'></td>")
    for _ in cobre["recovery"]:
        html.append("<td class='cell-cour-lab'>Courier</td><td class='cell-cour-lab'>Lab</td>")
        html.append("<td class='cell-cour-lab'>Courier</td><td class='cell-cour-lab'>Lab</td>")
    html.append("<td colspan='4' class='cell-empty'></td></tr>")

    html.append("<tr class='row-values'><td class='col-lbl-empty'></td>")
    for rec in cobre["recovery"]:
        c_a = _format_val(rec["turn_a"]["cour"], 2, is_pct=True)
        l_a = _format_val(rec["turn_a"]["lab"], 2, is_pct=True)
        c_b = _format_val(rec["turn_b"]["cour"], 2, is_pct=True)
        l_b = _format_val(rec["turn_b"]["lab"], 2, is_pct=True)
        html.append(f"<td class='cell-num'>{c_a}</td><td class='cell-num'>{l_a}</td>")
        html.append(f"<td class='cell-num'>{c_b}</td><td class='cell-num'>{l_b}</td>")
    html.append("<td colspan='4' class='cell-empty'></td></tr></table>")
    html.append("<div class='table-spacer'></div>")

    # Tabla Desviación Estándar de Diferencias Cobre
    stdev_c = cobre["stdev_table"]
    html.append(f"""
    <table class="excel-table stdev-table">
        <tr>
            <td class="cell-empty" style="width:140px;"></td>
            <th colspan="{len(stdev_c['columns'])}" class="cell-stdev-header">{stdev_c['title']}</th>
        </tr>
        <tr class="row-elem-header">
            <td class="cell-empty"></td>
    """)
    for col_name, _ in stdev_c["columns"]:
        html.append(f"<td class='cell-stdev-col'>{col_name}</td>")
    html.append("</tr><tr class='row-values'>")
    html.append(f"<td class='cell-stdev-label'>{stdev_c['label']}</td>")
    for _, val in stdev_c["columns"]:
        fmt_v = _format_val(val, 2, is_pct=True)
        html.append(f"<td class='cell-num cell-stdev-val'>{fmt_v}</td>")
    html.append("</tr></table>")
    html.append("<div class='table-spacer'></div>")

    # Tabla de Flujos Intermedios Cobre
    html.append(f"""
    <table class="excel-table intermediate-table">
        <tr>
            <td class="cell-stream-name" style="width:220px;">Fecha: {cobre['date_str']}</td>
            <th colspan="6" class="cell-guardia-header">GUARDIA &quot;A&quot;</th>
            <th colspan="6" class="cell-guardia-header">GUARDIA &quot;B&quot;</th>
        </tr>
        <tr class="row-interm-sub">
            <td class="cell-interm-th">Corriente / Flujo</td>
            <td class="cell-interm-th">Horas</td>
            <td class="cell-interm-th">%Oper</td>
            <td class="cell-interm-th">Ensayo</td>
            <td class="cell-interm-th">M&iacute;n</td>
            <td class="cell-interm-th">M&aacute;x</td>
            <td class="cell-interm-th">Avg</td>
            <td class="cell-interm-th">Horas</td>
            <td class="cell-interm-th">%Oper</td>
            <td class="cell-interm-th">Ensayo</td>
            <td class="cell-interm-th">M&iacute;n</td>
            <td class="cell-interm-th">M&aacute;x</td>
            <td class="cell-interm-th">Avg</td>
        </tr>
    """)

    for row_interm in cobre["intermediate_streams"]:
        sname = row_interm["stream"]
        ga = row_interm["guardia_a"]
        gb = row_interm["guardia_b"]

        # Fila 1: Ensayo Cu
        hrs_a = _format_val(ga["hrs"], 1)
        op_a = _format_val(ga["op"] * 100 if isinstance(ga["op"], (int, float)) else ga["op"], 1, is_pct=True)
        e1_name_a = ga["e1"]["name"] or "%Cu"
        min1_a = _format_val(ga["e1"]["min"], 3)
        max1_a = _format_val(ga["e1"]["max"], 3)
        avg1_a = _format_val(ga["e1"]["avg"], 3)

        hrs_b = _format_val(gb["hrs"], 1)
        op_b = _format_val(gb["op"] * 100 if isinstance(gb["op"], (int, float)) else gb["op"], 1, is_pct=True)
        e1_name_b = gb["e1"]["name"] or "%Cu"
        min1_b = _format_val(gb["e1"]["min"], 3)
        max1_b = _format_val(gb["e1"]["max"], 3)
        avg1_b = _format_val(gb["e1"]["avg"], 3)

        # Fila 2: Ensayo Mo
        e2_name_a = ga["e2"]["name"] or "%Mo"
        min2_a = _format_val(ga["e2"]["min"], 3)
        max2_a = _format_val(ga["e2"]["max"], 3)
        avg2_a = _format_val(ga["e2"]["avg"], 3)

        e2_name_b = gb["e2"]["name"] or "%Mo"
        min2_b = _format_val(gb["e2"]["min"], 3)
        max2_b = _format_val(gb["e2"]["max"], 3)
        avg2_b = _format_val(gb["e2"]["avg"], 3)

        html.append(f"""
        <tr>
            <td rowspan="2" class="cell-interm-stream">{sname}</td>
            <td rowspan="2" class="cell-num">{hrs_a}</td>
            <td rowspan="2" class="cell-num">{op_a}</td>
            <td class="cell-center">{e1_name_a}</td>
            <td class="cell-num">{min1_a}</td>
            <td class="cell-num">{max1_a}</td>
            <td class="cell-num">{avg1_a}</td>
            <td rowspan="2" class="cell-num">{hrs_b}</td>
            <td rowspan="2" class="cell-num">{op_b}</td>
            <td class="cell-center">{e1_name_b}</td>
            <td class="cell-num">{min1_b}</td>
            <td class="cell-num">{max1_b}</td>
            <td class="cell-num">{avg1_b}</td>
        </tr>
        <tr>
            <td class="cell-center">{e2_name_a}</td>
            <td class="cell-num">{min2_a}</td>
            <td class="cell-num">{max2_a}</td>
            <td class="cell-num">{avg2_a}</td>
            <td class="cell-center">{e2_name_b}</td>
            <td class="cell-num">{min2_b}</td>
            <td class="cell-num">{max2_b}</td>
            <td class="cell-num">{avg2_b}</td>
        </tr>
        """)

    html.append("</table></div><!-- Fin Sección Cobre -->")
    html.append("<div class='section-divider'></div>")

    # ==========================================================================
    # SECCIÓN MOLIBDENO C2
    # ==========================================================================
    html.append(f"""
    <div class="excel-section">
        <!-- TÍTULO PRINCIPAL MOLY -->
        <table class="excel-table">
            <tr>
                <th colspan="13" class="excel-main-title">
                    {moly['title']}
                </th>
            </tr>
        </table>
    """)

    # Tablas de Corrientes Principales Moly
    for stream in moly["streams"]:
        sname = stream["name"]
        elements = stream["elements"]

        html.append(f"""
        <table class="excel-table stream-table">
            <tr class="row-stream-header">
                <td class="col-lbl-empty"></td>
                <td colspan="12" class="cell-stream-name">{sname}</td>
            </tr>
        """)

        for chunk_idx in range(0, len(elements), 3):
            sub_elems = elements[chunk_idx:chunk_idx + 3]
            rem = 3 - len(sub_elems)

            # Nombres elementos
            html.append("<tr class='row-elem-header'><td class='col-lbl-empty'></td>")
            for elem in sub_elems:
                html.append(f"<td colspan='4' class='cell-elem-name'>{elem['name']}</td>")
            if rem > 0:
                html.append(f"<td colspan='{rem * 4}' class='cell-empty'></td>")
            html.append("</tr>")

            # Turno A / Turno B
            html.append("<tr class='row-turn-header'><td class='col-lbl-empty'></td>")
            for _ in sub_elems:
                html.append("<td colspan='2' class='cell-turn'>Turno A</td><td colspan='2' class='cell-turn'>Turno B</td>")
            if rem > 0:
                html.append(f"<td colspan='{rem * 4}' class='cell-empty'></td>")
            html.append("</tr>")

            # Courier / Lab
            html.append("<tr class='row-col-header'><td class='col-lbl-empty'></td>")
            for _ in sub_elems:
                html.append("<td class='cell-cour-lab'>Courier</td><td class='cell-cour-lab'>Lab</td>")
                html.append("<td class='cell-cour-lab'>Courier</td><td class='cell-cour-lab'>Lab</td>")
            if rem > 0:
                html.append(f"<td colspan='{rem * 4}' class='cell-empty'></td>")
            html.append("</tr>")

            # Valores
            html.append("<tr class='row-values'><td class='col-lbl-empty'></td>")
            for elem in sub_elems:
                dec = elem["dec"]
                c_a = _format_val(elem["turn_a"]["cour"], dec)
                l_a = _format_val(elem["turn_a"]["lab"], dec)
                c_b = _format_val(elem["turn_b"]["cour"], dec)
                l_b = _format_val(elem["turn_b"]["lab"], dec)
                html.append(f"<td class='cell-num'>{c_a}</td><td class='cell-num'>{l_a}</td>")
                html.append(f"<td class='cell-num'>{c_b}</td><td class='cell-num'>{l_b}</td>")
            if rem > 0:
                html.append(f"<td colspan='{rem * 4}' class='cell-empty'></td>")
            html.append("</tr>")

            # Diferencia-%Dif.
            html.append("<tr class='row-diff'><td class='cell-lbl-diff'>Diferencia-%Dif.</td>")
            for elem in sub_elems:
                dec = elem["dec"]
                d_a = _format_val(elem["dif_a"], dec, is_dif=True)
                p_a = _format_val(elem["pct_a"], 2, is_pct=True)
                d_b = _format_val(elem["dif_b"], dec, is_dif=True)
                p_b = _format_val(elem["pct_b"], 2, is_pct=True)
                html.append(f"<td class='cell-diff'>{d_a}</td><td class='cell-pct'>{p_a}</td>")
                html.append(f"<td class='cell-diff'>{d_b}</td><td class='cell-pct'>{p_b}</td>")
            if rem > 0:
                html.append(f"<td colspan='{rem * 4}' class='cell-empty'></td>")
            html.append("</tr>")

        html.append("</table><div class='table-spacer'></div>")

    # Recuperación Moly
    html.append("""
    <table class="excel-table recovery-table">
        <tr class="row-elem-header">
            <td class="col-lbl-empty"></td>
    """)
    for rec in moly["recovery"]:
        html.append(f"<td colspan='4' class='cell-rec-header'>{rec['name']}</td>")
    html.append("<td colspan='8' class='cell-empty'></td></tr>")

    html.append("<tr class='row-turn-header'><td class='col-lbl-empty'></td>")
    for _ in moly["recovery"]:
        html.append("<td colspan='2' class='cell-turn'>Turno A</td><td colspan='2' class='cell-turn'>Turno B</td>")
    html.append("<td colspan='8' class='cell-empty'></td></tr>")

    html.append("<tr class='row-col-header'><td class='col-lbl-empty'></td>")
    for _ in moly["recovery"]:
        html.append("<td class='cell-cour-lab'>Courier</td><td class='cell-cour-lab'>Lab</td>")
        html.append("<td class='cell-cour-lab'>Courier</td><td class='cell-cour-lab'>Lab</td>")
    html.append("<td colspan='8' class='cell-empty'></td></tr>")

    html.append("<tr class='row-values'><td class='col-lbl-empty'></td>")
    for rec in moly["recovery"]:
        c_a = _format_val(rec["turn_a"]["cour"], 2, is_pct=True)
        l_a = _format_val(rec["turn_a"]["lab"], 2, is_pct=True)
        c_b = _format_val(rec["turn_b"]["cour"], 2, is_pct=True)
        l_b = _format_val(rec["turn_b"]["lab"], 2, is_pct=True)
        html.append(f"<td class='cell-num'>{c_a}</td><td class='cell-num'>{l_a}</td>")
        html.append(f"<td class='cell-num'>{c_b}</td><td class='cell-num'>{l_b}</td>")
    html.append("<td colspan='8' class='cell-empty'></td></tr></table>")
    html.append("<div class='table-spacer'></div>")

    # Tabla Desviación Estándar Moly
    stdev_m = moly["stdev_table"]
    html.append(f"""
    <table class="excel-table stdev-table">
        <tr>
            <td class="cell-empty" style="width:140px;"></td>
            <th colspan="{len(stdev_m['columns'])}" class="cell-stdev-header">{stdev_m['title']}</th>
        </tr>
        <tr class="row-elem-header">
            <td class="cell-empty"></td>
    """)
    for col_name, _ in stdev_m["columns"]:
        html.append(f"<td class='cell-stdev-col'>{col_name}</td>")
    html.append("</tr><tr class='row-values'>")
    html.append(f"<td class='cell-stdev-label'>{stdev_m['label']}</td>")
    for _, val in stdev_m["columns"]:
        fmt_v = _format_val(val, 2, is_pct=True)
        html.append(f"<td class='cell-num cell-stdev-val'>{fmt_v}</td>")
    html.append("</tr></table>")
    html.append("<div class='table-spacer'></div>")

    # Flujos Intermedios Moly
    html.append(f"""
    <table class="excel-table intermediate-table">
        <tr>
            <td class="cell-stream-name" style="width:220px;">Fecha: {cobre['date_str']}</td>
            <th colspan="6" class="cell-guardia-header">GUARDIA &quot;A&quot;</th>
            <th colspan="6" class="cell-guardia-header">GUARDIA &quot;B&quot;</th>
        </tr>
        <tr class="row-interm-sub">
            <td class="cell-interm-th">Corriente / Flujo</td>
            <td class="cell-interm-th">Horas</td>
            <td class="cell-interm-th">%Oper</td>
            <td class="cell-interm-th">Ensayo</td>
            <td class="cell-interm-th">M&iacute;n</td>
            <td class="cell-interm-th">M&aacute;x</td>
            <td class="cell-interm-th">Avg</td>
            <td class="cell-interm-th">Horas</td>
            <td class="cell-interm-th">%Oper</td>
            <td class="cell-interm-th">Ensayo</td>
            <td class="cell-interm-th">M&iacute;n</td>
            <td class="cell-interm-th">M&aacute;x</td>
            <td class="cell-interm-th">Avg</td>
        </tr>
    """)

    for row_interm in moly["intermediate_streams"]:
        sname = row_interm["stream"]
        ga = row_interm["guardia_a"]
        gb = row_interm["guardia_b"]

        hrs_a = _format_val(ga["hrs"], 1)
        op_a = _format_val(ga["op"] * 100 if isinstance(ga["op"], (int, float)) else ga["op"], 1, is_pct=True)
        e1_name_a = ga["e1"]["name"] or "%Cu"
        min1_a = _format_val(ga["e1"]["min"], 3)
        max1_a = _format_val(ga["e1"]["max"], 3)
        avg1_a = _format_val(ga["e1"]["avg"], 3)

        hrs_b = _format_val(gb["hrs"], 1)
        op_b = _format_val(gb["op"] * 100 if isinstance(gb["op"], (int, float)) else gb["op"], 1, is_pct=True)
        e1_name_b = gb["e1"]["name"] or "%Cu"
        min1_b = _format_val(gb["e1"]["min"], 3)
        max1_b = _format_val(gb["e1"]["max"], 3)
        avg1_b = _format_val(gb["e1"]["avg"], 3)

        e2_name_a = ga["e2"]["name"] or "%Mo"
        min2_a = _format_val(ga["e2"]["min"], 3)
        max2_a = _format_val(ga["e2"]["max"], 3)
        avg2_a = _format_val(ga["e2"]["avg"], 3)

        e2_name_b = gb["e2"]["name"] or "%Mo"
        min2_b = _format_val(gb["e2"]["min"], 3)
        max2_b = _format_val(gb["e2"]["max"], 3)
        avg2_b = _format_val(gb["e2"]["avg"], 3)

        html.append(f"""
        <tr>
            <td rowspan="2" class="cell-interm-stream">{sname}</td>
            <td rowspan="2" class="cell-num">{hrs_a}</td>
            <td rowspan="2" class="cell-num">{op_a}</td>
            <td class="cell-center">{e1_name_a}</td>
            <td class="cell-num">{min1_a}</td>
            <td class="cell-num">{max1_a}</td>
            <td class="cell-num">{avg1_a}</td>
            <td rowspan="2" class="cell-num">{hrs_b}</td>
            <td rowspan="2" class="cell-num">{op_b}</td>
            <td class="cell-center">{e1_name_b}</td>
            <td class="cell-num">{min1_b}</td>
            <td class="cell-num">{max1_b}</td>
            <td class="cell-num">{avg1_b}</td>
        </tr>
        <tr>
            <td class="cell-center">{e2_name_a}</td>
            <td class="cell-num">{min2_a}</td>
            <td class="cell-num">{max2_a}</td>
            <td class="cell-num">{avg2_a}</td>
            <td class="cell-center">{e2_name_b}</td>
            <td class="cell-num">{min2_b}</td>
            <td class="cell-num">{max2_b}</td>
            <td class="cell-num">{avg2_b}</td>
        </tr>
        """)

    html.append("</table></div><!-- Fin Sección Moly -->")
    return "\n".join(html)


def compile_full_dashboard(
    portada_html: str,
    charts_cu_mo: List[Dict[str, str]],
    charts_fe_zn_ox: List[Dict[str, str]],
    charts_graf1: List[Dict[str, str]],
    charts_graf2: List[Dict[str, str]],
    charts_graf3: List[Dict[str, str]],
    charts_distrn: List[Dict[str, str]],
    eval_date: str = "",
) -> str:
    """
    Compila el documento HTML final con sistema de pestañas nativas que replican
    exactamente las hojas del libro de Excel original.
    """

    def _render_chart_grid(chart_list: List[Dict[str, str]]) -> str:
        items = []
        for ch in chart_list:
            items.append(f"""
            <div class="chart-card">
                <div class="chart-title">{ch['title']}</div>
                <img src="{ch['img_b64']}" alt="{ch['title']}" loading="lazy"/>
            </div>
            """)
        return f'<div class="chart-grid">{"".join(items)}</div>'

    html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Courier Auto C2 - Réplica Exacta de Excel</title>
    <!-- Auto-recarga cada 5 minutos (300 segundos) -->
    <meta http-equiv="refresh" content="300">
    <style>
        /* ESTILO GENERAL IDÉNTICO A EXCEL / SEGOE UI */
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: 'Segoe UI', Arial, Helvetica, sans-serif;
            font-size: 11px;
            background-color: #EAEAEA;
            color: #000000;
        }}

        /* BARRA SUPERIOR INSTITUCIONAL */
        .excel-ribbon {{
            background-color: #107C41; /* Verde característico de Microsoft Excel */
            color: #FFFFFF;
            padding: 8px 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        }}
        .ribbon-title {{
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }}
        .ribbon-info {{
            font-size: 11px;
            display: flex;
            gap: 15px;
            align-items: center;
        }}
        .btn-refresh {{
            background-color: #FFFFFF;
            color: #107C41;
            border: none;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: bold;
            border-radius: 3px;
            cursor: pointer;
        }}
        .btn-refresh:hover {{
            background-color: #D4EDDA;
        }}

        /* PESTAÑAS TIPO HOJAS DE CÁLCULO DE EXCEL */
        .tab-bar {{
            background-color: #D9D9D9;
            border-bottom: 1px solid #B0B0B0;
            display: flex;
            padding-left: 10px;
            overflow-x: auto;
            white-space: nowrap;
        }}
        .tab-btn {{
            background-color: #E1E1E1;
            border: 1px solid #B0B0B0;
            border-bottom: none;
            padding: 7px 16px;
            font-size: 11.5px;
            font-weight: 500;
            cursor: pointer;
            color: #333333;
            margin-right: 2px;
            border-radius: 4px 4px 0 0;
            user-select: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .tab-btn:hover {{
            background-color: #F0F0F0;
        }}
        .tab-btn.active {{
            background-color: #FFFFFF;
            font-weight: 700;
            color: #107C41;
            border-top: 3px solid #107C41;
            border-bottom: 1px solid #FFFFFF;
            margin-bottom: -1px;
        }}

        /* CONTENEDOR PRINCIPAL */
        .tab-content-wrapper {{
            padding: 15px 20px;
            max-width: 1350px;
            margin: 0 auto;
        }}
        .tab-pane {{
            display: none;
            background-color: #FFFFFF;
            border: 1px solid #C0C0C0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            padding: 15px 20px;
        }}
        .tab-pane.active {{
            display: block;
        }}

        /* TABLAS EXACTAS DE EXCEL */
        .excel-table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 0;
            font-size: 11px;
        }}
        .excel-table td, .excel-table th {{
            border: 1px solid #B0B0B0;
            padding: 3px 5px;
            line-height: 1.25;
            vertical-align: middle;
        }}

        /* COLORES Y CLASES DE HOJA PORTADA */
        .excel-main-title {{
            background-color: #C0C0C0;
            font-size: 13.5px;
            font-weight: bold;
            text-align: left;
            padding: 6px 10px;
            color: #000000;
        }}
        .excel-date {{
            float: right;
            font-size: 12px;
            font-weight: bold;
        }}
        .col-lbl-empty {{
            width: 125px;
            border: 1px solid #B0B0B0;
            background-color: #FFFFFF;
        }}
        .cell-stream-name {{
            background-color: #C0C0C0;
            font-size: 12px;
            font-weight: bold;
            padding: 4px 8px;
            text-align: left;
        }}
        .cell-elem-name {{
            background-color: #FFFF99;
            font-weight: bold;
            text-align: center;
            font-size: 11px;
        }}
        .cell-turn {{
            font-weight: bold;
            text-align: center;
            background-color: #FFFFFF;
        }}
        .cell-cour-lab {{
            font-size: 10px;
            font-weight: bold;
            text-align: center;
            background-color: #FFFFFF;
            width: 80px;
        }}
        .cell-lbl-diff {{
            background-color: #CCFFFF;
            font-weight: bold;
            font-size: 9.5px;
            text-align: center;
        }}
        .cell-num {{
            text-align: right;
            font-family: Consolas, 'Lucida Console', monospace;
            font-size: 11px;
            padding-right: 6px;
        }}
        .cell-diff {{
            text-align: right;
            font-family: Consolas, monospace;
            font-size: 11px;
            padding-right: 6px;
        }}
        .cell-pct {{
            text-align: right;
            font-family: Consolas, monospace;
            font-size: 11px;
            padding-right: 6px;
        }}
        .text-red {{
            color: #FF0000;
            font-weight: bold;
        }}
        .sin-dato {{
            color: #7F7F7F;
            font-style: italic;
        }}
        .cell-rec-header {{
            background-color: #FFCC99;
            font-weight: bold;
            text-align: center;
        }}
        .cell-stdev-header {{
            background-color: #CCFFFF;
            font-weight: bold;
            font-size: 10.5px;
            text-align: center;
            padding: 4px;
        }}
        .cell-stdev-col {{
            background-color: #FFFF99;
            font-weight: bold;
            font-size: 10px;
            text-align: center;
        }}
        .cell-stdev-label {{
            font-weight: bold;
            font-size: 10px;
            text-align: center;
        }}
        .cell-stdev-val {{
            font-weight: bold;
        }}
        .cell-guardia-header {{
            background-color: #CCFFFF;
            font-weight: bold;
            text-align: center;
            padding: 4px;
        }}
        .cell-interm-th {{
            background-color: #CCFFFF;
            font-weight: bold;
            text-align: center;
            font-size: 10px;
        }}
        .cell-interm-stream {{
            font-weight: 500;
            font-size: 10.5px;
            text-align: left;
            padding-left: 6px;
        }}
        .cell-center {{
            text-align: center;
            font-weight: bold;
        }}
        .cell-empty {{
            background-color: #FFFFFF;
            border: 1px solid #B0B0B0;
        }}
        .table-spacer {{
            height: 10px;
        }}
        .section-divider {{
            height: 20px;
            background-color: #EAEAEA;
            border-top: 1px solid #C0C0C0;
            border-bottom: 1px solid #C0C0C0;
            margin: 15px -20px;
        }}

        /* GRID DE GRÁFICAS EN PESTAÑAS SEPARADAS */
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
            gap: 15px;
            margin-top: 10px;
        }}
        .chart-card {{
            border: 1px solid #C0C0C0;
            background: #FFFFFF;
            padding: 8px;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .chart-title {{
            font-size: 11px;
            font-weight: bold;
            color: #1F4E79;
            margin-bottom: 6px;
            text-align: center;
            border-bottom: 1px solid #EAEAEA;
            width: 100%;
            padding-bottom: 4px;
        }}
        .chart-card img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #F0F0F0;
        }}
        .tab-intro {{
            font-size: 12px;
            color: #404040;
            margin-bottom: 10px;
            padding-bottom: 6px;
            border-bottom: 1px solid #E0E0E0;
        }}
    </style>
</head>
<body>

    <!-- BARRA SUPERIOR -->
    <div class="excel-ribbon">
        <div class="ribbon-title">
            <span>📊 Courier_AUTO-C2.xlsm</span> &mdash; Control de Calidad Analítica (Planta C2 Toquepala)
        </div>
        <div class="ribbon-info">
            <span>Fecha Evaluada: <strong>{eval_date}</strong></span>
            <button class="btn-refresh" onclick="location.reload();">🔄 Actualizar (F5)</button>
        </div>
    </div>

    <!-- PESTAÑAS (TABS) TIPO EXCEL -->
    <div class="tab-bar">
        <button class="tab-btn active" onclick="switchTab('tab-portada', this)">📑 Portada</button>
        <button class="tab-btn" onclick="switchTab('tab-cu-mo', this)">📈 Gráf. Cu-Mo</button>
        <button class="tab-btn" onclick="switchTab('tab-fe-zn', this)">📊 Graf. Fe-Zn-Ox</button>
        <button class="tab-btn" onclick="switchTab('tab-graf1', this)">🎯 Graf1 (Dispersión 1:1)</button>
        <button class="tab-btn" onclick="switchTab('tab-graf2', this)">📉 Graf2 (Error Residual)</button>
        <button class="tab-btn" onclick="switchTab('tab-graf3', this)">🥧 Graf3 (Conformidad %)</button>
        <button class="tab-btn" onclick="switchTab('tab-distrn', this)">🔔 DistrN (Normal Gauss)</button>
    </div>

    <!-- CONTENIDO DE LAS PESTAÑAS -->
    <div class="tab-content-wrapper">

        <!-- PESTAÑA 1: PORTADA (HOJA PRINCIPAL IDÉNTICA) -->
        <div id="tab-portada" class="tab-pane active">
            {portada_html}
        </div>

        <!-- PESTAÑA 2: GRÁFICAS CU-MO -->
        <div id="tab-cu-mo" class="tab-pane">
            <div class="tab-intro">
                <strong>Hoja: Gráf. Cu-Mo</strong> &mdash; 12 Gráficas de evolución temporal de Cu y Mo (Courier vs Laboratorio) para Planta de Cobre y Planta de Molibdeno.
            </div>
            {_render_chart_grid(charts_cu_mo)}
        </div>

        <!-- PESTAÑA 3: GRAF. FE-ZN-OX -->
        <div id="tab-fe-zn" class="tab-pane">
            <div class="tab-intro">
                <strong>Hoja: Graf. Fe-Zn-Ox</strong> &mdash; 6 Gráficas de evolución temporal para Hierro (%Fe), Zinc (%Zn), Óxidos (%Ox) e Insoluble (%Ins).
            </div>
            {_render_chart_grid(charts_fe_zn_ox)}
        </div>

        <!-- PESTAÑA 4: GRAF1 (DISPERSIÓN 1:1) -->
        <div id="tab-graf1" class="tab-pane">
            <div class="tab-intro">
                <strong>Hojas: Graf1_Cu_Mo &amp; Graf1_Cu_Mo_M</strong> &mdash; Gráficas de ajuste 1:1 entre Courier y Laboratorio con bandas de tolerancia superior e inferior (&plusmn;11% Cabeza, &plusmn;20% Cola, &plusmn;6% Concentrado).
            </div>
            {_render_chart_grid(charts_graf1)}
        </div>

        <!-- PESTAÑA 5: GRAF2 (ERROR RESIDUAL) -->
        <div id="tab-graf2" class="tab-pane">
            <div class="tab-intro">
                <strong>Hojas: Graf2_Cu_Mo &amp; Graf2_Cu_Mo_M</strong> &mdash; Cartas de control de error residual (Diferencia = Laboratorio - Courier) a lo largo de los últimos 62 turnos.
            </div>
            {_render_chart_grid(charts_graf2)}
        </div>

        <!-- PESTAÑA 6: GRAF3 (CONFORMIDAD %) -->
        <div id="tab-graf3" class="tab-pane">
            <div class="tab-intro">
                <strong>Hojas: Graf3_Cu_Mo &amp; Graf3_Cu_Mo_M</strong> &mdash; Gráficos circulares de porcentaje de conformidad histórica (Aceptable dentro de tolerancia vs Fuera de rango).
            </div>
            {_render_chart_grid(charts_graf3)}
        </div>

        <!-- PESTAÑA 7: DISTRN (DISTRIBUCIÓN NORMAL) -->
        <div id="tab-distrn" class="tab-pane">
            <div class="tab-intro">
                <strong>Hojas: DistrN_Cu &amp; DistrN_Mo</strong> &mdash; Histogramas de frecuencias de error empírico superpuestos con la curva teórica de densidad de Gauss.
            </div>
            {_render_chart_grid(charts_distrn)}
        </div>

    </div>

    <!-- JAVASCRIPT NATIVO PARA CAMBIO DE PESTAÑAS -->
    <script>
        function switchTab(tabId, btn) {{
            // Desactivar todos los paneles
            var panes = document.querySelectorAll('.tab-pane');
            panes.forEach(function(p) {{
                p.classList.remove('active');
            }});

            // Desactivar todos los botones
            var btns = document.querySelectorAll('.tab-btn');
            btns.forEach(function(b) {{
                b.classList.remove('active');
            }});

            // Activar el seleccionado
            var targetPane = document.getElementById(tabId);
            if (targetPane) {{
                targetPane.classList.add('active');
            }}

            // Marcar botón activo
            if (btn) {{
                btn.classList.add('active');
            }}
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}
    </script>
</body>
</html>
"""
    return html_template
