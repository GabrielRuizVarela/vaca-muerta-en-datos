# Cinco preguntas y cómo verificarlas

Las cinco preguntas que haría un revisor externo de ingeniería de datos, dónde las responde el repo y cómo se verifica cada respuesta. Después, qué muestra el proyecto, qué es riguroso, qué se midió y qué es limitado.

## Las cinco preguntas y dónde las responde el repo

1. **¿Cómo sé que el número de hoy sale del dato de hoy?** Manifiesto con hash, raw por versión, y el libro de hallazgos guarda el hash de datos de cada evaluación. README, sección Decisiones de diseño, y `docs/proceso/decisiones.md`.
2. **¿Es causal?** No: es una huella medida contra un control de la misma edad. README, secciones Resultado y Límites, y `wiki/hallazgos/placebo.md`.
3. **¿La dirección coincide con los esfuerzos conocidos?** Compara contra el SHmax publicado y dice que los datos no lo separan. `wiki/hallazgos/anisotropia.md` y `robustez.md`.
4. **¿Qué pasa con más volumen o más frecuencia?** 430.000 filas se reconstruyen en segundos; el paso natural es particionar por mes y cargar solo los meses rectificados. `docs/proceso/decisiones.md`. Pendiente: cómo convivirían trayectorias de rama, si la operadora las tiene.
5. **¿Cómo se evita que el agente invente?** Operaciones tipadas con argumentos validados, conexión de solo lectura, abstención ante lo que no está en los datos, y una evaluación que sigue valiendo después de cada actualización. `agente/` y `agente/eval/`.

## Cómo se verifica cada respuesta

| Pregunta | Qué se ejecuta | Qué debería pasar |
| --- | --- | --- |
| 1. El número de hoy sale del dato de hoy | `uv run python -m pipeline.claims` y `wiki/hallazgos/linaje.md` | todas las verificaciones en PASS contra el warehouse; el linaje muestra de qué tabla cruda sale cada cifra |
| 2. Causalidad | `uv run python -m pipeline.placebo` (y `wiki/hallazgos/placebo.md`) | Fechas falsas y permutación pasan; la pretendencia existe y la página lo dice |
| 3. Dirección contra los esfuerzos | `uv run python -m pipeline.validacion` (y `wiki/hallazgos/validacion.md`) | Eje estable de 82 a 93 grados pero no firme; no se separa del SHmax |
| 4. Más volumen o frecuencia | `uv run python -m pipeline.run_all` | Cadena completa con tiempos por paso; solo la ingesta toca la red (`--with-ingest`) |
| 5. El agente no inventa | `uv run python -m agente.eval.run --split holdout` y `uv run pytest tests/test_agente.py -q` | Argumentos validados, solo lectura, abstención ante lo que no está en los datos; 23/27 en reservadas con `nemotron-3.5-super` (no el modelo local) |

Todo: `uv run pytest -q` (todos los tests en verde) y `uv run ruff check pipeline agente tests`.

## Qué muestra

