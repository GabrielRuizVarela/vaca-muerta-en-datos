# Vaca Muerta en datos

Pipeline reproducible sobre los datos abiertos de la Secretaría de Energía de Argentina:
producción mensual por pozo no convencional (Capítulo IV) y datos de fractura (Adjunto IV).
Ingesta idempotente, modelo en DuckDB, controles de calidad publicados y un tablero estático
que se regenera con cada actualización semanal.

**Tablero:** `site/index.html` (estático, se abre directo en el navegador).
**Repetición temporal:** `site/replay.html` (mapa mes a mes de los pozos, las fracturas y los golpes de agua; también se abre con doble clic).

## Status

**2026-11-15.** Fase 2 completa y en `main` (PR 2 a 17): eventos, libro de hallazgos, repetición temporal, anisotropía por área con mapa, modelo de costo, `quiebre_caudal`, agente de 16 operaciones con preguntas de dos operaciones, robustez y `docs/para-projectA.md`. Los tests de determinismo cubren ahora el build, los marts de costo y de robustez, la wiki, `site/index.html` y `site/replay.html` (salvo la marca de hora). Ese test encontró un orden sin fijar en el tablero (la serie mensual por operador), ya corregido. La repetición temporal ya no carga fuentes de la red (pila de fuentes del sistema, funciona sin conexión) y el mapa de áreas se ve bien en modo claro y oscuro. Las preguntas nuevas del agente se midieron con un modelo del pool gratuito (40/41 en desarrollo, 23/27 en reservadas); falta la cifra con el modelo local. Los ejes y el modelo de costo no cambian: el eje de la cuenca ronda 93 grados (IC 70 a 122, p 0,022) pero no es firme ni se separa del SHmax publicado (67,5), y ningún factor del modelo de costo tiene un intervalo que excluya el cero. Hay 186 tests en verde. El informe de pads que cambian al agrupar por cercanía (1.210 de 3.448 pozos) está en la wiki. Las cifras de este README se verifican contra el warehouse con `pipeline.claims`, y `pipeline.run_all` corre toda la cadena con tiempos. Después se agregaron la validación del eje (estable en el punto estimado, no firme), la validación cruzada del modelo de costo (no le gana a la media fuera de muestra) y las pruebas de placebo (hay pretendencia: los 23 puntos son una cota superior y quedan 19 a 20 tras descontarla), 9 controles de calidad más (28) con linaje de tablas, una operación nueva del agente (16) y un tablero con el eje y el costo leídos del warehouse. `docs/para-projectA.md` mapea cada una de las cinco preguntas a un comando que la verifica.

**Asks for the owner**

1. Si querés la cifra con el modelo local `qwen3.5-35b-a3b-uncensored` (llama.cpp en 127.0.0.1:8080) hace falta el archivo del modelo en esta máquina u otra: no está acá y la RAM libre no alcanza. Con `VM_LLM_URL` y `VM_LLM_MODEL` el eval corre contra cualquier endpoint compatible con OpenAI. Reversible: sí, solo escribe resultados.

Resuelto el 2026-11-15: la corrida vieja 43675133643 del workflow `refresh` se borró en GitHub (con tu OK), así que `main` ya no figura en rojo. El repo queda privado (decisión tuya): nadie fue contactado y no hay mensaje redactado.

## Qué muestra

- Producción de petróleo de Vaca Muerta por operador desde 2015 (kbbl/d) y la participación de YPF.
- Curvas tipo de pozos shale oil por cohorte (año del primer petróleo), YPF contra el resto.
- Diseño de terminación (rama horizontal, etapas, arena por metro) contra productividad a 12 meses.
- **Interferencia entre pozos:** cuando se fractura un pozo nuevo, cuánto caen los pozos vecinos que ya producían,
  contra pozos de control de la misma edad.
- Una tabla de calidad de datos: qué anomalías tiene el dato público y cuántas filas afectan.
- **Eventos:** una tabla de eventos por pozo (fractura, primera producción, cambios de estado y de extracción,
  cierres, saltos de corte de agua y quiebres de caudal en la fecha de fractura de un vecino), con la operación `eventos_pozo` para consultarlos por sigla.
