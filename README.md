# Vaca Muerta en datos

Pipeline reproducible sobre los datos abiertos de la Secretaría de Energía de Argentina (producción mensual por pozo no convencional y datos de fractura): ingesta con hash, modelo en DuckDB, controles de calidad publicados y un tablero estático. Con los datos a septiembre de 2026, Vaca Muerta produce unos 698 kbbl/d de petróleo y YPF el 50%. En YPF la rama horizontal mediana pasó de unos 1.500 m (cohorte 2017) a 3.200 m (cohorte 2025), mientras el petróleo de 12 meses por metro de rama bajó de 83 a 77 bbl/m: una correlación, no una causa.

Caso de estudio, con figuras y cada cifra verificada: [`docs/caso-interferencia.md`](docs/caso-interferencia.md).

## Resultado

Un mes después de fracturar un pozo nuevo, los pozos vecinos a menos de 1 km rinden entre 19 y 23 puntos menos que pozos de control de la misma edad a 2 a 5 km (2.077 eventos).
A los 6 meses la brecha casi se cierra: es producción diferida, no perdida.
Contra un control de la misma edad el diferido de los meses 0 a 6 va de 5,8 a 10,7 millones de barriles (sin duplicar y descontando la brecha previa hasta el total original), y la brecha del mes 1 llega a 44 puntos en 2026.
En la cuenca DJ de Colorado, con los mismos estimadores y una regla fijada de antemano, la brecha del mes 1 se replica (tabla de abajo).
Es una huella medida y sometida a pruebas de placebo y permutación, no una causa demostrada: hay una brecha previa a la fractura
(por eso 23 es una cota superior y 19 a 20 el valor descontado).

## Result

One month after a new well is fracked, neighbouring wells within 1 km produce 19 to 23 percentage points less than same-age control wells 2 to 5 km away (2,077 events).
By month 6 the gap has almost closed: the oil is deferred, not lost.
Against a same-age control the deferral over months 0 to 6 ranges from 5.8 to 10.7 million barrels (de-duplicated and net of the pre-frac gap, up to the original total), and the month-1 gap reaches 44 points in 2026.
In Colorado's DJ basin, the same estimators and a pre-registered rule replicate the month-1 gap (table below).
This is a measured footprint that passes placebo and permutation tests, not a demonstrated cause: there is a gap before the frac
(so 23 is an upper bound and 19 to 20 is the discounted value).

## Mirá esto primero

- `docs/caso-interferencia.md`: el caso de estudio, con figuras y cada cifra con su verificación.
- `site/index.html`: el tablero (estático, se abre directo en el navegador).
- `site/replay.html`: la repetición mes a mes de pozos, fracturas y golpes de agua.
- `site/informe.html`: el informe para un operador (curva del padre, distancia, edad, robustez por operador y área, cierre a 6 meses y calculadora de valor del diferido), armado desde los marts por `pipeline/informe.py`.
- `wiki/hallazgos/interferencia.md`: el hallazgo con su historial por versión de datos.
- `docs/verificacion.md`: cinco preguntas y cómo verificarlas.

## Resultados y veredicto

| Resultado | Cifra | Intervalo | Veredicto |
| --- | --- | --- | --- |
| Interferencia al mes 1 (padres a menos de 1 km contra controles) | 19 a 23 puntos menos | IC 95% por bloques de 5 km de la brecha de 23: 17 a 29 | sostiene, con pretendencia |
| Eje de mayor merma (cuenca) | 93 grados (E-O) | 70 a 122 grados | regla de parada cumplida: es una descripción de la muestra y ya no se presenta como hallazgo; la dirección no se separa del SHmax publicado (67,5) ni de cómo se disponen pads y ramas (`wiki/hallazgos/eje_parada.md`) |
| Validación del eje fuera de tiempo | 92 grados con datos viejos, 88 en los nuevos | no se separa del SHmax ni de ejes al azar | no firme |
| Modelo de costo de la interferencia | R2 fuera de muestra -0,15 (la media del área da 0,01) | ningún coeficiente excluye cero | no predice |
| Placebo y permutación | fechas falsas de -2,4 a 0,6 puntos; permutadas de -8,4 a -4,8; real -22,9 | los intervalos de las fechas falsas incluyen cero | sostiene, con pretendencia |
| Sincronía dentro del mes | la brecha del mes 0 cambia -2,1 puntos por cada 0,1 de fracción del mes posterior al inicio de la fractura | IC 95%: -3,1 a -1,0; el mes previo: -0,7 (IC -1,8 a 0,5) | sostiene |
| Lado del hijo (rendimiento de 12 meses cerca de pozos depletados) | muy depletado contra virgen: -0,2 bbl por metro de rama (-0,3% del rendimiento virgen) | IC 95%: -12,8 a 12,4; el control negativo da 8,9 (IC 2,1 a 15,7) y no es nulo | no firme |
| Replicación en Colorado (cuenca DJ) | -19,9 puntos al mes 1; previa de -6,9 en el mes -1 | IC 95% por bloques de 5 km: -27,5 a -14,8 | se replica, con la regla fijada antes de correr; por día producido la brecha es -8,1, cerca de 60% menor |
| Padre en la ventana de gas (padres gasíferos a menos de 1 km, `wiki/hallazgos/gas.md`) | el padre gasífero cercano da -12,5 puntos de gas al mes 1, pero ya va -7,3 puntos abajo en el mes -1, antes de la fractura | IC 95% por bloques de 5 km de la brecha de gas: -27,1 a -3,6; por día efectivo la brecha es -3,4 y su IC incluye cero | no firme, con la regla fijada antes de correr: no pasa la pretendencia |
| Prueba prospectiva (`wiki/hallazgos/prospectiva.md`) | congelada el 2026-11-18 con los datos hasta 2026-09: brecha del mes 1 de -22,9 puntos (intervalo predicho -28,7 a -16,8) y cierre al mes 6, en eventos cuyos meses siguientes no estaban publicados | se puntúa con cada publicación nueva; hacen falta 100 eventos cercanos con el mes medido | se puntúa en cada publicación nueva; el veredicto y el mes de sus datos están en la página (al congelar, pendiente) |
| Diferimiento | a los 6 meses la brecha casi se cierra | al mes 12 no hay más padres cercanos bajo el 90% de su trayectoria que controles | sostiene: diferido, no perdido |

