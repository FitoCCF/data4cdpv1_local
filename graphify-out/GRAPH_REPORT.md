# Graph Report - .  (2026-07-21)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 47 nodes · 57 edges · 13 communities (12 shown, 1 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d80b5b06`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- collect_rows
- api2db.py
- main
- generar_calendario.py
- taskpx.py

## God Nodes (most connected - your core abstractions)
1. `collect_rows()` - 8 edges
2. `clean_string()` - 6 edges
3. `main()` - 6 edges
4. `fetch_entries()` - 5 edges
5. `build_row()` - 4 edges
6. `insert_rows()` - 4 edges
7. `load_samples_config()` - 4 edges
8. `load_existing_keys()` - 4 edges
9. `load_db_settings()` - 4 edges
10. `parse_date()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `Session`  [EXTRACTED]
  scripts/api2db.py →   _Bridges community 0 → community 2_

## Import Cycles
- None detected.

## Communities (13 total, 1 thin omitted)

### Community 0 - "collect_rows"
Cohesion: 0.29
Nodes (10): Any, build_row(), collect_rows(), fetch_entries(), load_samples_config(), Retrieve all payload entries for the provided tag from the given IP., Convert an API entry into a row ready to be inserted., Fetch sample configuration (id, tag, equipment_id) from works4cdp_sample. (+2 more)

### Community 1 - "api2db.py"
Cohesion: 0.33
Nodes (8): clean_string(), parse_date(), parse_float(), parse_int(), parse_time(), Normalise sentinel values ('N/A', '', None) to None., Return yyyy-mm-dd for a value like '17.09.2025'., Return HH:MM:SS from API hour strings.

### Community 2 - "main"
Cohesion: 0.29
Nodes (7): insert_rows(), load_db_settings(), load_existing_keys(), main(), Insert rows into works4cdp_assay using psycopg2's execute_batch., Fetch existing (sample_id, date, time, instance) tuples from works4cdp_assay., Read database connection settings from environment variables.

### Community 3 - "generar_calendario.py"
Cohesion: 0.40
Nodes (4): calcular_semana_extendida(), generar_registros_calendar(), Toma un rango de fechas y una lista de grupos, y genera una lista de filas (tupl, Calcula un número de semana continuo desde el año 1963.     Esto evita que el co

## Knowledge Gaps
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `collect_rows()` connect `collect_rows` to `api2db.py`, `main`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `fetch_entries()` connect `collect_rows` to `api2db.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._