- **Libro de hallazgos:** cinco hipótesis con umbral fijo, reevaluadas con cada dato nuevo y registradas en
  `wiki/hallazgos/ledger.csv`; la operación `libro_hallazgos` informa cuáles están confirmadas. La operación
  `clases_interferencia` cuenta cuántos pozos padre muestran golpe, cierre preventivo, ambos o ningún efecto.
- **Repetición mes a mes:** `site/replay.html`, generado por `pipeline.replay`, muestra cómo avanza el dato mes a mes.

Además:

- **Preguntas en lenguaje natural** (`agente/`) con un modelo local, sobre 16 operaciones tipadas de solo
  lectura, expuestas también como servidor MCP. El modelo elige la operación y sus argumentos; nunca escribe SQL
  ni números. Cada respuesta cita tablas, mes de datos y hash del archivo crudo.
- **Evaluación de exactitud** (`agente/eval/`): preguntas de desarrollo y reservadas, con la respuesta correcta
  calculada sobre el warehouse vigente (no guardada), así la evaluación sigue valiendo después de cada actualización.
- **Wiki y grafo generados** (`wiki/`): una página por operadora, área y pad con interferencia, y una página de
  hallazgo que acumula un historial por versión de datos. `wiki/grafo.json` une operadora, área, pad y pozo, con
  aristas `interfiere` (pozo hijo a pozo padre, con distancia y barriles diferidos).

Con los datos a septiembre de 2026: Vaca Muerta produce unos 698 kbbl/d de petróleo, YPF el 50%.
La rama horizontal mediana de YPF pasó de unos 1.500 m (cohorte 2017) a 3.200 m (cohorte 2025),
mientras el petróleo de 12 meses por metro de rama bajó de 83 a 77 bbl/m. Es una correlación,
no una causa.

**Interferencia.** En 2.077 eventos, un mes después de fracturar un pozo nuevo los pozos padre a menos de
1 km rinden 23 puntos menos (respecto de su caudal previo) que los padres a 2-5 km; a los 6 meses la brecha
casi se cierra. La brecha al mes 1 fue de 32 puntos en las fracturas de 2025 y de 44 en 2026 (año en curso).
Contra un control de la misma edad suman unos 10,7 millones de barriles diferidos en los meses 0 a 6, 7,8 de
ellos en YPF. Límites: coordenadas de superficie (no la trayectoria de la rama), y un cierre preventivo del
operador se ve igual que un daño en datos mensuales. Es una huella medida, no una causa.

