# Vaca Muerta en datos

Pipeline reproducible sobre los datos abiertos de la Secretaría de Energía de Argentina (producción mensual por pozo no convencional y datos de fractura): ingesta con hash, modelo en DuckDB, controles de calidad publicados y un tablero estático. Con los datos a septiembre de 2026, Vaca Muerta produce unos 698 kbbl/d de petróleo y YPF el 50%. En YPF la rama horizontal mediana pasó de unos 1.500 m (cohorte 2017) a 3.200 m (cohorte 2025), mientras el petróleo de 12 meses por metro de rama bajó de 83 a 77 bbl/m: una correlación, no una causa.

Caso de estudio, con figuras y cada cifra verificada: [`docs/caso-interferencia.md`](docs/caso-interferencia.md).

## Resultado

Un mes después de fracturar un pozo nuevo, los pozos vecinos a menos de 1 km rinden entre 19 y 23 puntos menos que pozos de control de la misma edad a 2 a 5 km (2.077 eventos).
A los 6 meses la brecha casi se cierra: es producción diferida, no perdida.
Contra un control de la misma edad el diferido de los meses 0 a 6 va de 5,8 a 10,7 millones de barriles (sin duplicar y descontando la brecha previa hasta el total original).
En otras cuencas, con los mismos estimadores y una regla fijada de antemano, la brecha del mes 1 se replica en 1 de 2 cuencas: en la cuenca DJ de Colorado sí y en Wyoming no (tabla de abajo).
Es una huella medida y sometida a pruebas de placebo y permutación, no una causa demostrada: hay una brecha previa a la fractura
(por eso 23 es una cota superior y 19 a 20 el valor descontado).

## Result

One month after a new well is fracked, neighbouring wells within 1 km produce 19 to 23 percentage points less than same-age control wells 2 to 5 km away (2,077 events).
By month 6 the gap has almost closed: the oil is deferred, not lost.
In other basins, with the same estimators and a pre-registered rule, the gap one month after the frac replicates in 1 of 2 basins: yes in Colorado's DJ basin, no in Wyoming (table below).
It is a measured footprint that passes placebo and permutation tests, not a demonstrated cause.
The rest of this repository is in Spanish.

## Mirá esto primero

