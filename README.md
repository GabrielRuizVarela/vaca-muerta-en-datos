# Vaca Muerta en datos

Pipeline reproducible sobre los datos abiertos de la Secretaría de Energía de Argentina:
producción mensual por pozo no convencional (Capítulo IV) y datos de fractura (Adjunto IV).
Ingesta idempotente, modelo en DuckDB, controles de calidad publicados y un tablero estático
que se actualiza solo cada semana.

**Tablero:** `site/index.html` (publicado con GitHub Pages).

## Qué muestra

- Producción de petróleo de Vaca Muerta por operador desde 2015 (kbbl/d) y la participación de YPF.
- Curvas tipo de pozos shale oil por cohorte (año del primer petróleo), YPF contra el resto.
- Diseño de terminación (rama horizontal, etapas, arena por metro) contra productividad a 12 meses.
- Una tabla de calidad de datos: qué anomalías tiene el dato público y cuántas filas afectan.

Con los datos a septiembre de 2026: Vaca Muerta produce unos 698 kbbl/d de petróleo, YPF el 50%.
La rama horizontal mediana de YPF pasó de unos 1.500 m (cohorte 2017) a 3.200 m (cohorte 2025),
mientras el petróleo de 12 meses por metro de rama bajó de 116 a 77 bbl/m. Es una correlación,
no una causa.

## Arquitectura

```
datos.energia.gob.ar (CKAN, CSV)
   │  pipeline/ingest.py   GET condicional (ETag/Last-Modified), SHA-256, raw inmutable por versión
   ▼
data/raw/<dataset>/<fecha>_<hash>.csv  + data/manifest.json
   │  pipeline/build.py    ejecuta pipeline/sql/*.sql en orden sobre DuckDB (create or replace: idempotente)
   ▼
staging ─► fct_produccion (grano pozo, mes) · dim_pozo · dim_fractura_pozo ─► marts
   │  pipeline/checks.py   controles bloqueantes (fallan el build) y avisos (se cuentan y publican)
   ▼
data/dq_report.json ─► pipeline/report.py ─► site/index.html
```

GitHub Actions (`.github/workflows/refresh.yml`) corre tests, ingesta, build, controles y
publicación cada lunes, y versiona el manifiesto y el reporte de calidad.

## Correr local

```bash
uv sync
uv run pytest -q                    # 8 tests sobre fixtures chicos
uv run python -m pipeline.ingest    # descarga unos 150 MB la primera vez
uv run python -m pipeline.build     # warehouse + controles de calidad
uv run python -m pipeline.report    # site/index.html
```

## Decisiones

- **Raw inmutable y direccionado por hash.** Una corrida sin cambios no escribe nada; cada versión
  publicada por la Secretaría queda guardada y se puede reconstruir el resultado de cualquier semana.
- **Reconstrucción completa en vez de incremental.** Son 430.000 filas: DuckDB reconstruye todo en
  menos de un segundo, y así no hay estado incremental que se desincronice. Con más volumen, el paso
  natural es particionar por mes y cargar solo los meses rectificados.
- **Controles en dos niveles.** Lo que rompe el modelo (grano duplicado, volúmenes negativos después
  de limpiar, hechos sin dimensión) frena la publicación. Lo que es propio del dato público (TEF
  inconsistente, fechas futuras, pozos sin fractura informada) se mide y se muestra.
- **Normalización de operadores en un seed versionado** (`seeds/operadores.csv`): la misma empresa
  aparece con varias razones sociales (por ejemplo, tres variantes de Vista).
- **Caudales por día calendario**, 1 m³ = 6,2898 bbl.

## Límites

Datos públicos declarados por las operadoras; pueden rectificarse después. Las curvas tipo son
promedios simples por mes de producción (sin normalizar por rama ni filtrar pozos cerrados). Los
hallazgos son correlaciones. Proyecto personal, no afiliado ni avalado por ninguna empresa.

---

*English summary:* a reproducible data pipeline over Argentina's public well-level production and
frac data for Vaca Muerta: idempotent hash-addressed ingestion, a DuckDB model with a (well, month)
grain, two-tier data-quality checks published alongside results, and a weekly self-refreshing static
dashboard on GitHub Pages.
