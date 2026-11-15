# Vaca Muerta en datos

Pipeline reproducible sobre los datos abiertos de la Secretaría de Energía de Argentina (producción mensual por pozo no convencional y datos de fractura): ingesta con hash, modelo en DuckDB, controles de calidad publicados y un tablero estático. Con los datos a septiembre de 2026, Vaca Muerta produce unos 698 kbbl/d de petróleo y YPF el 50%. En YPF la rama horizontal mediana pasó de unos 1.500 m (cohorte 2017) a 3.200 m (cohorte 2025), mientras el petróleo de 12 meses por metro de rama bajó de 83 a 77 bbl/m: una correlación, no una causa.

Caso de estudio, con figuras y cada cifra verificada: [`docs/caso-interferencia.md`](docs/caso-interferencia.md).

## Resultado

Un mes después de fracturar un pozo nuevo, los pozos vecinos a menos de 1 km rinden entre 19 y 23 puntos menos que pozos de control de la misma edad a 2 a 5 km (2.077 eventos).
A los 6 meses la brecha casi se cierra: es producción diferida, no perdida.
Contra un control de la misma edad el diferido de los meses 0 a 6 va de 5,8 a 10,7 millones de barriles (sin duplicar y descontando la brecha previa hasta el total original), y la brecha del mes 1 llega a 44 puntos en 2026.
Es una huella medida y sometida a pruebas de placebo y permutación, no una causa demostrada: hay una brecha previa a la fractura
(por eso 23 es una cota superior y 19 a 20 el valor descontado).

## Result

One month after a new well is fracked, neighbouring wells within 1 km produce 19 to 23 percentage points less than same-age control wells 2 to 5 km away (2,077 events).
By month 6 the gap has almost closed: the oil is deferred, not lost.
Against a same-age control the deferral over months 0 to 6 ranges from 5.8 to 10.7 million barrels (de-duplicated and net of the pre-frac gap, up to the original total), and the month-1 gap reaches 44 points in 2026.
This is a measured footprint that passes placebo and permutation tests, not a demonstrated cause: there is a gap before the frac
(so 23 is an upper bound and 19 to 20 is the discounted value).

## Mirá esto primero

- `docs/caso-interferencia.md`: el caso de estudio, con figuras y cada cifra con su verificación.
- `site/index.html`: el tablero (estático, se abre directo en el navegador).
- `site/replay.html`: la repetición mes a mes de pozos, fracturas y golpes de agua.
- `wiki/hallazgos/interferencia.md`: el hallazgo con su historial por versión de datos.
- `docs/verificacion.md`: cinco preguntas y cómo verificarlas.

## Resultados y veredicto

| Resultado | Cifra | Intervalo | Veredicto |
| --- | --- | --- | --- |
| Interferencia al mes 1 (padres a menos de 1 km contra controles) | 19 a 23 puntos menos | IC 95% de la brecha de 23: 18 a 27 | sostiene, con pretendencia |
| Eje de mayor merma (cuenca) | 93 grados (E-O) | 70 a 122 grados | no firme: no se separa del SHmax publicado (67,5) |
| Validación del eje fuera de tiempo | 92 grados con datos viejos, 88 en los nuevos | no se separa del SHmax ni de ejes al azar | no firme |
| Modelo de costo de la interferencia | R2 fuera de muestra -0,15 (la media del área da 0,01) | ningún coeficiente excluye cero | no predice |
| Placebo y permutación | fechas falsas de -2,4 a 0,6 puntos; permutadas de -8,4 a -4,8; real -22,9 | los intervalos de las fechas falsas incluyen cero | sostiene, con pretendencia |
| Sincronía dentro del mes | la brecha del mes 0 cambia -2,1 puntos por cada 0,1 de fracción del mes posterior al inicio de la fractura | IC 95%: -3,1 a -1,0; el mes previo: -0,7 (IC -1,8 a 0,5) | sostiene |
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
- Datos mensuales: un cierre preventivo del operador se ve igual que un daño por interferencia.
- No se afirma causalidad: es una huella medida contra un control, con una brecha previa a la fractura.
- El eje de mayor merma no es una medición de esfuerzos; los ejes de las áreas chicas dependen de pocos pads.
- El modelo de costo no predice un evento puntual: sus coeficientes describen asociaciones en la muestra.
- Datos públicos declarados por las operadoras; pueden rectificarse después.
- Proyecto personal, no afiliado ni avalado por ninguna empresa.

## Cómo se hizo

Ingesta con hash (raw inmutable por versión), modelo en DuckDB, 28 controles de calidad (los bloqueantes frenan la publicación) y linaje de cada tabla en `wiki/hallazgos/linaje.md`.
Hecho con asistencia de IA; cada cifra de esta página se verifica contra el warehouse con `uv run python -m pipeline.claims` y hay 246 tests.
Preguntas en lenguaje natural sobre 16 operaciones tipadas de solo lectura (`agente/`, también como servidor MCP): exactitud 40/41 en desarrollo y 23/27 en reservadas, con la respuesta correcta calculada sobre el warehouse vigente.

## Decisiones de diseño

- Raw inmutable y direccionado por hash: una corrida sin cambios no escribe nada y se puede reconstruir cualquier semana.
- Reconstrucción completa en vez de incremental: son 430.000 filas y DuckDB las reconstruye en segundos, sin estado que se desincronice.
- Controles en dos niveles: lo que rompe el modelo frena la publicación; lo propio del dato público se mide y se muestra.

Más: `wiki/` (hallazgos, operadoras, áreas, pads y grafo, con el libro de seis hipótesis con umbral fijo), `docs/proceso/` (arquitectura, decisiones y planes) y `agente/` (operaciones, evaluación y servidor MCP).
