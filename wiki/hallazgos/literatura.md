# Comparación con la literatura

Página escrita a mano (no la genera el pipeline). Pone las cifras de este proyecto al lado de las publicadas sobre interferencia entre pozos padre e hijo. Cada cifra propia se verifica contra el warehouse con `uv run python -m pipeline.claims`; cada cifra ajena dice de dónde sale y hasta dónde se leyó la fuente.

Cómo leer la tabla: casi ningún trabajo publicado mide lo mismo que este. Acá la unidad es el evento (un padre y el mes de fractura de su hijo más cercano), el resultado es el caudal mensual del padre contra controles de la misma cuenca y la fuente es el dato público mensual. Los trabajos de la industria miden presión de boca de pozo, EUR simulado o curvas de producción diaria de un operador. Las comparaciones son de orden de magnitud y de forma, no de igualdad.

## Fuentes y qué dicen

Rótulo de cada fuente: **resumen** (se leyó solo el resumen publicado), **artículo** (se leyó el texto), **nota** (se leyó una nota de prensa técnica que cita el trabajo; la cifra no se verificó en el original).

### Estados Unidos

- **Eagle Ford, Bakken, Haynesville, Niobrara y Woodford.** Miller, Lindsay, Baihly y Xu, "Parent Well Refracturing: Economic Safety Nets in an Uneconomic Market", SPE 180200 (2016). Resumen: más de 3.100 interferencias en cinco cuencas; en Haynesville y Bakken hay más golpes positivos que en las otras, y en Woodford y Niobrara la mayoría son negativos. Nota: un caso de estudio publicado en JPT cita que, en 1.210 casos del Eagle Ford, el padre tuvo un evento negativo de producción en alrededor del 41% de las veces. Rótulo: resumen y nota.
- **Midland Basin (condado de Reagan, Texas).** Presentación de 2019 sobre 47 pozos horizontales y 17 trabajos de fractura multipozo. Nota: concluye que los golpes no son un riesgo significativo para el petróleo del padre en esa zona; los efectos son sobre todo más agua y menos GOR y suelen ser temporarios (semanas a meses), y la mayor caída fue en el gas diario del padre, por un tiempo. Rótulo: nota.
- **Bakken.** Min y otros (EERC), URTeC 3862589 (2023), sobre datos de unos 17.000 pozos. Nota (JPT, agosto de 2023): en el Bakken los golpes suelen subir la producción del padre; el impacto en el hijo va de -15,4% con menos de 400 pies de espaciamiento a +0,6% con más de 1.200 pies si el padre no se refracturó (de -9% a +5% si se refracturó). Rótulo: nota.
- **Simulación (Permian).** Estudio de SLB citado en JPT (octubre de 2017): hijos simulados a 1.320 pies del padre producen alrededor de 5% menos petróleo acumulado a 5 años que el padre, y a 660 pies, alrededor de 24% menos. Rótulo: nota.

### Vaca Muerta

- **Lerza, Cuervo y Malhotra**, "Closing the Gap in Characterizing the Parent Child Effect for Unconventional Reservoirs: A Case of Study in Vaca Muerta Shale Formation", SPE 206001 (2021). Resumen: usa conceptos de inferencia causal de ensayos clínicos (equilibrio de covariables entre grupos) sobre datos reales; el espaciamiento, el momento de producción del padre y el diseño de ambos pozos cambian mucho el efecto sobre el EUR del hijo. Rótulo: resumen.
- **Cruz, Weimann y Ratcliff**, "Sensitivity analysis of the main variables affecting the EUR response under parent-child effect", URTeC 3969293 (LA URTeC 2023). Artículo (resumen e introducción): simulación acoplada de fractura y reservorio en el núcleo de petróleo de Vaca Muerta, con espaciamientos de 200, 300, 400 y 600 m y 0 a 5 años de depleción del padre; el EUR del hijo mejora con la distancia y a 600 m no se ve efecto con un solo hijo. Rótulo: artículo.
- **SLB, SPE 191836** (2018), "When, Where, and How to Drill and Complete Pads of Multiple Wells? Four-Dimensional Considerations for Field Development in the Vaca Muerta Shale". Resumen: modelo físico de interferencia para proponer espaciamiento y calendario de perforación de pads; la interferencia trae pérdida de producción. Rótulo: resumen.
- **Mamaní, Rosemblat y Álvarez Castillo (YPF)**, "Evaluación de frac-hits y su impacto en Loma Campana", Petrotecnia 4-2023 (IAPG). Artículo: detectan frac-hits por la presión del padre cerrado durante la fractura del hijo; la intensidad del golpe baja desde unos 370 m entre pozos; en los hijos analizados (padre a 240 a 400 m) las pérdidas superan el 20% de la productividad esperada; el análisis vale para Loma Campana y no necesariamente para toda la formación; dejan para una fase siguiente la producción del padre después del golpe. Rótulo: artículo.
- **YPF, fibra óptica descartable** (EconoJournal, junio de 2025). Nota: 27 etapas monitoreadas y 40 eventos de frac-hit identificados. No da pérdidas de producción. Rótulo: nota.
- **Pan American Energy** (Oil & Gas Journal, noviembre de 2023, que cita URTeC 3839771, 3866768 y 3861789). Nota: con desarrollo de relleno los hijos rindieron menos de lo esperado; un piloto mejoró la recuperación del hijo presurizando el padre durante la fractura del hijo; en otra zona los niveles de aterrizaje escalonados redujeron los golpes tempranos. Rótulo: nota.

