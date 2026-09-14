# -*- coding: utf-8 -*-
"""
buscar_tags.py
================================================================================
Prueba de extremo a extremo de la pasarela PiGateway desde WSL2.

Busca tags por patrón y devuelve TODOS sus atributos, encadenando dos llamadas:

    /search      -> resuelve el patrón a una lista de tags
    /attributes  -> trae los 52 atributos de PI Builder para cada uno

Equivale a searchTAg.py, pero sin AF SDK ni pythonnet del lado Linux.

Uso:
    python3 buscar_tags.py "*294100*"
    python3 buscar_tags.py "*294100*LIT*" --csv
    python3 buscar_tags.py "*TH001*" --max 20
    python3 buscar_tags.py                 # pregunta el patrón

Requisitos: pi_client.py en el mismo directorio, más requests y pandas.
================================================================================
"""

import sys
import argparse
from datetime import datetime

import pandas as pd

try:
    from pi_client import PiGateway
except ImportError:
    print('ERROR: no se encuentra pi_client.py. Debe estar en este directorio.')
    sys.exit(1)


# Los 52 atributos de PI Builder, en el mismo orden que searchTAg.py.
ATRIBUTOS = [
    # General
    'descriptor', 'instrumenttag', 'digitalset', 'displaydigits', 'engunits',
    'exdesc', 'future', 'pointsource', 'pointtype', 'ptclassname', 'sourcetag',
    # Archive
    'archiving', 'compressing', 'compdev', 'compmax', 'compmin', 'compdevpercent',
    'excdev', 'excmax', 'excmin', 'excdevpercent', 'scan', 'shutdown',
    'span', 'step', 'typicalvalue', 'zero',
    # Security
    'datasecurity', 'ptsecurity',
    # Classic
    'convers', 'filtercode', 'location1', 'location2', 'location3', 'location4',
    'location5', 'squareroot', 'srcptid', 'totalcode', 'userint1', 'userint2',
    'userreal1', 'userreal2',
    # System
    'changedate', 'changer', 'creationdate', 'creator', 'pointid',
]


def _es_verdadero(v):
    """PI devuelve los booleanos como '1'/'0' o 'True'/'False' según el atributo."""
    return str(v).strip().lower() in ('1', 'true', 'on', 'yes')