- `docs/caso-interferencia.md`: el caso de estudio, con figuras y cada cifra con su verificación.
- `site/index.html`: el tablero (estático, se abre directo en el navegador).
- `site/replay.html`: la repetición mes a mes de pozos, fracturas y golpes de agua.
- `site/mundo.html`: Vaca Muerta en 4D, la cuenca en 3D para recorrer en el tiempo: el estudio de eventos se arma desde el mapa, se puede plantar un pozo hijo hipotético y hacer dos cuentas de física con supuestos propios; cada elemento dice si es dato, medido o supuesto, y la página recalcula las respuestas del pipeline al abrir.
- `site/globo.html`: el globo de las cuencas: la Tierra queda oscura salvo donde un regulador publica petróleo por pozo (cada jurisdicción auditada con la textura de su nivel; lo oscuro es "no publica por pozo", no "no produce"), y cada cuenca medida (Vaca Muerta, Colorado, Wyoming) se abre en la misma repetición mes a mes que `mundo.html`, con su veredicto leído de los marts; se arma con `pipeline/globo.py` y necesita los tres warehouses.
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
| Replicación en Wyoming (WOGCC) | -2,5 puntos al mes 1; previa de -11,9 en el mes -1 | IC 95% por bloques de 5 km: -5,5 a 2,2 | no se replica, con la misma regla fijada antes de bajar la producción de Wyoming: el IC incluye cero y la brecha previa es mayor que la del mes 1; el mes 0 es la primera terminación y no la fractura |
| Replicación por cuenca (`wiki/hallazgos/replicacion_cuencas.md`) | se replica en 1 de 2 cuencas: Colorado sí, Wyoming no | sin estimación conjunta ni probabilidad | se publican las dos; con dos cuencas la lectura no separa una huella que depende de la cuenca de ruido distinto en cada una |
| Padre en la ventana de gas (padres gasíferos a menos de 1 km, `wiki/hallazgos/gas.md`) | el padre gasífero cercano da -12,5 puntos de gas al mes 1, pero ya va -7,3 puntos abajo en el mes -1, antes de la fractura | IC 95% por bloques de 5 km de la brecha de gas: -27,1 a -3,6; por día efectivo la brecha es -3,4 y su IC incluye cero | no firme, con la regla fijada antes de correr: no pasa la pretendencia |
| Prueba prospectiva (`wiki/hallazgos/prospectiva.md`) | congelada el 2026-11-18 con los datos hasta 2026-09: brecha del mes 1 de -22,9 puntos (intervalo predicho -28,7 a -16,8) y cierre al mes 6, en eventos cuyos meses siguientes no estaban publicados | se puntúa con cada publicación nueva; hacen falta 100 eventos cercanos con el mes medido | se puntúa en cada publicación nueva; el veredicto y el mes de sus datos están en la página (al congelar, pendiente) |
| Suba de la brecha en 2026 (`wiki/hallazgos/carga_anual.md`) | 2026 menos 2021 a 2024, con la misma antigüedad de carga de fracturas en todos los años: -14,7 puntos | IC 95% por bloques de 5 km: -46,2 a 12,7; 195 eventos cercanos de 2026 | no firme, con la regla fijada antes de correr: a los últimos años les faltan fracturas por cargar y el perfil por año no se lee como tendencia. Descriptivo, sin veredicto: con 2025 y 2026 juntos da -22,4 puntos (IC 95%: -42,3 a -2,3) |
| Diferimiento | a los 6 meses la brecha casi se cierra | al mes 12 no hay más padres cercanos bajo el 90% de su trayectoria que controles | sostiene: diferido, no perdido |

## Para un operador

Además del informe (`site/informe.html`):

- Hoja resumen para un operador (qué se ve, qué no se sabe, qué hacer con esto), con cada cifra verificada: `docs/resumen-operador.md`.
- Capa de decisión para un operador: la caída del mes 1, la parte de la brecha de caudal que se cierra a los 6 meses (80 a 91% según el control; quedan 2 a 5 puntos; no es volumen recuperado), el diferido medio por padre (446 a 821 m3 de petróleo en los meses 0 a 6) y una cota de lo que podría no volver (213 m3 por evento), por edad del padre y banda de espaciamiento, con precio y tasa como entradas de quien lo usa; dice qué dato interno resolvería lo que el dato público no resuelve (`wiki/hallazgos/decision_operador.md`).
- Modo con datos propios: el mismo estudio de eventos y el mismo modelo de dosis sobre los CSV de un operador, corrido en su máquina y con un rechazo automático si una ruta cae dentro del repo sin estar ignorada; sobre el dato público reproduce la brecha del mes 1 y sus 2.077 eventos (`docs/operador-datos-propios.md`, `uv run python -m pipeline.local`).

## Cómo correrlo