## Nuestras cifras al lado

| Pregunta | Literatura (rótulo) | Este proyecto (dato público mensual, toda la cuenca) |
| --- | --- | --- |
| ¿Qué parte de los padres cercanos tiene una caída? | Eagle Ford: alrededor de 41% de 1.210 casos con evento negativo (nota). | Descriptivo, agregado para esta página después de leer la literatura (post hoc, sin regla fijada antes): el 55,8% de 2.090 eventos cercanos con los meses 0 y 1 tiene un índice medio menor que 0,75 en esos dos meses, contra el 30,9% de 18.288 eventos de control. La definición no es la de la industria y el umbral es arbitrario; lo comparable es el exceso sobre los controles, no la cifra sola. |
| ¿Cuánto cae el padre al mes siguiente? | No hay una cifra de cuenca comparable en las fuentes leídas. | Padres a menos de 1 km: entre 19 y 23 puntos menos que controles de 2 a 5 km un mes después de la fractura del hijo (2.094 eventos), con una brecha previa a la fractura que hace de 23 una cota superior ([interferencia.md](interferencia.md)). |
| ¿Es temporario? | Midland (Reagan): sobre todo temporario, semanas a meses (nota). OGJ (Vaca Muerta, un pad): las conexiones bajan después de 6 meses (nota). | A los 6 meses la brecha queda dentro de 5 puntos con los cuatro controles probados (de -2,1 a -4,8); "se cierra" quiere decir menos de 5 puntos y no cero. |
| ¿Puede subir la producción del padre? | Bakken: a menudo sube (nota). Haynesville y Bakken: más golpes positivos (resumen). | En la mediana los padres cercanos caen; este trabajo no mide la parte de eventos con subida. |
| ¿Cuánto pierde el hijo? | Bakken: de -15,4% a +0,6% según espaciamiento (nota). Simulación: 5% a 1.320 pies y 24% a 660 pies (nota). Loma Campana: más de 20% en hijos con padre a 240 a 400 m (artículo). | Hijos muy depletados contra vírgenes del mismo cuadrado de 2 km: -10,9% del rendimiento virgen a 12 meses (IC 95%: -33,4% a 11,6%). No firme; la mayor pérdida compatible con el dato público es el límite inferior de ese intervalo ([hijo_celdas.md](hijo_celdas.md)). |
| ¿El gas del padre también cae? | Midland (Reagan): la mayor caída fue en el gas diario del padre, por un tiempo, y el GOR bajó (nota). | Padres gasíferos a menos de 1 km: -12,6 puntos de gas al mes 1 (IC 95% por bloques de 5 km: -27,1 a -3,8), pero ya -7,2 en el mes -1, antes de la fractura; por día efectivo -3,4 puntos, con IC que incluye cero: la caída está en los días producidos. No firme ([gas.md](gas.md)). En los padres petrolíferos el GOR no muestra un cambio (IC que incluye cero): -1,3 puntos al mes 1 (IC 95% por pads: -3,8 a 0,6). |

## Qué aporta este trabajo

- **Toda la cuenca, con dato público.** Los trabajos leídos sobre Vaca Muerta son de un área (Loma Campana), de un pad o simulaciones de un modelo conceptual. Acá entran todos los eventos de shale de Vaca Muerta con ubicación, con el dato mensual que publica la Secretaría de Energía, y cualquiera puede repetir la cuenta.
- **El lado del padre, en producción.** El trabajo de Loma Campana mide el golpe por presión y deja para después la producción del padre; acá se mide esa producción contra controles, mes a mes.
- **Reglas fijadas antes de correr.** Las pruebas con veredicto escriben su regla y su muestra mínima en el código antes de calcular el resultado (lo agregado después de ver resultados se rotula como post hoc), y la publican aunque el resultado no favorezca la hipótesis (por ejemplo, el eje de mayor merma pasó a ser una descripción de la muestra).
- **Controles negativos y placebos.** Fechas de fractura falsas, fechas permutadas, pretendencia, cuatro controles distintos y un control negativo del lado del hijo.
- **Cifras verificadas.** Cada cifra del README y de las páginas se compara contra el warehouse en cada corrida (`pipeline/claims.py`).

## Límites de esta comparación

- Las definiciones no coinciden: un "evento negativo" de la industria se define con producción diaria o presión; acá es el caudal mensual. La caída de un mes puede ser un cierre preventivo del operador y no un daño (con datos mensuales no se separan).
- Las cifras de notas de prensa no se verificaron en el trabajo original.
- Las distancias de este proyecto son entre bocas de pozo, no entre ramas horizontales; los espaciamientos de la literatura son entre ramas.
