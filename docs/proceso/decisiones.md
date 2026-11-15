# Decisiones de diseño y arquitectura

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
agente/ops.py (operaciones tipadas) ─► agente/router.py (modelo de lenguaje) · agente/mcp_server.py (MCP)
   │  agente/eval/run.py   exactitud en preguntas dev / reservadas
```

GitHub Actions corre el lint y los tests en cada push (la prueba de cifras omite lo que necesita el warehouse). El servidor de datos.energia.gob.ar no responde desde los runners de GitHub (fuera de Argentina), así que la actualización semanal corre con `./refresh.sh` desde una máquina en Argentina (cron), y versiona manifiesto, reporte de calidad y sitio.

## Decisiones

- **Raw inmutable y direccionado por hash.** Una corrida sin cambios no escribe nada; cada versión publicada por la Secretaría queda guardada y se puede reconstruir el resultado de cualquier semana.
- **Reconstrucción completa en vez de incremental.** Son 430.000 filas: DuckDB reconstruye todo en menos de un segundo, y así no hay estado incremental que se desincronice. Con más volumen, el paso natural es particionar por mes y cargar solo los meses rectificados.
- **Controles en dos niveles.** Lo que rompe el modelo (grano duplicado, volúmenes negativos después de limpiar, hechos sin dimensión) frena la publicación. Lo que es propio del dato público (TEF inconsistente, fechas futuras, pozos sin fractura informada) se mide y se muestra. Son 28 controles, con conciliación entre capas (filas del CSV, staging y hechos; volúmenes por año; pozos de las dimensiones), deriva de esquema contra las columnas que lee el SQL de staging y frescura del último mes publicado; el linaje de cada tabla se genera en `wiki/hallazgos/linaje.md`.
- **Normalización de operadores en un seed versionado** (`seeds/operadores.csv`): la misma empresa aparece con varias razones sociales (por ejemplo, tres variantes de Vista).
- **Caudales por día calendario**, 1 m3 = 6,2898 bbl.

## Límites del tablero

Las curvas tipo son promedios simples por mes de producción (sin normalizar por rama ni filtrar pozos cerrados). Las clases de evento salen de datos mensuales: un cierre preventivo y un golpe de interferencia pueden verse iguales. En anisotropía y costo no se identifica la pérdida del pozo hijo por la depleción del padre ni el espaciamiento lateral entre ramas (solo hay coordenadas de superficie).
