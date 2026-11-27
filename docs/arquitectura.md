# Arquitectura

Qué entra, qué se calcula, qué se publica y qué impide que una cifra publicada se aparte del dato. Una página; el detalle de cada parte está en el docstring de su módulo.

## El flujo

```
Secretaría de Energía, datos abiertos
(producción no convencional por pozo y mes; fracturas, Adjunto IV; trayectorias de pozo)
    |
    v
pipeline.ingest ......... data/raw/ (una copia por fecha y hash, nunca se pisa) y data/manifest.json
    |
    v
pipeline.build .......... pipeline/sql/01 a 05 -> data/warehouse.duckdb
    |                       stg_  filas de la fuente, tipadas y con el operador normalizado
    |                       dim_ y fct_  el modelo: un pozo, un pozo-mes, un evento fechado
    |                       int_  pares padre e hijo, bandas de distancia, eventos del estudio
    |                       mart_  lo que leen las páginas
    |                     pipeline.checks: los controles bloqueantes frenan el build; los avisos se cuentan y se publican
    v
análisis ................ un módulo por pregunta (placebo, bloques, dosis, hijo, gas, carga_anual y los demás pasos de run_all)
    |                     cada uno lee int_ y mart_, escribe sus propios mart_ y arma su página de wiki/hallazgos/
    |                     pipeline.trayectorias lee además la copia cruda de las trayectorias, que el SQL no usa
    v
publicación ............. pipeline.figuras (docs/img/), pipeline.wiki (wiki/), pipeline.informe (site/informe.html),
    |                     pipeline.report (site/index.html), pipeline.replay (site/replay.html), pipeline.mundo (site/mundo.html)
    v
pipeline.claims ......... las cifras que tienen verificación en README.md, docs/, wiki/ y site/, contra el warehouse
```

Todo corre con un comando, `uv run python -m pipeline.run_all`, que ejecuta los pasos en ese orden y muestra el tiempo de cada uno. `--list` imprime los pasos; `--only` y `--skip` corren una parte.

## Decisiones que sostienen el resto

- **Raw inmutable.** La descarga guarda cada archivo con su fecha y su hash, y el manifiesto registra origen, tamaño y hora. Si la fuente no cambió no se guarda una copia nueva, solo se anota cuándo se verificó. Las copias anteriores quedan en disco junto a la nueva: nada las pisa ni las borra.
- **Reconstrucción completa.** Cada tabla se rehace desde raw con `create or replace`. No hay estado incremental que se desincronice. Dos builds de los mismos archivos dan las mismas tablas del modelo bit a bit: `pipeline.build` arma el modelo con un solo hilo y toma la fecha de corte de las fracturas del manifiesto, no del reloj. Si el manifiesto no trae esa fecha (la muestra de `data/muestra/`), usa el día de la corrida.
- **SQL para el modelo, Python para la estadística.** Las tablas con grano definido (pozo, pozo-mes, par padre e hijo, evento) son SQL que se lee de arriba abajo. El remuestreo, los modelos y las pruebas son módulos de Python que leen esas tablas y no las modifican.
- **Controles en dos niveles.** Lo que rompe el modelo (grano, nulos, valores imposibles después de limpiar) frena la publicación. Lo que es propio del dato público (rectificaciones, meses sin carga, fracturas que se cargan tarde) no se corrige en silencio: se mide y se publica en `data/dq_report.json`.
- **Linaje leído del código.** `wiki/hallazgos/linaje.md` se arma leyendo el SQL y el código de los módulos de Python que escriben marts: de qué archivo crudo, o de qué valor del manifiesto, sale cada tabla del warehouse. Para los marts de Python el grano es el módulo (cada mart muestra los orígenes de todo su módulo), y un test comprueba que la página cubre todas las tablas del warehouse.

## Qué impide que una cifra se aparte del dato