- **Pipeline reproducible.** Ingesta de los datos abiertos de la Secretaría de Energía (431.322 filas de producción mensual por pozo y la fractura asociada) con GET condicional, SHA-256 y raw inmutable por versión. Reconstrucción completa en DuckDB, idempotente: dos corridas seguidas el mismo día dan wiki, repetición y reporte de calidad idénticos byte a byte (el control de frescura guarda la fecha de la corrida) (hay tests automáticos del build, de los marts de costo y de robustez, del árbol del wiki, del sitio y de la repetición).
- **Controles de calidad en dos niveles.** 28 controles: los que rompen el modelo frenan el build (0 fallidos hoy) y los propios del dato público se miden y se publican en el sitio. `wiki/hallazgos/linaje.md` lista de qué tabla cruda sale cada tabla derivada.
- **Un comando.** `uv run python -m pipeline.run_all` corre build, costo, robustez, validación, placebo, wiki, sitio, repetición y verificación de cifras, con tiempos, y se detiene en el primer fallo. CI corre los tests y el lint.
- **Estudio de eventos.** 2.077 fracturas de un pozo nuevo a menos de 1 km de un padre que producía, contra padres de control de la misma edad a 2 a 5 km. Un mes después el padre cercano rinde entre 19 y 23 puntos menos que el control (23 es el valor bruto y una cota superior; 19 descuenta la brecha previa a la fractura); a los 6 meses la brecha casi se cierra. Son entre 5,8 y 10,7 millones de barriles diferidos contra el control de la misma edad (sin duplicar y descontando la brecha previa hasta el total original); el reparto por operadora (por evento, no como parte del total) no se lee como una comparación de desempeño. Es diferimiento, no pérdida: la fracción de padres que no se recupera a los 12 meses no supera a la de los controles.
- **Registro de eventos** por pozo (fractura, primera producción, cambios de estado y de extracción, cierres, saltos de agua, quiebres de caudal) y **libro de hallazgos**: quince hipótesis con umbral fijo, reevaluadas con cada dato nuevo y registradas en un CSV versionado.
- **Agente con 16 operaciones tipadas de solo lectura** (también como servidor MCP). Un modelo local elige la operación y los argumentos; nunca escribe SQL ni números; cada respuesta cita tablas, mes de datos y hash del archivo. Evaluación con preguntas de desarrollo y reservadas, con la respuesta correcta calculada sobre el warehouse vigente: 40/41 y 23/27 en la última medición (2026-11-15), hecha con `nvidia/nemotron-3.5-super-vl-120b-a12b` y no con el modelo local; la medición anterior con `qwen3.5-35b-a3b` local, sobre el set previo a las preguntas de dos operaciones, fue 27/27 y 15/16.
- **Repetición mes a mes** (`site/replay.html`), wiki y grafo con aristas bitemporales.

## Qué es riguroso

Raw inmutable y controles publicados. Intervalos por bootstrap de pads hijo, test de permutación por bloques, eje estimado fuera de muestra en el modelo de costo (lo corrigió una revisión). Un análisis de robustez en 13 subconjuntos que se publica aunque debilite el resultado. Las cifras del README y del tablero se verifican contra el warehouse con `pipeline.claims` (todas pasan hoy). Los límites están escritos en el README.

## Qué se midió después, y qué dijo (los tres resultados incómodos están publicados)

- **Validación del eje este-oeste** (`wiki/hallazgos/validacion.md`). El punto estimado es estable: 92 grados con los eventos viejos, 88 con los nuevos y 82 con el corte de agua como resultado alternativo. Pero no es firme: solo el salto del corte de agua deja un eje definido, ningún grupo de años lo define, y el eje de los eventos viejos no predice mejor los nuevos que el SHmax publicado o un eje al azar (mejoras de menos de 1% de la suma de cuadrados).
- **Modelo de costo con validación cruzada** (`pipeline/costo.py`, `mart_costo_cv`). Fuera de muestra no le gana a predecir la media (R2 de unos -0,15 contra -0,00 y 0,01; el error absoluto es parecido) y el término del ángulo no agrega nada. Da un intervalo del 80% desde los residuos fuera de muestra (por ejemplo, el padre p165347: 232.720 bbl, de 174.725 a 399.391), que supone errores independientes entre padres.
- **Placebo y pretendencia** (`wiki/hallazgos/placebo.md`). Las fechas falsas y la permutación pasan, pero los padres cercanos ya rendían menos antes de la fractura (-2,5, -3,5 y -6,3 puntos en los meses -3, -2 y -1). Los 23 puntos son una cota superior: contra ese nivel previo la caída adicional al mes 1 es de 19 a 20 puntos, si la brecha previa es un nivel y no un efecto anticipado (los datos mensuales no lo separan).

## Qué es limitado

- Coordenadas de superficie, sin trayectoria de la rama: no se mide el espaciamiento real ni la pérdida del pozo hijo.
- Datos mensuales: un cierre preventivo y un golpe de interferencia se ven igual.
- Eje de mayor merma: unos 93 grados (IC 70 a 122), consistente en los subconjuntos pero no firme (sin Loma Campana deja de estar definido). No se puede afirmar que difiera del SHmax publicado (unos 67,5). No es una medición de esfuerzos.
- El modelo de costo no le gana a la media fuera de muestra y ningún factor tiene un intervalo que excluya cero.
- Los 23 puntos incluyen una brecha previa a la fractura (ver arriba).
- Datos públicos declarados por las operadoras; pueden rectificarse. Proyecto personal, no afiliado a ninguna empresa.
