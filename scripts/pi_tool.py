# -*- coding: utf-8 -*-
"""
pi_tool.py
================================================================================
Cliente de línea de comandos para el PI System desde WSL2, a través de la
pasarela PiGateway. Sustituye el flujo manual de PI DataLink en Excel y sirve
como capa de acceso para el proyecto de análisis de relaves.

SUBCOMANDOS
--------------------------------------------------------------------------------
  buscar    Busca tags por patrón. Consola: tag | descriptor | instrumenttag.
            CSV: los 52 atributos de PI Builder más columnas derivadas.

  extraer   Extracción masiva a CSV, eligiendo el método del AF SDK:
            recorded, interpolated, summary, plot, recorded_by_count.
            Trocea en bloques, guarda checkpoints y reanuda tras una caída.

  perfil    Historia realmente disponible por tag: primer evento, último
            evento y ventana común. Sirve para acotar el rango antes de
            extraer.

PRINCIPIOS
--------------------------------------------------------------------------------
  - NO rellena, NO imputa, NO descarta. Los huecos quedan como NaN explícitos
    y la calidad viaja en un archivo aparte. La limpieza es del pipeline.
  - Reconstrucción consciente del atributo `step`: los tags step se llevan a
    grilla con retención de orden cero, nunca con interpolación lineal.
  - Todo timestamp del transporte es UTC; se convierte a hora local al final.
  - Cada corrida deja un manifiesto JSON con el colectivo, el miembro, los
    parámetros y las estadísticas por tag.

EJEMPLOS
--------------------------------------------------------------------------------
  # Búsqueda con todos los atributos a CSV
  python3 pi_tool.py buscar "*294100*" --csv

  # Dato crudo de dos años, tags desde archivo, salida larga
  python3 pi_tool.py extraer --tags-file tags_espesadores.txt \\
      --metodo recorded --inicio "2024-07-14" --fin "2026-09-02"

  # Grilla de 1 minuto reconstruida desde eventos crudos, respetando step
  python3 pi_tool.py extraer --tags-file tags.txt --metodo recorded \\
      --inicio "2026-01-01" --fin "2026-03-01" --grilla 1min --formato ancho

  # Agregados de 12 h ponderados por tiempo
  python3 pi_tool.py extraer --patron "*TH001*LVL*" --metodo summary \\
      --inicio "2025-01-01" --fin "2026-09-01" --duracion 12h

  # Perfil de historia y ventana común
  python3 pi_tool.py perfil --tags-file tags.txt

Requisitos: pi_client.py en el mismo directorio, requests y pandas.
================================================================================
"""

from __future__ import annotations

import os
import sys
import json
import glob
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

try:
    from pi_client import PiGateway
except ImportError:
    print('ERROR: no se encuentra pi_client.py en este directorio.')
    sys.exit(1)


