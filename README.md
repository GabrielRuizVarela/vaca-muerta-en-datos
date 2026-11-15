# Vaca Muerta en datos

Pipeline reproducible sobre los datos abiertos de la Secretaría de Energía de Argentina:
producción mensual por pozo no convencional (Capítulo IV) y datos de fractura (Adjunto IV).
Ingesta idempotente, modelo en DuckDB, controles de calidad publicados y un tablero estático
que se regenera con cada actualización semanal.

**Tablero:** `site/index.html` (estático, se abre directo en el navegador).

## Qué muestra

- Producción de petróleo de Vaca Muerta por operador desde 2015 (kbbl/d) y la participación de YPF.
- Curvas tipo de pozos shale oil por cohorte (año del primer petróleo), YPF contra el resto.
- Diseño de terminación (rama horizontal, etapas, arena por metro) contra productividad a 12 meses.
- **Interferencia entre pozos:** cuando se fractura un pozo nuevo, cuánto caen los pozos vecinos que ya producían,
  contra pozos de control de la misma edad.
- Una tabla de calidad de datos: qué anomalías tiene el dato público y cuántas filas afectan.

Además:

- **Preguntas en lenguaje natural** (`agente/`) con un modelo local, sobre 11 operaciones tipadas de solo
  lectura, expuestas también como servidor MCP. El modelo elige la operación y sus argumentos; nunca escribe SQL
  ni números. Cada respuesta cita tablas, mes de datos y hash del archivo crudo.
- **Evaluación de exactitud** (`agente/eval/`): preguntas de desarrollo y reservadas, con la respuesta correcta
  calculada sobre el warehouse vigente (no guardada), así la evaluación sigue valiendo después de cada actualización.
- **Wiki y grafo generados** (`wiki/`): una página por operadora, área y pad con interferencia, y una página de
  hallazgo que acumula un historial por versión de datos. `wiki/grafo.json` une operadora, área, pad y pozo, con
  aristas `interfiere` (pozo hijo a pozo padre, con distancia y barriles diferidos).

Con los datos a septiembre de 2026: Vaca Muerta produce unos 698 kbbl/d de petróleo, YPF el 50%.
La rama horizontal mediana de YPF pasó de unos 1.500 m (cohorte 2017) a 3.200 m (cohorte 2025),
mientras el petróleo de 12 meses por metro de rama bajó de 116 a 77 bbl/m. Es una correlación,
no una causa.

**Interferencia.** En 2.077 eventos, un mes después de fracturar un pozo nuevo los pozos padre a menos de
1 km rinden 23 puntos menos (respecto de su caudal previo) que los padres a 2-5 km; a los 6 meses la brecha
casi se cierra. La brecha al mes 1 fue de 32 puntos en las fracturas de 2025 y de 44 en 2026 (año en curso).
Contra un control de la misma edad suman unos 10,7 millones de barriles diferidos en los meses 0 a 6, 7,8 de
ellos en YPF. Límites: coordenadas de superficie (no la trayectoria de la rama), y un cierre preventivo del
operador se ve igual que un daño en datos mensuales. Es una huella medida, no una causa.

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
   │  pipeline/wiki.py     páginas por operadora / área / pad + hallazgos con historial + grafo.json
   ▼
agente/ops.py (operaciones tipadas) ─► agente/router.py (modelo local) · agente/mcp_server.py (MCP)
   │  agente/eval/run.py   exactitud en preguntas dev / reservadas
```

GitHub Actions corre los tests en cada push. El servidor de datos.energia.gob.ar no responde
desde los runners de GitHub (fuera de Argentina), así que la actualización semanal corre con
`./refresh.sh` desde una máquina en Argentina (cron), y versiona manifiesto, reporte de calidad y sitio.

## Correr local

```bash
uv sync
uv run pytest -q                    # tests sobre fixtures chicos
uv run python -m pipeline.ingest    # descarga unos 150 MB la primera vez
uv run python -m pipeline.build     # warehouse + controles de calidad
uv run python -m pipeline.wiki      # wiki/ y wiki/grafo.json
uv run python -m pipeline.report    # site/index.html

# Preguntas (modelo local OpenAI-compatible; por defecto llama.cpp en 127.0.0.1:8080)
uv run python -m agente.router "¿Cuánto petróleo difirió YPF por interferencia en La Amarga Chica?"
uv run python -m agente.eval.run --split dev       # para iterar el prompt
uv run python -m agente.eval.run --split holdout   # para reportar; no se ajusta sobre este
uv run python -m agente.mcp_server                 # servidor MCP por stdio
```

Exactitud con `qwen3.5-35b-a3b` local (Q4, 8 GB de VRAM), datos a 2026-09: 27/27 en desarrollo y 15/16 en
reservadas (la falla: se abstuvo ante una pregunta sobre controles de calidad que sí podía responder). El set
es chico y de una sola operación por pregunta; el próximo paso es sumar preguntas que combinan dos operaciones.

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
dashboard. Novel part: a parent/child well-interference event study (near parents lose about 23 points of
rate one month after a nearby frac versus 2-5 km controls; about 10.7 MMbbl deferred), a local-model question
router over 11 typed read-only operations (also an MCP server) with a held-out accuracy eval, and a generated
wiki + graph whose finding pages keep a history per data version.
