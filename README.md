# Vaca Muerta en datos

Cuando se fractura un pozo nuevo junto a pozos que ya producían, ¿los que ya producían rinden menos? Se contesta con datos públicos de la Secretaría de Energía, en seis preguntas encadenadas: cada una nace de la duda que dejó la anterior. Esta es la versión corta; la larga, con la figura y un caso para recorrer, está en [`site/index.html`](site/index.html).

**¿Le pega al vecino?** *Sostiene, con pretendencia.* Un mes después de fracturar un pozo nuevo, los pozos vecinos a menos de 1 km rinden entre 19 y 23 puntos menos que pozos de control de la misma edad a 2 a 5 km (2.094 eventos). Hay una brecha previa a la fractura (por eso 23 es una cota superior y 19 a 20 el valor descontado).

**¿O es un artefacto del método?** *Sostiene, con pretendencia.* Las fechas falsas y las permutaciones no reproducen la brecha, y una brecha plantada a propósito se recupera. Es una huella medida, no una causa demostrada.

**¿Se pierde o se atrasa?** *Sostiene.* A los 6 meses la brecha casi se cierra: es producción diferida, no perdida. Contra un control de la misma edad el diferido de los meses 0 a 6 va de 6,4 a 11,4 millones de barriles (sin duplicar y descontando la brecha previa hasta el total original).

**¿Por dónde pasa?** *No firme.* El eje de mayor merma, que se publicó como hallazgo, no resistió una validación fuera de tiempo y se retiró como descripción de la muestra. Lo que sí se sostiene es el mecanismo por la geometría de las ramas.

**¿Se puede anticipar o planificar?** *No predice* el costo, *no predice el riesgo* y los dos intentos de planificar quedaron *sin muestra*: pedían más datos de los que hay.

**¿Pasa fuera de Vaca Muerta?** En otras cuencas, con los mismos estimadores y una regla fijada de antemano, la brecha del mes 1 se replica en 1 de 2 cuencas: en la cuenca DJ de Colorado sí y en Wyoming no (tabla de abajo).

**Qué no sabemos.** Si la huella es una propiedad de Vaca Muerta o de cómo se ve el dato público, y qué parte de la brecha previa es efecto anticipado. La prueba prospectiva quedó congelada el 2026-11-18 con los datos hasta 2026-09: hacen falta 100 eventos cercanos con el mes medido y hoy está pendiente.

Contexto: con los datos a octubre de 2026, Vaca Muerta produce unos 709 kbbl/d de petróleo y YPF el 50,5%. En YPF la rama horizontal mediana pasó de unos 1.500 m (cohorte 2017) a 3.316 m (cohorte 2025), mientras el petróleo de 12 meses por metro de rama bajó de 83 a 79 bbl/m: una correlación, no una causa.

Caso de estudio, con figuras y cada cifra verificada: [`docs/caso-interferencia.md`](docs/caso-interferencia.md).

## Result

One month after a new well is fracked, neighbouring wells within 1 km produce 19 to 23 percentage points less than same-age control wells 2 to 5 km away (2,094 events).
By month 6 the gap has almost closed: the oil is deferred, not lost.
In other basins, with the same estimators and a pre-registered rule, the gap one month after the frac replicates in 1 of 2 basins: yes in Colorado's DJ basin, no in Wyoming (table below).
It is a measured footprint that passes placebo and permutation tests, not a demonstrated cause.
The rest of this repository is in Spanish.

## Mirá esto primero