**Anisotropía y costo de la interferencia.** `pipeline/costo.py` estima, entre 0,3 y 1 km, el eje de mayor
merma del padre al mes 1 con un ajuste axial coseno (controlando distancia y edad, con intervalo por bootstrap
de pads hijo y test de permutación por bloques de pads). En toda la cuenca el eje queda cerca de 93 grados (E-O, IC 95% de 70 a 122),
algo más al este-oeste que el SHmax publicado (OSO-ENE, unos 67,5 grados); entre las áreas, Loma Campana y
Fortín de Piedra tienen un eje definido y las chicas no. Un modelo lineal de los barriles diferidos en los
meses 0 a 6 mide cuánto pesan distancia, rumbo respecto del eje, edad y caudal del padre, arena y etapas del
hijo y cierre declarado; ningún factor tiene un intervalo que excluya cero (el desvío respecto del eje es el que más se acerca: unos -960 bbl por cada 10 grados, con el eje estimado fuera de muestra). Al mes 12, la
fracción de padres cercanos que no vuelve al 90% de la trayectoria de control no excede a la de los controles
(diferimiento, no pérdida permanente). La operación `costo_interferencia` del agente da el diferido esperado
alrededor de un pad o punto, ahora con un intervalo de 80% basado en los errores fuera de muestra. Esos errores son grandes: con validación cruzada por pad hijo el R2 del modelo es -0,15, sin mejorar a la media simple en R2 ni en RMSE (R2 de cero con la media del entrenamiento y de 0,01 con la media del área), y para el pad p165347 el diferido esperado de unos 232.700 bbl tiene un intervalo de 80% de unos 175.000 a 399.000 bbl (supone errores independientes entre padres, así que el real es más ancho). Los coeficientes describen asociaciones en la muestra, no sirven para predecir un evento puntual. Detalle en `wiki/hallazgos/anisotropia.md`. Es una comparación con lo publicado, no
una medición de esfuerzos. `pipeline/robustez.py` repite la estimación en 13 subconjuntos (períodos, operador, sin cada
área grande, bandas de distancia, muestra recortada): en los 9 donde el eje está definido el IC contiene los 93 grados de la
cuenca, pero en 4 el IC mide 90 grados o más y en 5 el p de permutación no baja de 0,10 (sin Loma Campana el eje deja de
estar definido), así que la dirección este-oeste es consistente pero no firme. El coeficiente de desvío respecto del eje
(unos -960 bbl por 10 grados) conserva el signo en las 6 especificaciones alternativas, pero ningún intervalo excluye cero.
Detalle en `wiki/hallazgos/robustez.md`.
`pipeline/validacion.py` lo somete a tres pruebas más. Con otros resultados medidos sobre los mismos 1.734 eventos, solo
el salto del corte de agua da un eje definido (82 grados, IC de 61 a 101, p de 0,036), consistente con los 93 grados; la
fracción de días efectivos (116 grados), el caudal al mes 2 y 3 y el cierre declarado no lo definen. Por año de fractura del
hijo ningún grupo tiene un eje definido (el de 2025 queda lejos, en 8 grados, con un IC de 124 grados). Con un corte en
2023-06, el eje estimado solo con los 925 eventos de entrenamiento (92 grados) queda en 88 grados en los 809 de prueba, pero ahí
el IC mide 128 grados y el p de permutación es 0,43; la mejora del eje de entrenamiento en la prueba (0,4% de la suma de cuadrados; solo el eje sale del entrenamiento) no se separa
de la del SHmax ni de la de ejes al azar. El eje este-oeste es consistente en el punto estimado, pero no se replica como
resultado firme fuera de muestra. Detalle en `wiki/hallazgos/validacion.md`.
`pipeline/placebo.py` somete el estudio de eventos a pruebas de falsación. Con fechas de fractura falsas (±6 y ±12 meses) la brecha del mes 1 es cercana a cero (de -2,4 a 0,6 puntos, todos los intervalos incluyen cero), y con las fechas permutadas entre hijos del mismo año la brecha real (-22,9 puntos) queda fuera de las 200 permutadas (de -8,4 a -4,8); con fechas permutadas el eje no queda definido en ninguna de 10 corridas con intervalo. Pero no sale limpio: los padres cercanos ya rendían menos que los controles antes de la fractura (-2,5, -3,5 y -6,3 puntos en los meses -3, -2 y -1, con intervalos que excluyen cero, también sin los golpes previos de pozos vecinos), así que los 23 puntos son una cota superior: medida contra ese nivel previo, la caída adicional al mes 1 es de 19 a 20 puntos, si la brecha previa es un nivel distinto de los padres cercanos y no un efecto anticipado (los datos mensuales no lo separan). Detalle en `wiki/hallazgos/placebo.md`.

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

GitHub Actions corre el lint y los tests en cada push (la prueba de cifras omite lo que necesita el warehouse). El servidor de datos.energia.gob.ar no responde
desde los runners de GitHub (fuera de Argentina), así que la actualización semanal corre con
`./refresh.sh` desde una máquina en Argentina (cron), y versiona manifiesto, reporte de calidad y sitio.

## Correr local

```bash
uv sync
uv run pytest -q                    # tests sobre fixtures chicos
uv run ruff check pipeline agente tests   # lint (reglas E9 y F), el mismo que corre en CI

# Todo en un comando: build, costo, robustez, validación, placebo, wiki, report, replay y claims, con tiempos y deteniéndose en el primer fallo
uv run python -m pipeline.run_all                 # --with-ingest descarga primero; --only a,b; --skip a,b; --list
uv run python -m pipeline.claims                  # verifica contra el warehouse las cifras citadas en este README y en docs/para-projectA.md (sale 1 si alguna difiere)

# Los pasos por separado
uv run python -m pipeline.ingest    # descarga unos 150 MB la primera vez
uv run python -m pipeline.build     # warehouse + controles de calidad
uv run python -m pipeline.costo     # anisotropía y costo de la interferencia (después de build)
uv run python -m pipeline.robustez  # estabilidad del eje y del costo en subconjuntos (después de costo)
uv run python -m pipeline.validacion  # eje con otros resultados, por año y fuera de tiempo (después de costo)
uv run python -m pipeline.placebo   # pretendencia, fechas falsas y permutación del estudio de eventos (después de build)
uv run python -m pipeline.wiki      # wiki/ y wiki/grafo.json
uv run python -m pipeline.report    # site/index.html
uv run python -m pipeline.replay    # site/replay.html (unos 4,5 MB, datos embebidos)

# Preguntas (modelo local OpenAI-compatible; por defecto llama.cpp en 127.0.0.1:8080)
uv run python -m agente.router "¿Cuánto petróleo difirió YPF por interferencia en La Amarga Chica?"
uv run python -m agente.eval.run --split dev       # para iterar el prompt
uv run python -m agente.eval.run --split holdout   # para reportar; no se ajusta sobre este
uv run python -m agente.mcp_server                 # servidor MCP por stdio
```