## Cómo correrlo

```bash
uv sync
uv run pytest -q                           # tests sobre fixtures chicos
uv run ruff check pipeline agente tests    # lint, el mismo que corre en CI
uv run python -m pipeline.run_all          # toda la cadena con tiempos; --with-ingest, --only a,b, --skip a,b, --list
uv run python -m pipeline.claims           # verifica contra el warehouse las cifras citadas en este README
```

`--with-ingest` descarga unos 150 MB y necesita una red argentina: datos.energia.gob.ar no responde desde fuera del país, así que la actualización semanal corre con `./refresh.sh` desde una máquina en Argentina y GitHub Actions solo corre lint y tests.
Demo sin la descarga grande: `make demo` (muestra pequeña; ver `data/muestra/README.md`).
Demo del agente sin modelo: `uv run python -m agente.demo`.
Preguntas con un modelo propio (cualquier endpoint compatible con OpenAI, con `VM_LLM_URL` y `VM_LLM_MODEL`): `uv run python -m agente.router "¿Cuánto petróleo difirió YPF por interferencia en La Amarga Chica?"`.

## Límites

- Coordenadas de superficie (pads), no la trayectoria de la rama.
- Los intervalos de las demás pruebas remuestrean pads hijo; con bloques espaciales de 5 km (144 bloques) el IC de la brecha del mes 1 es 1,29 veces más ancho y ningún veredicto cambia (`wiki/hallazgos/bloques.md`).
- Datos mensuales: un cierre preventivo del operador se ve igual que un daño por interferencia.
- No se afirma causalidad: es una huella medida contra un control, con una brecha previa a la fractura.
- La caída de los padres cercanos no es igual en todas las direcciones de superficie en la muestra completa (con intervalos por pads), pero con datos públicos esa dirección no se separa del SHmax publicado ni de la forma en que se disponen los pads; la geometría de las ramas no se pudo probar. No es un hallazgo sobre esfuerzos ni sobre la fractura. La regla de parada fijada antes de correr se cumplió (`wiki/hallazgos/eje_parada.md`): la hipótesis del libro pasó de `anisotropia` a `asimetria_de_superficie`.
- Dosis y respuesta: con datos públicos no se ve que la caída del mes 1 crezca con la arena por etapa, la arena por metro de rama, la presión máxima de tratamiento ni la depleción del padre (modelo conjunto con Holm e intervalos por pads hijo: ninguna cumple y los quintiles no muestran orden; tampoco en la parte de caudal por día). Es compatible con cierre preventivo o con variables no observadas (espaciamiento real) y no dice que no haya golpes de fractura (`wiki/hallazgos/dosis.md`). Tampoco aparece una respuesta tardía en los meses 2 a 4 (16 pruebas con Holm; la más cercana es la depleción al mes 4, con p de 0,016 sin ajustar y de 0,26 ajustado; `wiki/hallazgos/dosis_meses.md`). Tampoco con la arena de todo el pad del hijo (pozos del pad fracturados en el mismo mes o a un mes) ni en los eventos a menos de 0,5 km con la interacción depleción por cercanía: ninguna de las nueve pruebas cumple tras Holm, y el límite alto de los intervalos llega a 0,29 desvíos de la caída en la muestra completa y a 0,43 (índice) o 0,54 (caudal por día) en el subconjunto cercano, así que no se descartan efectos de ese tamaño ni menores; cada variable sola da lo mismo y el FIV no pasa de 2,6 (prueba agregada después de ver los resultados; `wiki/hallazgos/dosis_pad.md`).
- Control de la brecha: la brecha del mes 1 (de -23 a -24 puntos) y su cierre a los 6 meses no dependen de cuál de cuatro controles se use (2 a 5 km, 5 a 10 km, 2 a 10 km, y 2 a 5 km sin otro hijo a menos de 2 km); a los 6 meses la brecha queda dentro de 5 puntos con los cuatro (entre -2,1 y -4,7), pero con tres de ellos su IC excluye cero, así que "se cierra" quiere decir menos de 5 puntos y no cero (`wiki/hallazgos/anillo.md`).
- Capa de decisión para un operador: la caída del mes 1, la parte de la brecha de caudal que se cierra a los 6 meses (80 a 91% según el control; quedan 2 a 5 puntos; no es volumen recuperado), el diferido medio por padre (446 a 821 m3 de petróleo en los meses 0 a 6) y una cota de lo que podría no volver (213 m3 por evento), por edad del padre y banda de espaciamiento, con precio y tasa como entradas de quien lo usa; dice qué dato interno resolvería lo que el dato público no resuelve (`wiki/hallazgos/decision_operador.md`).
- Potencia del nulo de dosis: con 1.544 eventos en 262 pads hijo, el efecto mínimo detectable con 80% de potencia y corrección de Holm va de 0,22 a 0,32 desvíos de la caída por desvío de la dosis; un efecto de 0,2 puede pasar inadvertido con este dato, y la simulación de planta y recupera muestra que la cuenta analítica es optimista (`wiki/hallazgos/potencia_dosis.md`).
- Modo con datos propios: el mismo estudio de eventos y el mismo modelo de dosis sobre los CSV de un operador, corrido en su máquina y con un rechazo automático si una ruta cae dentro del repo sin estar ignorada; sobre el dato público reproduce la brecha del mes 1 y sus 2.077 eventos (`docs/operador-datos-propios.md`, `uv run python -m pipeline.local`).
- Robustez por operador y por área: sacando de a un operador (7) o de a un área (8) con al menos 50 eventos cercanos, la brecha del mes 1 queda entre -29,3 y -20,0 puntos con el IC 95% siempre por debajo de cero (sin YPF: -22,6) y el cierre del mes 6 queda dentro de 5 puntos; el nulo de dosis no se replica en el Colorado porque ese dato público no trae arena, etapas ni presión (`wiki/hallazgos/robustez_operador.md`).
- Hoja resumen para un operador (qué se ve, qué no se sabe, qué hacer con esto), con cada cifra verificada: `docs/resumen-operador.md`.
- El modelo de costo no predice un evento puntual: sus coeficientes describen asociaciones en la muestra.
- Lado del hijo: el grupo muy depletado se ubica en zonas de desarrollo más denso y el control negativo da efecto, así que su nulo no se lee como ausencia de degradación. Comparando hijos del mismo lugar (diseño fijado después de ver ese control negativo y antes de correrlo), dentro de cuadrados de 2 km el hijo muy depletado da -11,2% del virgen (IC 95%: -33,8% a 11,5%) con el control negativo del grupo que decide nulo: sigue no firme, y la mayor pérdida compatible con el dato público es la cota superior de ese intervalo (`wiki/hallazgos/hijo_celdas.md`).
- Datos públicos declarados por las operadoras; pueden rectificarse después.
- Replicación en otra cuenca: se corrió en la cuenca DJ de Colorado con una regla fijada de antemano (`wiki/hallazgos/replicacion.md`); es validez externa de la huella y no una estimación conjunta. Colorado no tiene etapas ni arena, la rama es un proxy y los cierres aparecen como cero días producidos. `--with-colorado` es opcional.
- Proyecto personal, no afiliado ni avalado por ninguna empresa.