Hace falta Python 3.13 o más nuevo y [uv](https://docs.astral.sh/uv/). La cadena completa tarda entre diez y quince minutos; los tests, unos tres.

```bash
uv sync
uv run pytest -q                           # tests sobre fixtures chicos
uv run ruff check pipeline agente tests    # lint, el mismo que corre en CI
uv run python -m pipeline.run_all          # toda la cadena con tiempos; --with-ingest, --only a,b, --skip a,b, --list
uv run python -m pipeline.claims           # verifica contra el warehouse las cifras citadas en este README
```

`--with-ingest` descarga unos 150 MB y necesita una red argentina: datos.energia.gob.ar no responde desde fuera del país, así que la actualización corre con `./refresh.sh` desde una máquina en Argentina.
GitHub Actions corre el lint y los tests; `pipeline.claims` necesita el warehouse completo, así que corre en `./refresh.sh` y a mano, no en GitHub Actions (ahí solo se verifican las cifras que salen de archivos versionados).
Demo sin la descarga grande: `make demo` (muestra pequeña; ver `data/muestra/README.md`).
Demo del agente sin modelo: `uv run python -m agente.demo`.
Preguntas con un modelo propio (cualquier endpoint compatible con OpenAI, con `VM_LLM_URL` y `VM_LLM_MODEL`): `uv run python -m agente.router "¿Cuánto petróleo difirió YPF por interferencia en La Amarga Chica?"`.

## Límites

Lo que este estudio no puede decir con dato público, en una línea cada uno. El detalle, con cada cifra verificada, está en [`wiki/hallazgos/limites.md`](wiki/hallazgos/limites.md).

- No se afirma causalidad: es una huella medida contra un control, con una brecha previa a la fractura.
- Datos mensuales y declarados por las operadoras: un cierre preventivo del operador se ve igual que un daño por interferencia, y las cifras pueden rectificarse después.
- Coordenadas de superficie (pads), no la trayectoria de la rama: la dirección de mayor merma no se separa del SHmax publicado ni de cómo se disponen los pads, y no es un hallazgo sobre esfuerzos ni sobre la fractura.
- "Se cierra" a los 6 meses quiere decir menos de 5 puntos y no cero: con 3 de los 4 controles probados el intervalo de la brecha todavía excluye cero.
- Dosis y respuesta: no se ve que la caída del mes 1 crezca con la arena, la presión ni la depleción del padre, pero el efecto mínimo detectable con 80% de potencia y corrección de Holm va de 0,22 a 0,32 desvíos de la caída por desvío de la dosis. Un efecto menor puede pasar inadvertido, y el nulo no dice que no haya golpes de fractura.
- Lado del hijo: el nulo no se lee como ausencia de degradación, porque el control negativo da efecto; la mayor pérdida compatible con el dato público es el límite inferior de su intervalo.
- Por año: a los últimos años les faltan fracturas por cargar, así que el perfil por año no se lee como tendencia.
- Otras cuencas: se corrió en Colorado y en Wyoming con la misma regla fijada de antemano; la lectura conjunta es validez externa de la huella y no una estimación conjunta; el dato público de Colorado no trae arena, etapas ni presión y en Wyoming la fecha del hijo es la primera terminación y no la fractura.
- El modelo de costo no predice un evento puntual: sus coeficientes describen asociaciones en la muestra.

Proyecto personal, no afiliado ni avalado por ninguna empresa.

## Cómo se hizo

Ingesta con hash (raw inmutable por versión), modelo en DuckDB, 29 controles de calidad (los bloqueantes frenan la publicación) y linaje de cada tabla en `wiki/hallazgos/linaje.md`.
Hecho con asistencia de IA; cada cifra de esta página se verifica contra el warehouse con `uv run python -m pipeline.claims` y hay 797 tests.
Preguntas en lenguaje natural sobre 16 operaciones tipadas de solo lectura (`agente/`, también como servidor MCP): exactitud 40/41 en desarrollo y 23/27 en reservadas, con la respuesta correcta calculada sobre el warehouse vigente.

## Decisiones de diseño

- Raw inmutable y direccionado por hash: una corrida sin cambios no escribe nada y se puede reconstruir cualquier semana.
- Reconstrucción completa en vez de incremental: son 430.000 filas y DuckDB las reconstruye en segundos, sin estado que se desincronice.
- Controles en dos niveles: lo que rompe el modelo frena la publicación; lo propio del dato público se mide y se muestra.

Más: `wiki/` (hallazgos, operadoras, áreas, pads y grafo, con el libro de 17 hipótesis con umbral fijo), `docs/arquitectura.md` (el flujo, las decisiones de diseño y qué impide que una cifra se aparte del dato), `docs/proceso/` (decisiones y planes) y `agente/` (operaciones, evaluación y servidor MCP).