- `docs/caso-interferencia.md`: el caso de estudio, con figuras y cada cifra con su verificación.
- `site/index.html`: el tablero (estático, se abre directo en el navegador).
- `site/replay.html`: la repetición mes a mes de pozos, fracturas y golpes de agua.
- `site/mundo.html`: la cuenca en 3D para recorrer mes a mes. Cada pozo es un punto en su ubicación de superficie sobre una imagen satelital (Sentinel-2, con su fecha en pantalla). Desde el mapa se arma el estudio de eventos, se planta un pozo hijo hipotético y se hacen dos cuentas de física con supuestos propios. Cada elemento dice si es dato, medido o supuesto, y al abrir la página recalcula las respuestas del pipeline.
- `site/globo.html`: el globo de las cuencas. Está oscuro salvo donde un regulador publica petróleo por pozo (lo oscuro es "no publica por pozo", no "no produce"); cada jurisdicción auditada se dibuja con la textura de su nivel. Cada cuenca medida (Vaca Muerta, Colorado, Wyoming) se abre en la misma repetición mes a mes que `mundo.html`, con su veredicto leído de los marts. Se arma con `pipeline/globo.py` y necesita los tres warehouses.
- `site/informe.html`: el informe para un operador (curva del padre, distancia, edad, robustez por operador y área, cierre a 6 meses y calculadora de valor del diferido), armado desde los marts por `pipeline/informe.py`.
- `wiki/hallazgos/interferencia.md`: el hallazgo con su historial por versión de datos.
- `docs/verificacion.md`: cinco preguntas y cómo verificarlas.

## Todos los resultados