## Cómo se hizo

Ingesta con hash (raw inmutable por versión), modelo en DuckDB, 28 controles de calidad (los bloqueantes frenan la publicación) y linaje de cada tabla en `wiki/hallazgos/linaje.md`.
Hecho con asistencia de IA; cada cifra de esta página se verifica contra el warehouse con `uv run python -m pipeline.claims` y hay 492 tests.
Preguntas en lenguaje natural sobre 16 operaciones tipadas de solo lectura (`agente/`, también como servidor MCP): exactitud 40/41 en desarrollo y 23/27 en reservadas, con la respuesta correcta calculada sobre el warehouse vigente.

## Decisiones de diseño

- Raw inmutable y direccionado por hash: una corrida sin cambios no escribe nada y se puede reconstruir cualquier semana.
- Reconstrucción completa en vez de incremental: son 430.000 filas y DuckDB las reconstruye en segundos, sin estado que se desincronice.
- Controles en dos niveles: lo que rompe el modelo frena la publicación; lo propio del dato público se mide y se muestra.

Más: `wiki/` (hallazgos, operadoras, áreas, pads y grafo, con el libro de quince hipótesis con umbral fijo), `docs/proceso/` (arquitectura, decisiones y planes) y `agente/` (operaciones, evaluación y servidor MCP).