def interpretar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Columnas derivadas que traducen la metadata a decisiones de pipeline.

    `reconstruccion` es la más importante: un tag step NO se interpola
    linealmente. Consignas, estados y posiciones discretas se reconstruyen con
    retención de orden cero, porque interpolar crea valores intermedios que el
    proceso nunca tuvo.
    """
    if df.empty:
        return df

    if 'step' in df.columns:
        df['reconstruccion'] = df['step'].apply(
            lambda v: 'ZOH (retención)' if _es_verdadero(v) else 'lineal')

    if 'archiving' in df.columns:
        df['historiza'] = df['archiving'].apply(_es_verdadero)

    if 'compressing' in df.columns:
        df['comprimido'] = df['compressing'].apply(_es_verdadero)

    # Banda muerta de compresión en % del span: cuánta dinámica se perdió.
    if 'compdev' in df.columns and 'span' in df.columns:
        def _pct(r):
            try:
                span = float(r['span'])
                comp = float(r['compdev'])
                return round(100.0 * comp / span, 3) if span else None
            except (TypeError, ValueError):
                return None
        df['compdev_pct_span'] = df.apply(_pct, axis=1)

    return df


def main():
    ap = argparse.ArgumentParser(description='Busca tags PI y trae sus atributos.')
    ap.add_argument('patron', nargs='?', help='Patrón de búsqueda, ej. *294100*')
    ap.add_argument('--host', default=None, help='Host de la pasarela (por defecto, autodetecta)')
    ap.add_argument('--puerto', type=int, default=5000)
    ap.add_argument('--max', type=int, default=0, help='Límite de tags a detallar (0 = sin límite)')
    ap.add_argument('--csv', action='store_true', help='Exportar el resultado a CSV')
    ap.add_argument('--lote', type=int, default=50, help='Tags por llamada a /attributes')
    args = ap.parse_args()

    patron = args.patron or input('Patrón del tag a buscar (ej. *294100*): ').strip()
    if not patron:
        print('Patrón vacío. Nada que hacer.')
        return

    pi = PiGateway(host=args.host, puerto=args.puerto)

    # ---------------- 1. Conectividad ----------------
    print('Pasarela: {}'.format(pi.base))
    try:
        h = pi.health()
    except Exception as e:
        print('\nNo hay respuesta de la pasarela: {}'.format(e))
        print('Verifique que gw4Pi.exe esté corriendo y que este host la alcance:')
        print('  curl -s {}/health'.format(pi.base))
        return

    print('PI Server: {} | colectivo: {} ({}) | SDK {}'.format(
        h.get('server'), h.get('collective'), h.get('memberType'), h.get('sdk')))
    print('Timeout de operación: {} s'.format(h.get('operationTimeoutS')))

    # ---------------- 2. Búsqueda ----------------
    print('\nBuscando "{}"...'.format(patron))
    hallados = pi.search(patron)
    if hallados.empty:
        print('Sin coincidencias.')
        return

    print('{} tags encontrados.'.format(len(hallados)))
    cols = [c for c in ('tag', 'descriptor', 'engunits', 'pointtype')
            if c in hallados.columns]
    print('\n' + '=' * 100)
    print(hallados[cols].to_string(index=False))
    print('=' * 100)

    tags = hallados['tag'].tolist()
    if args.max and len(tags) > args.max:
        print('\nLimitando el detalle a los primeros {} tags (--max).'.format(args.max))
        tags = tags[:args.max]

    # ---------------- 3. Atributos completos ----------------
    print('\nExtrayendo {} atributos de {} tags...'.format(len(ATRIBUTOS), len(tags)))
    partes = []
    for i in range(0, len(tags), args.lote):
        lote = tags[i:i + args.lote]
        print('  lote {}-{}'.format(i + 1, i + len(lote)))
        partes.append(pi.attributes(lote, ATRIBUTOS))
    df = pd.concat(partes, ignore_index=True)
    df = interpretar(df)

    # ---------------- 4. Resumen ----------------
    resumen = [c for c in ('tag', 'descriptor', 'engunits', 'pointtype',
                           'step', 'reconstruccion', 'historiza', 'comprimido',
                           'compdev', 'compdev_pct_span', 'compmax',
                           'scan', 'creationdate')
               if c in df.columns]
    print('\n' + '=' * 130)
    print(' METADATA RELEVANTE PARA RECONSTRUCCIÓN')
    print('=' * 130)
    with pd.option_context('display.width', 200, 'display.max_columns', None):
        print(df[resumen].to_string(index=False))
    print('=' * 130)

    # Avisos: lo que cambiaría una decisión del pipeline.
    avisos = []
    if 'historiza' in df.columns:
        for t in df.loc[~df['historiza'].fillna(True), 'tag']:
            avisos.append('{}: archiving = 0, NO historiza.'.format(t))
    if 'reconstruccion' in df.columns:
        zoh = df.loc[df['reconstruccion'] == 'ZOH (retención)', 'tag'].tolist()
        if zoh:
            avisos.append('Tags step (no interpolar linealmente): {}'.format(', '.join(zoh)))
    if 'compdev_pct_span' in df.columns:
        for _, r in df.iterrows():
            v = r.get('compdev_pct_span')
            if v is not None and v == v and v > 2:
                avisos.append(
                    '{}: compdev = {}% del span, compresión agresiva; la varianza '
                    'medida subestima la real.'.format(r['tag'], v))

    print('\n AVISOS')
    print('-' * 130)
    if avisos:
        for a in avisos:
            print('  - ' + a)
    else:
        print('  Ninguno.')

    # ---------------- 5. Exportación ----------------
    if args.csv:
        limpio = patron.replace('*', 'X').replace('?', 'Y').replace('/', '_')
        nombre = 'Busqueda_{}_{}.csv'.format(
            limpio, datetime.now().strftime('%Y%m%d_%H%M'))
        df.to_csv(nombre, index=False, encoding='utf-8-sig')
        print('\n[OK] {} tags x {} columnas exportados en: {}'.format(
            len(df), len(df.columns), nombre))

    return df


if __name__ == '__main__':
    main()