| Resultado | Cifra | Intervalo | Veredicto |
| --- | --- | --- | --- |
| Interferencia al mes 1 (padres a menos de 1 km contra controles) | 19 a 23 puntos menos | IC 95% por bloques de 5 km de la brecha de 23: 17 a 30 | sostiene, con pretendencia |
| Eje de mayor merma (cuenca) | 93 grados (E-O) | 70 a 123 grados | regla de parada cumplida: es una descripción de la muestra y ya no se presenta como hallazgo; la dirección no se separa del SHmax publicado (67,5) ni de cómo se disponen pads y ramas (`wiki/hallazgos/eje_parada.md`) |
| Validación del eje fuera de tiempo | 92 grados con datos viejos, 89 en los nuevos | no se separa del SHmax ni de ejes al azar | no firme |
| Mecanismo por la geometría de las ramas (`wiki/hallazgos/mecanismo.md`) | el padre al costado de la rama del hijo contra el de su punta, al mes 1: un contraste de -28,0 puntos sobre 1.201 costados y 915 puntas | IC 95% por bloques de 5 km: -35,9 a -19,7; en el mes -1 da -5,6 puntos (IC -13,9 a 2,5), así que no se separa de cero | sostiene, con la regla fijada antes de correr (commit bddf1e0771): es una huella medida compatible con la geometría de las ramas, no una prueba de causa ni de esfuerzos, y un cierre preventivo del padre al costado da el mismo contraste; el placebo no descarta una diferencia previa de hasta 13,9 puntos (cota superior), y la banda de 0 a 300 m ya da -13,8 en el mes -1; la muestra es sobre todo de 2016 a 2023 |
| Diseño causal con controles aún no tratados (`wiki/hallazgos/causal.md`) | la primera fractura de un hijo a menos de 1 km sube el corte de agua del padre 13,8 puntos porcentuales (447 tratados), pero sin los pozos de YPF no se separa de cero; el petróleo al mes 1 da -25,8 puntos (468 tratados) | IC 95% por bloques de 5 km del corte de agua: 9,5 a 19,9; un cierre de más de medio mes sin hijo cerca sube el corte 3,6 (IC 2,3 a 7,1); del petróleo: -33,9 a -17,9, pero padres nunca tratados con fechas sorteadas ya dan -8,0 (IC -15,2 a -0,5) | con la regla fijada antes de calcular (commit 8f52ff1): el corte de agua cumple la regla de comunicación física causal bajo tendencias paralelas; como es una proporción, también subiría si solo cayera el petróleo, y D3, fijado después ([`causal_profundo.md`](wiki/hallazgos/causal_profundo.md)), muestra que en los días que el padre produce entra agua: su agua por día producido sube 19,5 puntos del líquido de la base (IC 12,8 a 29,2) y su petróleo por día producido no se separa de cero; el volumen de agua del mes no alcanza a separarse de cero (4,8, IC -0,1 a 12,3), y no se midió si es porque el padre pierde días; la dosis, fijada también después, no da gradiente: la cercana menos la lejana da 3,2 puntos porcentuales (IC -3,7 a 10,8) y el tercil de más agua de fractura del hijo menos el de menos da -8,6 (IC -18,9 a 9,4); la suba no se cura en 12 meses (media de los meses 6 a 12, cada mes solo y no el mayor de dos como en D2: 10,9, IC 7,7 a 15,0) y depende de YPF: sin sus pozos da 7,1 con un IC que incluye cero (-0,6 a 18,1) sobre 129 tratados de 447, así que el dato no la muestra fuera de YPF; en Colorado, la cuenca DJ (D7, regla fijada después), el mismo diseño se repite: el corte sube 9,0 puntos porcentuales (IC 6,3 a 12,1, 1.247 tratados) y D3 da el mismo veredicto que en Vaca Muerta; el petróleo no sobrevive a su placebo (M* = 0,62), así que la brecha sigue siendo una huella y no se lee como efecto causal; la persistencia de los meses 7 a 24 queda sin muestra (43 tratados de 200) |
| Modelo de costo de la interferencia | R2 fuera de muestra -0,18 (la media del área da -0,03) | solo el coeficiente de la distancia excluye cero, y por poco | no predice |
| Placebo y permutación | fechas falsas de -2,4 a 0,5 puntos; permutadas de -8,1 a -4,9; real -23,0 | los intervalos de las fechas falsas incluyen cero | sostiene, con pretendencia |
| Sincronía dentro del mes | la brecha del mes 0 cambia -2,1 puntos por cada 0,1 de fracción del mes posterior al inicio de la fractura | IC 95%: -3,3 a -0,8; el mes previo: -0,7 (IC -1,9 a 0,6) | sostiene |
| Lado del hijo (rendimiento de 12 meses cerca de pozos depletados) | muy depletado contra virgen: -0,2 bbl por metro de rama (-0,2% del rendimiento virgen) | IC 95%: -12,6 a 12,2; el control negativo da 8,9 (IC 2,1 a 15,7) y no es nulo | no firme |
| Replicación en Colorado (cuenca DJ) | -19,9 puntos al mes 1; previa de -6,9 en el mes -1 | IC 95% por bloques de 5 km: -27,5 a -14,8 | se replica, con la regla fijada antes de correr; por día producido la brecha es -8,1, cerca de 60% menor |
| Replicación en Wyoming (WOGCC) | -2,5 puntos al mes 1; previa de -11,9 en el mes -1 | IC 95% por bloques de 5 km: -5,5 a 2,2 | no se replica, con la misma regla fijada antes de bajar la producción de Wyoming: el IC incluye cero y la brecha previa es mayor que la del mes 1; el mes 0 es la primera terminación y no la fractura |
| Replicación por cuenca (`wiki/hallazgos/replicacion_cuencas.md`) | se replica en 1 de 2 cuencas: Colorado sí, Wyoming no | sin estimación conjunta ni probabilidad | se publican las dos; con dos cuencas la lectura no separa una huella que depende de la cuenca de ruido distinto en cada una |
| Padre en la ventana de gas (padres gasíferos a menos de 1 km, `wiki/hallazgos/gas.md`) | el padre gasífero cercano da -12,6 puntos de gas al mes 1, pero ya va -7,2 puntos abajo en el mes -1, antes de la fractura | IC 95% por bloques de 5 km de la brecha de gas: -27,1 a -3,8; por día efectivo la brecha es -3,4 y su IC incluye cero | no firme, con la regla fijada antes de correr: no pasa la pretendencia |
| Prueba prospectiva (`wiki/hallazgos/prospectiva.md`) | congelada el 2026-11-18 con los datos hasta 2026-09: brecha del mes 1 de -22,9 puntos (intervalo predicho -28,7 a -16,8) y cierre al mes 6, en eventos cuyos meses siguientes no estaban publicados | se puntúa con cada publicación nueva; hacen falta 100 eventos cercanos con el mes medido | se puntúa en cada publicación nueva; el veredicto y el mes de sus datos están en la página (al congelar, pendiente) |
| Suba de la brecha en 2026 (`wiki/hallazgos/carga_anual.md`) | 2026 menos 2021 a 2024, con la misma antigüedad de carga de fracturas en todos los años: -15,1 puntos | IC 95% por bloques de 5 km: -43,5 a 10,9; 212 eventos cercanos de 2026 | no firme, con la regla fijada antes de correr: a los últimos años les faltan fracturas por cargar y el perfil por año no se lee como tendencia. Descriptivo, sin veredicto: con 2025 y 2026 juntos da -21,5 puntos (IC 95%: -40,7 a -5,4) |
| Diferimiento | a los 6 meses la brecha casi se cierra | al mes 12 no hay más padres cercanos bajo el 90% de su trayectoria que controles | sostiene: diferido, no perdido |
| Golpes en el mismo mes con el padre como su propio control (`wiki/hallazgos/golpes_mismo_padre.md`) | solo se puede identificar con padres que tuvieron dos meses de golpe aislados con distinta cantidad de hijos: 87 padres y 197 meses de golpe en Vaca Muerta y 19 padres y 38 meses en Colorado | no hay intervalo que valga con tan pocos pads del padre en el bootstrap | sin muestra, con la regla fijada antes de correr: pedía 150 padres y 400 meses de golpe, así que el dato no decide si agrupar hijos le cuesta menos al padre |
| Calendario de golpes: matrices de costo, calendario óptimo y backtest ajustado en 2023 (`wiki/hallazgos/calendario_golpes.md`) | descriptivo, no una recomendación al operador: con el ajuste de 2023 el modelo de costo fijo más hijo predice peor que el aditivo, en la estimación puntual, en 344 eventos aislados de 2024 a 2026: D = -0,13 (habilidad del fijo menos la del aditivo; con el ajuste de 2023 el costo fijo se acota en cero) | IC 95% por pads del padre: -2,86 a 0,03; descriptivo, el arrepentimiento del calendario observado contra el óptimo, con el ajuste de toda la muestra y b acotado en cero, es una cota superior: 3.197 días de base (IC 95%: 0 a 8.034) | sin muestra, con la regla fijada antes de correr: pedía 100 eventos aislados en 2023 y hay 81, así que el dato no decide si conviene reagrupar el calendario |
| Lado del hijo dentro del pad (hijos del mismo pad según las ramas a menos de 600 m, `wiki/hallazgos/hijo_pad.md`) | pendiente dentro del pad: 0,1 bbl por metro de rama por cada 100 bbl por metro de exposición previa, sobre 850 hijos de 234 pads, todos fracturados de 2016 a 2023, así que no habla de los hijos recientes | IC 95%: -0,8 a 1,1; cota superior de la pérdida: 0,9% del rendimiento virgen por cada 100 bbl por metro; el control negativo da 0,3 (IC 95%: -0,1 a 0,9) | no se ve degradación, con la regla fijada antes de correr; la exposición cuenta solo ramas medidas, así que la pendiente se atenúa hacia cero y no es que no haya degradación |
| Alcance y dilución de la huella entre ramas (`wiki/hallazgos/alcance_rama.md`) | alcance medido hasta 1.000 m entre ramas: la brecha del mes 1 es de -50,3 puntos a menos de 300 m, -20,5 de 300 a 600 m, -9,0 de 600 a 1.000 m y -1,5 de 1.000 a 2.000 m, sobre 10.173 eventos con las dos ramas medidas | IC 95% por bloques de 5 km a menos de 300 m: -60,2 a -40,4; la dilución (A menos B) da -4,1 puntos (IC 95%: -11,7 a 2,7) | alcance medido; la distancia de superficie no se separa de la de ramas; el control de superficie está contaminado (los controles con la rama a menos de 1.000 m rinden 7,8 puntos menos); con la regla fijada antes de correr (commit `76d9831`). La muestra es sobre todo de hijos fracturados de 2016 a 2023: las trayectorias cubren el 86% de esos hijos pero el 39% de los de 2024 y el 25% de los de 2025 |
| Riesgo de golpe fuerte con un modelo logístico probado hacia adelante (`wiki/hallazgos/riesgo.md`) | en la prueba de 2023 y 2024, sobre 492 eventos cercanos, el AUC es 0,67 y la habilidad de Brier contra la tasa de entrenamiento por área es 0,09 | IC 95% por pads de hijo del AUC: 0,60 a 0,74; de la habilidad de Brier: -0,04 a 0,21 | no predice el riesgo, con la regla fijada antes de correr (commit `4b19b90`): el AUC pasa el umbral pero la habilidad de Brier no excluye cero. La muestra es sobre todo de hijos fracturados de 2016 a 2023: las trayectorias cubren el 86% de esos hijos pero el 39% de los de 2024 y el 25% de los de 2025 |
| Dosis con la geometría de las ramas, detrás de una puerta de potencia (`wiki/hallazgos/dosis_geometria.md`) | con los padres a menos de 600 m entre ramas (464 eventos de 134 pads hijo) el menor MDE80 con Holm es de 0,34 desvíos de la caída por desvío de la dosis, contra 0,22 de la muestra completa | el mayor MDE80 con Holm es de 0,52; la simulación de planta y recupera no valida la cuenta analítica, que resulta optimista en esa simulación (la causa no está medida) | la geometría no da más potencia, con la regla fijada antes de correr (commit `59b3a26`): no se corrió el modelo de dosis y no se publica ningún coeficiente; no dice que no haya dosis y respuesta. La muestra es sobre todo de hijos fracturados de 2016 a 2023: las trayectorias cubren el 86% de esos hijos pero el 39% de los de 2024 y el 25% de los de 2025 |