# =========================================================================== #
# Constantes
# =========================================================================== #
ATRIBUTOS_PI = [
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

METODOS_CON_RANGO = ('recorded', 'interpolated', 'summary', 'plot')
METODOS_TODOS = METODOS_CON_RANGO + ('recorded_by_count', 'current', 'end_of_stream')

# Chunk por defecto según método. El colectivo impone 60 s de OperationTimeOut,
# así que los bloques deben ser conservadores.
CHUNK_DEFECTO = {'recorded': 3, 'interpolated': 7, 'summary': 90, 'plot': 365}

# El troceado lo gobierna ExtractorPI, no el cliente: se le pasa una ventana
# mayor que cualquier rango real, pero dentro del límite de pandas.Timedelta.
SIN_TROCEO_CLIENTE = 3650


def log(msg: str) -> None:
    print('[{}] {}'.format(datetime.now().strftime('%H:%M:%S'), msg), flush=True)


def es_verdadero(v: Any) -> bool:
    return str(v).strip().lower() in ('1', 'true', 'on', 'yes')


# =========================================================================== #
# Resolución de la lista de tags
# =========================================================================== #
class ResolvedorTags:
    """Obtiene la lista de tags desde --tags, --tags-file o --patron."""

    def __init__(self, pi: PiGateway):
        self.pi = pi

    def resolver(self, args) -> List[str]:
        tags: List[str] = []

        if args.tags:
            tags += [t.strip() for t in args.tags.split(',') if t.strip()]

        if args.tags_file:
            tags += self._desde_archivo(args.tags_file)

        if args.patron:
            hallados = self.pi.search(args.patron)
            if hallados.empty:
                raise SystemExit('El patrón "{}" no encontró tags.'.format(args.patron))
            tags += hallados['tag'].tolist()
            log('Patrón "{}" resolvió {} tags.'.format(args.patron, len(hallados)))

        if not tags:
            raise SystemExit('Indique --tags, --tags-file o --patron.')

        return self._validar(tags)

    @staticmethod
    def _desde_archivo(ruta: str) -> List[str]:
        """
        Acepta: un tag por línea (# para comentarios), o CSV con columna 'tag'
        (o 'tag_pi' / 'Tag_Original', por compatibilidad con los CSV previos).
        """
        if not os.path.exists(ruta):
            raise SystemExit('No existe el archivo de tags: {}'.format(ruta))

        if ruta.lower().endswith(('.csv', '.tsv')):
            sep = '\t' if ruta.lower().endswith('.tsv') else ','
            df = pd.read_csv(ruta, sep=sep)
            for col in ('tag', 'tag_pi', 'Tag_Original', 'Tag_Encontrado'):
                if col in df.columns:
                    return df[col].dropna().astype(str).tolist()
            raise SystemExit(
                'El CSV no tiene columna de tags (tag / tag_pi / Tag_Original).')

        with open(ruta, 'r', encoding='utf-8') as f:
            return [l.strip() for l in f
                    if l.strip() and not l.strip().startswith('#')]

    @staticmethod
    def _validar(tags: List[str]) -> List[str]:
        """Aborta ante duplicados: previene el bug silencioso del dict."""
        vistos, dup, unicos = set(), set(), []
        for t in tags:
            if t in vistos:
                dup.add(t)
            else:
                vistos.add(t)
                unicos.append(t)
        if dup:
            raise SystemExit('Tags duplicados en la entrada: {}'.format(sorted(dup)))
        log('{} tags únicos validados.'.format(len(unicos)))
        return unicos


# =========================================================================== #
# Búsqueda de tags
# =========================================================================== #
class BuscadorTags:
    def __init__(self, pi: PiGateway, dir_salida: str):
        self.pi = pi
        self.dir_salida = dir_salida

    def ejecutar(self, patron: str, limite: int = 0,
                 lote: int = 50, exportar: bool = True) -> pd.DataFrame:
        log('Buscando "{}"...'.format(patron))
        hallados = self.pi.search(patron)
        if hallados.empty:
            print('Sin coincidencias.')
            return pd.DataFrame()

        tags = hallados['tag'].tolist()
        log('{} tags encontrados.'.format(len(tags)))
        if limite and len(tags) > limite:
            log('Limitando el detalle a {} tags (--max).'.format(limite))
            tags = tags[:limite]

        partes = []
        for i in range(0, len(tags), lote):
            sub = tags[i:i + lote]
            log('  atributos {}-{}'.format(i + 1, i + len(sub)))
            partes.append(self.pi.attributes(sub, ATRIBUTOS_PI))
        df = self.interpretar(pd.concat(partes, ignore_index=True))

        self._consola(df)

        if exportar:
            limpio = patron.replace('*', 'X').replace('?', 'Y').replace('/', '_')
            ruta = os.path.join(
                self.dir_salida,
                'tags_{}_{}.csv'.format(limpio, datetime.now().strftime('%Y%m%d_%H%M')))
            os.makedirs(self.dir_salida, exist_ok=True)
            df.to_csv(ruta, index=False, encoding='utf-8-sig')
            print('\n[OK] {} tags x {} columnas -> {}'.format(
                len(df), len(df.columns), ruta))
        return df

    @staticmethod
    def _consola(df: pd.DataFrame) -> None:
        cols = [c for c in ('tag', 'descriptor', 'instrumenttag') if c in df.columns]
        print('\n' + '=' * 120)
        print(' COINCIDENCIAS ({})'.format(len(df)))
        print('=' * 120)
        with pd.option_context('display.width', 250, 'display.max_colwidth', 70,
                               'display.max_rows', None):
            print(df[cols].fillna('').to_string(index=False))
        print('=' * 120)

    @staticmethod
    def interpretar(df: pd.DataFrame) -> pd.DataFrame:
        """Traduce la metadata a decisiones de pipeline."""
        if df.empty:
            return df

        if 'step' in df.columns:
            df['reconstruccion'] = df['step'].apply(
                lambda v: 'ZOH' if es_verdadero(v) else 'lineal')
        if 'archiving' in df.columns:
            df['historiza'] = df['archiving'].apply(es_verdadero)
        if 'compressing' in df.columns:
            df['comprimido'] = df['compressing'].apply(es_verdadero)

        # Banda muerta de compresión, en unidades de ingeniería y en % del span.
        # Ambas hacen falta: 25 m3/h sobre un span de 5000 es solo 0.5%, pero
        # borra toda la dinámica fina de un flujo de alimentación.
        def _pct(r):
            try:
                span, comp = float(r['span']), float(r['compdev'])
                return round(100.0 * comp / span, 4) if span else None
            except (TypeError, ValueError, KeyError):
                return None

        if 'compdev' in df.columns:
            df['compdev_eu'] = pd.to_numeric(df['compdev'], errors='coerce')
            if 'span' in df.columns:
                df['compdev_pct_span'] = df.apply(_pct, axis=1)
        return df


# =========================================================================== #
# Extracción masiva
# =========================================================================== #
class ExtractorPI:
    """
    Extracción por bloques con checkpoint en disco y reanudación.

    Un bloque que agota el tiempo del servidor se parte a la mitad y se
    reintenta, hasta un mínimo de una hora. Así una ventana densa no obliga a
    bajar el troceado de toda la corrida.
    """

    MIN_BLOQUE_H = 1

    def __init__(self, pi: PiGateway, dir_salida: str, etiqueta: str,
                 reanudar: bool = True):
        self.pi = pi
        self.dir_salida = dir_salida
        self.etiqueta = etiqueta
        self.dir_chunks = os.path.join(dir_salida, '_chunks_' + etiqueta)
        self.reanudar = reanudar
        os.makedirs(self.dir_chunks, exist_ok=True)

    # ---------------- bloques ----------------
    @staticmethod
    def bloques(inicio: str, fin: str, dias: float) -> List[Tuple[str, str]]:
        t0, tf = pd.Timestamp(inicio), pd.Timestamp(fin)
        if t0 >= tf:
            raise SystemExit('El inicio debe ser anterior al fin.')
        out = []
        while t0 < tf:
            t1 = min(t0 + pd.Timedelta(days=dias), tf)
            out.append((t0.strftime('%Y-%m-%d %H:%M:%S'),
                        t1.strftime('%Y-%m-%d %H:%M:%S')))
            t0 = t1
        return out

    @staticmethod
    def _nombre_chunk(t0: str) -> str:
        return 'chunk_' + t0.replace(' ', '_').replace(':', '').replace('-', '') + '.csv.gz'

    # ---------------- llamada por bloque ----------------
    def _llamar(self, tags: Sequence[str], metodo: str, t0: str, t1: str,
                args) -> pd.DataFrame:
        if metodo == 'recorded':
            return self.pi.recorded(tags, t0, t1, boundary=args.boundary,
                                    filtro=args.filtro or '', chunk_dias=SIN_TROCEO_CLIENTE)
        if metodo == 'interpolated':
            return self.pi.interpolated(tags, t0, t1, intervalo=args.intervalo,
                                        chunk_dias=SIN_TROCEO_CLIENTE)
        if metodo == 'plot':
            return self.pi.plot(tags, t0, t1, intervalos=args.intervalos)
        if metodo == 'summary':
            tipos = [x.strip() for x in args.tipos.split(',') if x.strip()]
            return self.pi.summary(tags, t0, t1, duracion=args.duracion,
                                   tipos=tipos, basis=args.basis,
                                   chunk_dias=SIN_TROCEO_CLIENTE)
        raise SystemExit('Método no soportado en modo bloque: {}'.format(metodo))

    def _con_reintento(self, tags, metodo, t0, t1, args) -> pd.DataFrame:
        """Ante fallo, parte el bloque a la mitad y reintenta."""
        try:
            return self._llamar(tags, metodo, t0, t1, args)
        except Exception as e:
            dur_h = (pd.Timestamp(t1) - pd.Timestamp(t0)).total_seconds() / 3600.0
            if dur_h <= self.MIN_BLOQUE_H:
                log('  bloque mínimo alcanzado y sigue fallando: {}'.format(e))
                raise
            medio = (pd.Timestamp(t0) + (pd.Timestamp(t1) - pd.Timestamp(t0)) / 2)
            medio_s = medio.strftime('%Y-%m-%d %H:%M:%S')
            log('  fallo ({}). Partiendo el bloque en dos.'.format(
                str(e)[:120]))
            a = self._con_reintento(tags, metodo, t0, medio_s, args)
            b = self._con_reintento(tags, metodo, medio_s, t1, args)
            return pd.concat([a, b], ignore_index=True)

    # ---------------- extracción completa ----------------
    def extraer(self, tags: Sequence[str], metodo: str, args) -> pd.DataFrame:
        # Métodos sin rango temporal: una sola llamada.
        if metodo in ('current', 'end_of_stream', 'recorded_by_count'):
            if metodo == 'current':
                df = self.pi.current(tags)
            elif metodo == 'end_of_stream':
                df = self.pi.end_of_stream(tags)
            else:
                df = self.pi.recorded_by_count(tags, desde=args.inicio or '*',
                                               count=args.count,
                                               forward=not args.hacia_atras)
            return df

        chunk = args.chunk_dias or CHUNK_DEFECTO.get(metodo, 7)
        bloques = self.bloques(args.inicio, args.fin, chunk)
        log('{} bloques de {} día(s) | método: {}'.format(
            len(bloques), chunk, metodo))

        rutas = []
        for i, (t0, t1) in enumerate(bloques, 1):
            ruta = os.path.join(self.dir_chunks, self._nombre_chunk(t0))
            if self.reanudar and os.path.exists(ruta):
                log('[{}/{}] {} -> ya existe, se omite'.format(i, len(bloques), t0))
                rutas.append(ruta)
                continue

            log('[{}/{}] {} -> {}'.format(i, len(bloques), t0, t1))
            df = self._con_reintento(tags, metodo, t0, t1, args)
            df.to_csv(ruta, index=False, compression='gzip')
            log('    {} filas'.format(len(df)))
            rutas.append(ruta)

        if not rutas:
            return pd.DataFrame()

        log('Consolidando {} bloques...'.format(len(rutas)))
        partes = [pd.read_csv(r, compression='gzip') for r in rutas]
        df = pd.concat(partes, ignore_index=True)

        if 't' in df.columns:
            df['t'] = pd.to_datetime(df['t'], errors='coerce', format='ISO8601')
            claves = ['tag', 't'] + (['summary'] if 'summary' in df.columns else [])
            df = (df.drop_duplicates(subset=claves)
                    .sort_values(claves)
                    .reset_index(drop=True))
        return df


# =========================================================================== #
# Reconstrucción a grilla regular
# =========================================================================== #
class ReconstructorGrilla:
    """
    Lleva eventos crudos a una grilla regular respetando el atributo `step`.

    Los tags step (válvulas, estados, consignas) se reconstruyen con retención
    de orden cero. Interpolar linealmente una consigna fabrica valores
    intermedios que el proceso nunca tuvo.

    Un hueco mayor que `compmax` no es compresión: es pérdida de dato, y se
    marca como NaN en lugar de rellenarse.
    """

    def __init__(self, atributos: pd.DataFrame):
        self.attr = atributos.set_index('tag') if not atributos.empty else pd.DataFrame()

    def _es_step(self, tag: str) -> bool:
        if self.attr.empty or tag not in self.attr.index:
            return False
        return es_verdadero(self.attr.loc[tag].get('step'))

    def _compmax_s(self, tag: str) -> Optional[float]:
        if self.attr.empty or tag not in self.attr.index:
            return None
        try:
            v = float(self.attr.loc[tag].get('compmax'))
            return v if v > 0 else None
        except (TypeError, ValueError):
            return None

    def reconstruir(self, df_largo: pd.DataFrame, freq: str,
                    inicio: str, fin: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Devuelve (valores, calidad) en formato ancho, con NaN explícitos."""
        if df_largo.empty:
            return pd.DataFrame(), pd.DataFrame()

        tz = df_largo['t'].dt.tz
        grilla = pd.date_range(pd.Timestamp(inicio, tz=tz),
                               pd.Timestamp(fin, tz=tz), freq=freq, inclusive='left')

        valores, calidad = {}, {}
        for tag, g in df_largo.groupby('tag'):
            s = (g.set_index('t')['value'].sort_index())
            s = s[~s.index.duplicated(keep='last')]
            bueno = (g.set_index('t')['good'].sort_index())
            bueno = bueno[~bueno.index.duplicated(keep='last')]

            if self._es_step(tag):
                v = s.reindex(s.index.union(grilla)).ffill().reindex(grilla)
            else:
                v = (s.reindex(s.index.union(grilla))
                       .interpolate(method='time', limit_area='inside')
                       .reindex(grilla))

            # Edad del último evento real en cada punto de la grilla.
            ult = (pd.Series(s.index, index=s.index)
                     .reindex(s.index.union(grilla)).ffill().reindex(grilla))
            edad_s = (pd.Series(grilla, index=grilla)
                      - pd.to_datetime(ult)).dt.total_seconds()

            cmax = self._compmax_s(tag)
            if cmax:
                # Hueco mayor que compmax: el historiador debió grabar y no lo
                # hizo. Es pérdida de dato, no compresión.
                v = v.where(edad_s <= cmax * 1.5)

            valores[tag] = v
            calidad[tag] = edad_s

        dfv = pd.DataFrame(valores, index=grilla)
        dfc = pd.DataFrame(calidad, index=grilla)
        dfv.index.name = dfc.index.name = 't'
        return dfv, dfc


# =========================================================================== #
# Manifiesto de auditoría
# =========================================================================== #
def construir_manifiesto(df: pd.DataFrame, tags: Sequence[str],
                         metodo: str, args, health: Dict[str, Any]) -> Dict[str, Any]:
    m: Dict[str, Any] = {
        'generado': datetime.now().isoformat(timespec='seconds'),
        'servidor': health.get('server'),
        'colectivo': health.get('collective'),
        'miembro': health.get('host'),
        'rol_miembro': health.get('memberType'),
        'sdk': health.get('sdk'),
        'metodo': metodo,
        'parametros': {k: v for k, v in vars(args).items()
                       if k not in ('func',) and v is not None},
        'n_tags_solicitados': len(tags),
        'n_filas': int(len(df)),
    }

    por_tag = {}
    if not df.empty and 'tag' in df.columns:
        for tag, g in df.groupby('tag'):
            e = {'eventos': int(len(g))}
            if 'good' in g.columns:
                buenos = int(g['good'].fillna(False).astype(bool).sum())
                e['buenos'] = buenos
                e['pct_bueno'] = round(100.0 * buenos / len(g), 2) if len(g) else 0.0
            if 't' in g.columns:
                e['primer_ts'] = str(g['t'].min())
                e['ultimo_ts'] = str(g['t'].max())
            por_tag[tag] = e

    faltantes = [t for t in tags if t not in por_tag]
    m['tags_sin_dato'] = faltantes
    m['por_tag'] = por_tag
    return m


# =========================================================================== #
# Subcomandos
# =========================================================================== #
def cmd_buscar(args, pi: PiGateway) -> None:
    BuscadorTags(pi, args.dir_salida).ejecutar(
        args.patron_pos, limite=args.max, lote=args.lote, exportar=not args.sin_csv)


def cmd_perfil(args, pi: PiGateway) -> None:
    tags = ResolvedorTags(pi).resolver(args)
    df = pi.perfil_historia(tags)
    if df.empty:
        print('Sin resultados.')
        return

    cols = [c for c in ('tag', 'inicio_util', 'ultimo_ts', 'dias_historia',
                        'rezago_h', 'step', 'archiving', 'estado') if c in df.columns]
    print('\n' + '=' * 130)
    print(' PERFIL DE HISTORIA ({} tags)'.format(len(df)))
    print('=' * 130)
    with pd.option_context('display.width', 250, 'display.max_rows', None):
        print(df[cols].fillna('').to_string(index=False))
    print('=' * 130)

    v = pi.ventana_comun(tags)
    if v.get('inicio') is not None:
        print('\n VENTANA COMÚN')
        print('  inicio: {}  (lo impone {})'.format(v['inicio'], v['limita_inicio']))
        print('  fin   : {}  (lo impone {})'.format(v['fin'], v['limita_fin']))
        print('  ancho : {} días'.format(v['dias']))

    os.makedirs(args.dir_salida, exist_ok=True)
    ruta = os.path.join(args.dir_salida, 'perfil_{}.csv'.format(
        datetime.now().strftime('%Y%m%d_%H%M')))
    df.to_csv(ruta, index=False, encoding='utf-8-sig')
    print('\n[OK] {}'.format(ruta))


def cmd_extraer(args, pi: PiGateway) -> None:
    tags = ResolvedorTags(pi).resolver(args)
    health = pi.health()

    if args.metodo in METODOS_CON_RANGO and not (args.inicio and args.fin):
        raise SystemExit('El método {} requiere --inicio y --fin.'.format(args.metodo))

    etiqueta = args.etiqueta or args.metodo
    extractor = ExtractorPI(pi, args.dir_salida, etiqueta, reanudar=not args.sin_reanudar)

    t_ini = datetime.now()
    df = extractor.extraer(tags, args.metodo, args)
    log('Extracción terminada: {} filas en {}.'.format(
        len(df), str(datetime.now() - t_ini).split('.')[0]))

    os.makedirs(args.dir_salida, exist_ok=True)
    sello = datetime.now().strftime('%Y%m%d_%H%M')
    base = os.path.join(args.dir_salida, '{}_{}_{}'.format(
        args.prefijo, etiqueta, sello))

    # --- Reconstrucción a grilla (solo desde eventos crudos) ---------------
    if args.grilla:
        if args.metodo != 'recorded':
            raise SystemExit('--grilla solo aplica al método recorded.')
        log('Reconstruyendo grilla {} (ZOH para tags step)...'.format(args.grilla))
        attrs = pi.attributes(tags, ['step', 'compmax', 'pointtype', 'engunits'])
        dfv, dfc = ReconstructorGrilla(attrs).reconstruir(
            df, args.grilla, args.inicio, args.fin)
        dfv.to_csv(base + '_valores.csv', encoding='utf-8-sig')
        dfc.to_csv(base + '_edad_evento_s.csv', encoding='utf-8-sig')
        print('\n[OK] grilla   -> {}_valores.csv  ({} x {})'.format(
            base, len(dfv), len(dfv.columns)))
        print('[OK] calidad  -> {}_edad_evento_s.csv'.format(base))
        print('     (edad en segundos del último evento real; NaN = sin dato)')

    # --- Salida principal ---------------------------------------------------
    if args.formato == 'ancho' and not args.grilla and 'value' in df.columns:
        ancho = pi.to_wide(df)
        calidad = pi.mascara_calidad(df)
        ancho.to_csv(base + '_valores.csv', encoding='utf-8-sig')
        calidad.to_csv(base + '_calidad.csv', encoding='utf-8-sig')
        print('\n[OK] valores -> {}_valores.csv  ({} x {})'.format(
            base, len(ancho), len(ancho.columns)))
        print('[OK] calidad -> {}_calidad.csv'.format(base))
    else:
        df.to_csv(base + '.csv', index=False, encoding='utf-8-sig')
        print('\n[OK] datos   -> {}.csv  ({} filas)'.format(base, len(df)))

    # --- Manifiesto ---------------------------------------------------------
    man = construir_manifiesto(df, tags, args.metodo, args, health)
    with open(base + '_manifiesto.json', 'w', encoding='utf-8') as f:
        json.dump(man, f, indent=2, ensure_ascii=False)
    print('[OK] manifiesto -> {}_manifiesto.json'.format(base))

    if man['tags_sin_dato']:
        print('\n AVISO: {} tag(s) sin dato en el rango:'.format(
            len(man['tags_sin_dato'])))
        for t in man['tags_sin_dato'][:20]:
            print('  - ' + t)
        if len(man['tags_sin_dato']) > 20:
            print('  ... y {} más (ver manifiesto)'.format(
                len(man['tags_sin_dato']) - 20))


# =========================================================================== #
# CLI
# =========================================================================== #
def construir_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog='pi_tool.py',
        description='Cliente PI System vía la pasarela PiGateway (WSL2 -> Windows).',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--host', default=None, help='Host de la pasarela (autodetecta)')
    ap.add_argument('--puerto', type=int, default=5000)
    ap.add_argument('--dir-salida', default='./salida_pi')
    ap.add_argument('--zona', default='America/Lima', help='Zona horaria de salida')

    sub = ap.add_subparsers(dest='comando', required=True)

    # ---- buscar ----
    b = sub.add_parser('buscar', help='Busca tags y exporta sus atributos.')
    b.add_argument('patron_pos', metavar='PATRON', help='Ej. *294100*')
    b.add_argument('--max', type=int, default=0, help='Límite de tags a detallar')
    b.add_argument('--lote', type=int, default=50)
    b.add_argument('--sin-csv', action='store_true')
    b.set_defaults(func=cmd_buscar)

    # ---- argumentos de selección de tags, compartidos ----
    def add_tags(p):
        p.add_argument('--tags', help='Lista separada por comas')
        p.add_argument('--tags-file', help='Archivo .txt (uno por línea) o .csv')
        p.add_argument('--patron', help='Patrón de búsqueda, ej. *TH001*')

    # ---- extraer ----
    e = sub.add_parser('extraer', help='Extracción masiva a CSV.')
    add_tags(e)
    e.add_argument('--metodo', choices=METODOS_TODOS, default='recorded')
    e.add_argument('--inicio', help='Ej. "2024-07-14" o "*-30d"')
    e.add_argument('--fin', help='Ej. "2026-09-02" o "*"')
    e.add_argument('--chunk-dias', type=float, default=None,
                   help='Días por bloque (por defecto según método)')
    e.add_argument('--formato', choices=('largo', 'ancho'), default='largo')
    e.add_argument('--grilla', default=None,
                   help='Reconstruye a grilla regular (ej. 1min). Solo con recorded.')
    e.add_argument('--prefijo', default='pi')
    e.add_argument('--etiqueta', default=None, help='Nombre del set de chunks')
    e.add_argument('--sin-reanudar', action='store_true')
    # específicos por método
    e.add_argument('--intervalo', default='1m', help='interpolated: paso de la grilla')
    e.add_argument('--boundary', default='Inside',
                   choices=('Inside', 'Outside', 'Interpolated'))
    e.add_argument('--filtro', default=None, help='Expresión de filtro PI')
    e.add_argument('--intervalos', type=int, default=640, help='plot: nº de intervalos')
    e.add_argument('--duracion', default='12h', help='summary: ancho del bloque')
    e.add_argument('--tipos', default='Average,Minimum,Maximum,StdDev,Count,PercentGood')
    e.add_argument('--basis', default='TimeWeighted',
                   choices=('TimeWeighted', 'EventWeighted'))
    e.add_argument('--count', type=int, default=1, help='recorded_by_count: nº eventos')
    e.add_argument('--hacia-atras', action='store_true')
    e.set_defaults(func=cmd_extraer)

    # ---- perfil ----
    p = sub.add_parser('perfil', help='Historia disponible y ventana común.')
    add_tags(p)
    p.set_defaults(func=cmd_perfil)

    return ap


def main() -> None:
    args = construir_parser().parse_args()

    pi = PiGateway(host=args.host, puerto=args.puerto, zona_local=args.zona)
    try:
        h = pi.health()
    except Exception as e:
        print('No hay respuesta de la pasarela en {}.\n{}'.format(pi.base, e))
        sys.exit(1)

    print('Pasarela: {} | PI: {} | colectivo: {} ({})'.format(
        pi.base, h.get('server'), h.get('collective'), h.get('memberType')))

    args.func(args, pi)


if __name__ == '__main__':
    main()