1. **`pipeline.claims`.** Una verificación fija una cifra escrita en un documento: el archivo, la frase que la contiene y la función que calcula su valor desde el warehouse, un reporte versionado o el código. Si el dato cambia y el texto no, la verificación falla y dice cuál. Hay verificaciones sobre el README, el caso de estudio, el resumen para un operador, `docs/verificacion.md`, `site/index.html`, `site/informe.html`, `site/mundo.html` y una parte de `wiki/hallazgos/`, incluidas páginas que genera el pipeline, para detectar una página vieja en el repositorio. Una cifra sin verificación no está cubierta, salvo en `wiki/hallazgos/limites.md`, `README.md`, `docs/resumen-operador.md` y `docs/caso-interferencia.md`: cada una tiene un test que falla si aparece una cifra que ni una verificación fija ni una frase definicional (un parámetro del método, una fecha, un número de sección) explica.
2. **Reglas fijadas antes de correr.** Los módulos que dan un veredicto (entre ellos la réplica en otra cuenca, el gas, la subida de 2026 y la prueba prospectiva) tienen su regla escrita en el docstring antes de calcular: muestra, estadístico, umbrales y veredictos posibles. La regla lleva su fecha y dice qué se había mirado antes de fijarla; la de la subida de 2026 dice además qué cambia en los documentos con cada veredicto. Lo que se agregó después de ver un resultado está marcado así en el mismo docstring y en la página que lo publica.
3. **Libro de hipótesis.** `pipeline/hallazgos.py` guarda cada hipótesis como una consulta, una expectativa y un umbral fijo (o el veredicto de su propia regla, si la tiene), y `pipeline.wiki` las vuelve a evaluar en cada corrida. El resultado está en `wiki/hallazgos/libro.md`, con las que no se sostienen incluidas.
4. **Prueba prospectiva.** Las predicciones para los meses que todavía no existían quedaron congeladas en `data/prospectiva_congelada.json`, con su hash. Cada actualización del dato las puntúa; el archivo no se edita.
5. **Tests.** Fixtures chicos y calculables a mano para los estimadores, pruebas de determinismo (dos corridas dan las mismas tablas y los mismos archivos, sin contar la marca de hora de generación de las páginas HTML) y una prueba que construye el warehouse y el tablero sobre la muestra de `data/muestra/`.

## Qué corre dónde

- **En cualquier máquina:** `uv sync`, los tests, el lint y `make demo` (el warehouse y el tablero sobre la muestra de `data/muestra/`, sin descargar datos; sus cifras no son las de la cuenca).
- **Con el dato completo:** `--with-ingest` necesita una red argentina, porque el servidor de la Secretaría no respondió desde fuera del país donde se probó (los dos runners de GitHub en Estados Unidos de la línea siguiente). Ahí corre también `./refresh.sh`, que baja el dato nuevo y rearma todo.
- **Desde fuera de la Argentina:** `scripts/bajar_datos_crudos.py` baja de la release los tres archivos crudos del manifest y `pipeline.run_all` sin `--with-ingest` arma todo desde ellos. El workflow `rerun-afuera.yml`, que se lanza a mano en la copia pública, hace eso en un runner de GitHub y corre también `pipeline.claims`; con `cuencas`, suma Wyoming y Colorado desde sus fuentes públicas. Se corrió el 2026-11-27 (UTC) en dos runners de GitHub en Estados Unidos, donde el portal de la Secretaría no respondió en los 30 segundos que lo espera el workflow: la corrida 45916953885, solo con Vaca Muerta, dio en `pipeline.claims` 3444 PASS, 0 FAIL y 982 SKIP, y la 45916967376, con las tres cuencas, 4353 PASS, 0 FAIL y 73 SKIP; son los mismos totales que en la máquina donde se armó el estudio. `run_all` tardó 4347 y 4685 segundos.
- **En integración continua:** lint y tests. Las verificaciones que necesitan el warehouse se saltean ahí y se dicen como salteadas, no como aprobadas.

## Otras entradas

- **Datos propios de un operador.** `pipeline.local` arma en memoria las mismas tablas a partir de dos CSV y llama al mismo código del estudio de eventos y de dosis. No reimplementa nada y se niega a leer o escribir en rutas que git versionaría (`docs/operador-datos-propios.md`).
- **Preguntas en lenguaje natural.** `agente/` expone operaciones tipadas de solo lectura sobre el warehouse, también como servidor MCP. El modelo elige la operación y sus parámetros; la cifra la calcula la operación, no el modelo. La evaluación está en `agente/eval/`.
- **Otra cuenca.** `pipeline/colorado/` baja y arma un warehouse aparte con el dato público de Colorado, y `pipeline.replicacion` corre ahí el mismo estudio de eventos con su regla fijada antes de correr. Es opcional (`--with-colorado`).