## Para un operador

Además del informe (`site/informe.html`):

- Hoja resumen para un operador (qué se ve, qué no se sabe, qué hacer con esto), con cada cifra verificada: `docs/resumen-operador.md`.
- Capa de decisión para un operador (`wiki/hallazgos/decision_operador.md`): la caída del mes 1, la parte de la brecha de caudal que se cierra a los 6 meses (80 a 91% según el control; quedan 2 a 5 puntos; no es volumen recuperado), el diferido medio por padre (485 a 869 m3 de petróleo en los meses 0 a 6) y una cota de lo que podría no volver (103 m3 por evento), por edad del padre y banda de espaciamiento. El precio y la tasa los pone quien la usa. Dice qué dato interno resolvería lo que el dato público no resuelve.
- Modo con datos propios: el mismo estudio de eventos y el mismo modelo de dosis sobre los CSV de un operador, corrido en su máquina y con un rechazo automático si una ruta cae dentro del repo sin estar ignorada; sobre el dato público de septiembre de 2026 reproduce la brecha del mes 1 y sus 2.077 eventos (validación sin repetir con los datos de octubre) (`docs/operador-datos-propios.md`, `uv run python -m pipeline.local`).

## Cómo correrlo

Hace falta Python 3.13 o más nuevo y [uv](https://docs.astral.sh/uv/). La cadena completa tarda entre diez y quince minutos; los tests, unos tres.

```bash
uv sync
uv run pytest -q                           # tests sobre fixtures chicos
uv run ruff check pipeline agente tests    # lint, el mismo que corre en CI
uv run python -m pipeline.run_all          # toda la cadena con tiempos; --with-ingest, --only a,b, --skip a,b, --list
uv run python -m pipeline.claims           # verifica contra el warehouse las cifras citadas en este README
```

`--with-ingest` descarga unos 190 MB y necesita una red argentina: datos.energia.gob.ar no responde desde fuera del país, así que la actualización corre con `./refresh.sh` desde una máquina en Argentina.
GitHub Actions corre el lint y los tests; `pipeline.claims` necesita el warehouse completo, así que corre en `./refresh.sh` y a mano, no en GitHub Actions (ahí solo se verifican las cifras que salen de archivos versionados).
Demo sin la descarga grande: `make demo` (muestra pequeña; ver `data/muestra/README.md`).
Demo del agente sin modelo: `uv run python -m agente.demo`.
Preguntas con un modelo propio (cualquier endpoint compatible con OpenAI, con `VM_LLM_URL` y `VM_LLM_MODEL`): `uv run python -m agente.router "¿Cuánto petróleo difirió YPF por interferencia en La Amarga Chica?"`.

## Límites

Lo que este estudio no puede decir con dato público. Los primeros límites tienen su detalle, con cada cifra verificada, en [`wiki/hallazgos/limites.md`](wiki/hallazgos/limites.md); los de las pruebas más nuevas (alcance, riesgo, dosis con geometría, calendario) se leen solo acá.

- No se afirma causalidad sobre el petróleo: es una huella medida contra un control, con una brecha previa a la fractura. Con controles que también van a recibir un hijo cerca, pero más tarde, la caída no sobrevive a su placebo ([`wiki/hallazgos/causal.md`](wiki/hallazgos/causal.md)). La única afirmación causal es la suba del corte de agua, y es causa bajo supuestos nombrados (tendencias paralelas, que no se prueban después de la fractura, y un placebo de cierre que la acota), no un hecho físico medido ni nuevo (la literatura de golpes de fractura ya trata la respuesta del padre como señal de interferencia; lo nuevo es el diseño sobre dato público de toda la cuenca): el corte de agua sube si entra agua o si el petróleo cae más que el agua; D3, fijado después, dice que entra agua en los días que el padre produce, aunque el volumen del mes no alcanza a separarse de cero, y no se midió si es porque el padre pierde días; el corte no sube más con el hijo más cerca ni más grande (la dosis, fijada después, no da gradiente); la suba no se cura en 12 meses, y depende de YPF: sin sus pozos da 7,1 puntos porcentuales con un IC que incluye cero (-0,6 a 18,1, 129 tratados), así que no se lee como un efecto de toda la cuenca; y solo cuenta la primera fractura a menos de 1 km de cada padre.
- Datos mensuales y declarados por las operadoras: un cierre preventivo del operador se ve igual que un daño por interferencia, y las cifras pueden rectificarse después.
- Coordenadas de superficie (pads), no la trayectoria de la rama: la dirección de mayor merma no se separa del SHmax publicado ni de cómo se disponen los pads, y no es un hallazgo sobre esfuerzos ni sobre la fractura. Las trayectorias publicadas se cargan aparte, solo para describir su cobertura y la distancia entre ramas: [`wiki/hallazgos/trayectorias.md`](wiki/hallazgos/trayectorias.md). Con ellas se probó aparte la posición del padre respecto de la rama del hijo (costado o punta), en `wiki/hallazgos/mecanismo.md`: mide una huella de geometría, no esfuerzos, y la muestra es sobre todo de 2016 a 2023.
- "Se cierra" a los 6 meses quiere decir menos de 5 puntos y no cero: con 3 de los 4 controles probados el intervalo de la brecha todavía excluye cero.
- Dosis y respuesta: no se ve que la caída del mes 1 crezca con la arena, la presión ni la depleción del padre, pero el efecto mínimo detectable con 80% de potencia y corrección de Holm va de 0,22 a 0,31 desvíos de la caída por desvío de la dosis. Un efecto menor puede pasar inadvertido, y el nulo no dice que no haya golpes de fractura.
- Lado del hijo: el nulo no se lee como ausencia de degradación, porque el control negativo da efecto; la mayor pérdida compatible con el dato público es el límite inferior de su intervalo.
- Lado del hijo dentro del pad: la exposición cuenta solo ramas medidas, así que es una cota inferior y la pendiente se atenúa hacia cero; "no se ve degradación" no es "no hay degradación", y dentro del pad la exposición es en parte el orden de las fracturas y no solo depleción.
- Alcance entre ramas: el alcance es el borde de las bandas probadas (300, 600, 1.000 y 2.000 m) y no un borde exacto; la muestra son los pares con las dos ramas medidas y es sobre todo de 2016 a 2023, así que no dice nada de los hijos recientes; el control lateral solo conoce ramas publicadas; la distancia es en planta, sin la cota; el recálculo del diferido de esa página no es el rango del estudio y solo compara un control con el otro.
- Riesgo de golpe fuerte: el "no predice el riesgo" es contra estas variables y un modelo logístico sin ajuste, entrenado con cientos de eventos, y no prueba que nada prediga el riesgo; los intervalos cubren el muestreo de la prueba y no el del entrenamiento; la muestra es sobre todo de 2016 a 2023 y no dice nada de los hijos recientes.
- Dosis con la geometría de las ramas: la puerta de potencia no pasó (el menor MDE80 con Holm es de 0,34 desvíos contra 0,22), así que no se corrió el modelo de dosis sobre los padres cercanos entre ramas; la muestra es sobre todo de 2016 a 2023, no incluye padres con la rama cercana pero la boca a 1 km o más, y la cuenta analítica de potencia es optimista frente a la simulación (la causa no está medida; puede ser en parte la resolución del bootstrap de la simulación).
- Por año: a los últimos años les faltan fracturas por cargar, así que el perfil por año no se lee como tendencia.
- Otras cuencas: se corrió en Colorado y en Wyoming con la misma regla fijada de antemano; la lectura conjunta es validez externa de la huella y no una estimación conjunta; el dato público de Colorado no trae arena, etapas ni presión y en Wyoming la fecha del hijo es la primera terminación y no la fractura.
- El modelo de costo no predice un evento puntual: sus coeficientes describen asociaciones en la muestra.
- Calendario de golpes: el optimizador mueve hijos entre meses solo dentro del modelo y solo del lado del padre; con «sin muestra» sus cifras son descriptivas, el arrepentimiento con b acotado en cero es una cota superior y no una estimación, y suma el costo de meses que en su mayoría no son aislados.

Proyecto personal, no afiliado ni avalado por ninguna empresa.

## Cómo se hizo

Ingesta con hash (raw inmutable por versión), modelo en DuckDB, 29 controles de calidad (los bloqueantes frenan la publicación) y linaje de cada tabla en `wiki/hallazgos/linaje.md`.
Hecho con asistencia de IA; cada cifra de esta página se verifica contra el warehouse con `uv run python -m pipeline.claims` y hay 1228 tests.
Preguntas en lenguaje natural sobre 16 operaciones tipadas de solo lectura (`agente/`, también como servidor MCP): exactitud 40/41 en desarrollo y 23/27 en reservadas, con la respuesta correcta calculada sobre el warehouse vigente.

## Decisiones de diseño

- Raw inmutable y direccionado por hash: una corrida sin cambios no escribe nada y se puede reconstruir cualquier semana.
- Reconstrucción completa en vez de incremental: son 436.308 filas y DuckDB las reconstruye en segundos, sin estado que se desincronice.
- Controles en dos niveles: lo que rompe el modelo frena la publicación; lo propio del dato público se mide y se muestra.

Más: `wiki/` (hallazgos, operadoras, áreas, pads y grafo, con el libro de 17 hipótesis con umbral fijo), `docs/arquitectura.md` (el flujo, las decisiones de diseño y qué impide que una cifra se aparte del dato), `docs/proceso/` (decisiones y planes) y `agente/` (operaciones, evaluación y servidor MCP).

## Licencia

El código y los textos de este repositorio usan la licencia MIT ([LICENSE](LICENSE)). Los datos de terceros conservan los términos de su fuente; la atribución de cada una está en [ATRIBUCION.md](ATRIBUCION.md).