Exactitud medida el 2026-11-15 con `nvidia/nemotron-3.5-super-vl-120b-a12b` (120B parámetros, servido por el pool gratuito y no por el modelo local; viajan solo las preguntas y el catálogo de operaciones, nunca el warehouse), datos a 2026-09: 40/41 en desarrollo y 23/27 en
reservadas (85%). El set de desarrollo se usó para iterar el prompt, así que la cifra a reportar es la de reservadas. Las cuatro fallas de reservadas: dos preguntas en las que el modelo no devolvió respuesta, una consulta al libro de hallazgos sin el id de la hipótesis y una pregunta de dos mediciones que resolvió con una sola. La falla de desarrollo es un argumento omitido (`tipo`). La medición anterior, con `qwen3.5-35b-a3b` local (Q4, 8 GB de VRAM) sobre el set previo a las preguntas de dos operaciones, fue 27/27 y 15/16; ese modelo no está hoy en esta máquina y no se midió con el set completo.

## Decisiones

- **Raw inmutable y direccionado por hash.** Una corrida sin cambios no escribe nada; cada versión
  publicada por la Secretaría queda guardada y se puede reconstruir el resultado de cualquier semana.
- **Reconstrucción completa en vez de incremental.** Son 430.000 filas: DuckDB reconstruye todo en
  menos de un segundo, y así no hay estado incremental que se desincronice. Con más volumen, el paso
  natural es particionar por mes y cargar solo los meses rectificados.
- **Controles en dos niveles.** Lo que rompe el modelo (grano duplicado, volúmenes negativos después
  de limpiar, hechos sin dimensión) frena la publicación. Lo que es propio del dato público (TEF
  inconsistente, fechas futuras, pozos sin fractura informada) se mide y se muestra. Son 28 controles,
  con conciliación entre capas (filas del CSV, staging y hechos; volúmenes por año; pozos de las dimensiones),
  deriva de esquema contra las columnas que lee el SQL de staging y frescura del último mes publicado; el
  linaje de cada tabla se genera en `wiki/hallazgos/linaje.md`.
- **Normalización de operadores en un seed versionado** (`seeds/operadores.csv`): la misma empresa
  aparece con varias razones sociales (por ejemplo, tres variantes de Vista).
- **Caudales por día calendario**, 1 m³ = 6,2898 bbl.

## Límites

Datos públicos declarados por las operadoras; pueden rectificarse después. Las curvas tipo son
promedios simples por mes de producción (sin normalizar por rama ni filtrar pozos cerrados). Los
hallazgos son correlaciones. Las clases de evento salen de datos mensuales: un cierre preventivo y un golpe de
interferencia pueden verse iguales. Anisotropía y costo: no se identifica la pérdida del pozo hijo por la
depleción del padre ni el espaciamiento lateral entre ramas (solo hay coordenadas de superficie), y los ejes
de las áreas chicas dependen de pocos pads. Proyecto personal, no afiliado ni avalado por ninguna empresa.

---

*English summary:* a reproducible data pipeline over Argentina's public well-level production and
frac data for Vaca Muerta: idempotent hash-addressed ingestion, a DuckDB model with a (well, month)
grain, two-tier data-quality checks published alongside results, and a weekly self-refreshing static
dashboard. Novel part: a parent/child well-interference event study (near parents lose about 23 points of
rate one month after a nearby frac versus 2-5 km controls; about 10.7 MMbbl deferred), a local-model question
router over 16 typed read-only operations (also an MCP server) with a held-out accuracy eval, and a generated
wiki + graph whose finding pages keep a history per data version.
