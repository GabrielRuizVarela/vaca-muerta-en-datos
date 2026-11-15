# Investigación, fase 3: qué aguanta lo medido y qué medir después

Plan de investigación, 2026-11-15. Documento interno: no es un mensaje para nadie. Parte de los resultados publicados en `wiki/hallazgos/` (anisotropía, robustez, validación, placebo, libro) y del README; no rehace esas cifras. Dos datos nuevos se verificaron sobre una copia del warehouse: `stg_fractura` tiene `fecha_inicio`, `fecha_fin`, `presion_maxima_psi`, `agua_m3` y `terminacion` para los 5.064 trabajos; la duración mediana de una fractura es de 13 días y el 47% de los trabajos empieza en un mes y termina en el siguiente. `stg_produccion` tiene `dias_efectivos` en todas las filas y gas en el 79%.

Otro hilo está construyendo en paralelo la validación del eje, la incertidumbre del costo, la verificación de cifras, el linaje, el tablero y una operación de robustez del agente. Este documento no diseña esas piezas: dice qué se le exige a su resultado (secciones 3.6 y 3.9) y qué preguntas científicas las rodean.

## 0. Resumen

- Lo sólido: hay una caída brusca de producción en padres cercanos alineada con la fecha de fractura del hijo, que no aparece en fechas falsas ni con fechas permutadas, que viene con un salto de corte de agua y que se cierra en unos 6 meses.
- Lo débil: la magnitud (hay pretendencia, 23 puntos es una cota superior), el mecanismo (cierre preventivo y daño se confunden), el volumen agregado (sin intervalo) y todo lo direccional.
- Lo que no se sostiene como afirmación: que exista un eje de interferencia distinto del SHmax publicado, que el rumbo pese en el costo, y que el modelo de costo prediga algo mejor que la media.
- La amenaza principal al eje no es estadística sino geométrica: con coordenadas de superficie, el rumbo hijo a padre mezcla la dirección de propagación de las fracturas con la forma en que se disponen los pads y las ramas, y ambas predicen ejes parecidos.
- Primeras tres tareas: separar días efectivos de caudal por día, calcular la potencia para separar 93 de 67,5 grados, y correr controles negativos del eje (ventana previa y anillo lejano). Suman unas 12 horas.

## 1. Qué sostienen los resultados y qué no

Para cada afirmación: qué sostiene, qué no, la explicación alternativa más fuerte y qué dato las distingue.

### 1.1 Brecha al mes 1 de 23 puntos (padres a menos de 1 km contra controles de 2 a 5 km)

- **Sostiene:** existe una caída asociada a la fecha de fractura. Las fechas desplazadas -12 y -6 meses dan brechas de -2,4 y -0,4 puntos con intervalos que incluyen cero, y la brecha real (-22,9) queda fuera de las 200 permutaciones (-8,4 a -4,8). El perfil temporal (pico en k = 1, cierre hacia k = 6) es el de una perturbación transitoria.
- **No sostiene:** la magnitud (la brecha previa de -6,3 puntos en k = -1 la contamina; el descuento a 19 o 20 puntos depende de suponer que la brecha previa es un nivel fijo), ni que sea daño al pozo.
- **Alternativa más fuerte:** cierre o estrangulamiento preventivo del padre durante la fractura del vecino, que es práctica operativa habitual. Produce la misma huella mensual: caída en el mes de la fractura y vuelta en pocos meses.
- **Qué las distingue:** descomponer la caída en días efectivos y caudal por día efectivo. Un cierre preventivo baja los días y deja el caudal por día casi igual; un golpe de fractura baja el caudal por día, sube el corte de agua y puede mover la relación gas petróleo. Está en `stg_produccion` (sección 3.1).

### 1.2 Recuperación al mes 6 y "diferimiento, no pérdida"

- **Sostiene:** la mediana de la brecha al mes 6 es chica (-2,1 puntos) y la fracción de padres que no vuelve al 90% de la trayectoria de control a los 12 meses no supera a la de los controles (exceso -1,9 puntos, IC -5,1 a 1,2).
- **No sostiene:** que no haya pérdida. Una mediana que se cierra es compatible con una mezcla: algunos padres pierden de forma permanente y otros ganan (los golpes a pozos viejos a veces represurizan y suben el caudal). El umbral del 90% es grueso y el IC admite un exceso de hasta 1,2 puntos en contra, pero también de 5 a favor; con 1.760 padres no tiene potencia para pérdidas chicas.
- **Alternativa:** heterogeneidad que se cancela, más controles contaminados (un control a 2 a 5 km puede recibir su propio hijo cercano en la ventana, lo que acerca ambas curvas).
- **Qué las distingue:** el déficit acumulado de 0 a 24 meses por padre, con su distribución completa (no solo la mediana) y un intervalo por conglomerados; separar padres con brecha positiva y negativa al mes 1 y seguir a cada grupo.

### 1.3 Unos 10,7 millones de barriles diferidos en los meses 0 a 6 (73% en YPF)

- **Sostiene:** un orden de magnitud de la huella, sumada sobre eventos.
- **No sostiene:** la cifra puntual. No tiene intervalo publicado, incluye la brecha previa (la misma pretendencia que reduce los 23 puntos reduce también los barriles), y un padre con dos hijos en 6 meses aporta dos eventos con ventanas superpuestas (posible doble conteo). El 73% en YPF refleja que YPF tiene la mayoría de los padres en desarrollo denso (Loma Campana), no que sus prácticas sean peores; sin normalizar por evento y por caudal base no dice nada del operador.
- **Qué hace falta:** suma por padre y mes (sin superponer ventanas), con intervalo por bootstrap de pads hijo y una versión descontando la pretendencia; informar barriles por evento y como fracción del caudal base, por operador.

### 1.4 Eje de mayor merma de la cuenca: unos 93 grados (IC 70 a 122, p 0,022)

- **Sostiene:** en la muestra completa la caída al mes 1 no es isotrópica en el rumbo de superficie hijo a padre, y el punto estimado es estable (92 con eventos viejos, 88 con nuevos, 82 con el salto de agua). Las fechas permutadas no dejan eje definido en 10 de 10.
- **No sostiene:** un eje firme (4 de 13 subconjuntos con IC de 90 grados o más, sin Loma Campana no está definido, ningún año lo define, fuera de tiempo el IC mide 128 grados y p 0,43), ni que difiera del SHmax publicado (67,5; fuera de tiempo el eje de entrenamiento no mejora al SHmax: 0,18% de la suma de cuadrados, IC -1,23% a 1,73%), ni que sea una medición de esfuerzos. Además el ángulo explica menos del 1% de la suma de cuadrados.
- **Alternativa más fuerte: geometría de desarrollo.** En Vaca Muerta las ramas se perforan en general cerca de la perpendicular al SHmax para que las fracturas crezcan transversales a la rama. Entonces los vecinos lado a lado (ramas paralelas que comparten roca) quedan desplazados en superficie en una dirección cercana al SHmax, y los vecinos en la dirección de la rama quedan punta con punta o con las ramas alejándose. Un efecto que depende solo de la distancia entre ramas, sin ninguna anisotropía de la fractura, ya daría un eje de merma cercano a la dirección lado a lado. Esa dirección la fija cómo diseña cada operador el pad, no el esfuerzo. Con 694 de 1.734 eventos en Loma Campana, el eje de la cuenca es en buena parte el eje de un solo plan de desarrollo.
- **Qué las distingue:** con datos públicos, solo en parte. (a) Estimar el eje de exposición: la orientación de las propias parejas y de las filas de pads en cada área, sin mirar la merma; si el eje de merma coincide con él, la geometría alcanza. (b) Un modelo de distancia entre ramas con la longitud de rama de `dim_fractura_pozo` y azimut supuesto, contra el modelo de rumbo. (c) Coordenadas de fondo o trayectorias, que no están en el warehouse (sección 3.4).

### 1.5 Ejes por área (Fortín de Piedra 62 grados, Loma Campana 101 grados)

- **Sostiene:** dos de siete áreas tienen un eje definido con la regla del proyecto.
- **No sostiene:** una rotación regional ni una diferencia entre áreas. Son 7 pruebas sin corrección; a 0,05 se esperan unos 0,35 falsos positivos y salen 2 con p de 0,020 y 0,046, lo que no resiste una corrección de Holm (umbral 0,007 para la primera). Fortín de Piedra tiene 27 pads hijo y un contraste de 93,5 puntos, muy sensible a pocos pads; además es mayormente gas, así que el índice de petróleo mide otra cosa.
- **Alternativa:** cada área tiene su propio diseño de pad y azimut de rama, lo que da ejes de exposición distintos.

### 1.6 Rumbo en el modelo de costo (-963 bbl por 10 grados, IC -1.841 a 231)

- **No sostiene** nada: el IC incluye cero en las 7 especificaciones, y fuera de muestra el término de ángulo no mejora el R2 (diferencia de 0,003). Que el signo se repita en 6 de 6 especificaciones no es evidencia independiente: comparten casi todos los eventos.
- **Lectura honesta:** el rumbo no agrega capacidad de predecir barriles diferidos. Debería salir del modelo de costo o quedar marcado como exploratorio.

### 1.7 Modelo de costo

- **No sostiene** predicción: R2 fuera de muestra -0,15, peor que la media del área (0,009) en R2 y RMSE; 26,6% de las predicciones bajo cero; mal calibrado en los extremos (decil 10: 26.702 predichos contra 16.213 observados). El intervalo de 80% supone errores independientes entre padres del mismo hijo, que es falso por diseño (responden al mismo hijo), así que es demasiado angosto.
- **Lo que sí se puede decir:** la variación entre eventos es grande y casi no la explican las variables públicas; el mejor estimador puntual hoy es la media del área con su dispersión.

### 1.8 Salto del corte de agua y cierre declarado (libro: confirmados)

- **Sostiene:** los padres cercanos tienen saltos de corte de agua más de 0,15 con 18,8 puntos más de frecuencia que los controles, y figuran parados en el mes de la fractura 7 puntos más. El salto de agua es la firma clásica de un golpe de fractura (llega fluido de fractura del hijo) y es la mejor evidencia mecánica que tiene el proyecto. El cierre declarado es evidencia directa de que una parte de la caída es operativa.
- **No sostiene:** cuánto de la caída es cada cosa. El salto de agua también puede aparecer al reabrir un pozo cerrado (cambia la relación de flujo de las fases), así que hay que medirlo en padres sin cierre declarado y sin caída de días.

### 1.9 Libro de hallazgos: `anisotropia` figura como "confirmado"

- La prueba del libro compara un sector de 56,25 a 101,25 grados contra 0 ± 22,5 grados con un umbral fijo. Ese sector contiene tanto los 93 grados como el SHmax (67,5), así que "confirmado" no distingue entre ellos, y la etiqueta convive mal con "no firme" en el README. Si el sector se eligió después de ver la estimación, la prueba no es independiente. Recomendación para el hilo de verificación de cifras: renombrar el hallazgo a algo como "merma mayor en el sector ENE a E que en el N" y agregar en la página que no separa 93 de 67,5 ni de la geometría de desarrollo.

### 1.10 Pretendencia (-2,5, -3,5 y -6,3 puntos en k = -3, -2, -1)

- **Alternativas:** (a) nivel distinto: los hijos se ubican cerca de padres que ya declinaban más (infill en zonas maduras); (b) anticipación operativa: cierres o restricciones durante la perforación del hijo o la preparación de la fractura; (c) efecto de vecinos previos, ya descartado en parte (persiste sin golpes previos a menos de 2 km); (d) regresión a la media en la base -6 a -4.
- **Qué las distingue:** que la brecha crezca hacia k = -1 (de -2,5 a -6,3) es más compatible con (b) o con una deriva que con un nivel fijo, lo que haría que el descuento a 19 o 20 puntos sea demasiado optimista o demasiado pesimista según la forma de la deriva. Separar días y caudal por día en k = -3 a -1 (si la brecha previa es de días, es operativa) y usar el día de inicio de la fractura dentro del mes (sección 3.5).

## 2. Amenazas a la validez, concretas a este dato

**Medición.**
- Coordenadas de superficie: con ramas de 1.500 a 3.200 m, la distancia de superficie de 0,3 a 1 km puede corresponder a ramas a 100 m o a 3 km. El umbral "menos de 1 km" mezcla vecinos reales con pozos que no comparten roca, lo que diluye el efecto y distorsiona el rumbo.
- Sin zona de aterrizaje: Vaca Muerta tiene varias zonas apiladas; dos ramas a poca distancia de superficie pueden estar en niveles distintos. `dim_pozo.formacion` no lo resuelve.
- Resolución mensual: con fracturas que duran 13 días (mediana) y el 47% cruzando el fin de mes, el mes k = 0 mezcla días antes y después. La asignación de k depende de qué fecha se usa (`primera_fractura`, que parece salir de `fecha_inicio`).
- Datos declarados y rectificables, con prácticas de declaración distintas por operador (días efectivos, estado Parado Transitoriamente). Un operador que declara cierres y otro que no producen eventos distintos con la misma física.
- El índice truncado en [0, 2] acota la influencia de outliers pero también recorta los golpes positivos grandes.

**Selección.**
- Los hijos no se ubican al azar: el operador elige dónde hacer infill. La pretendencia sugiere que los padres cercanos ya eran distintos.
- Padres con más de 1 m3/d y con datos en la base: quedan fuera padres marginales o recién abiertos.
- Controles de 2 a 5 km: si el emparejamiento no es dentro del área, comparan geología y operador distintos; aun dentro del área, pueden estar en el borde del desarrollo.

**Confusión.**
- Desarrollo denso: un padre cercano a un hijo está cerca de otros hijos que fracturan en fechas próximas (zipper, pads múltiples). La media de las fechas permutadas (-6,5 puntos, no cero) es la huella de esto.
- Controles contaminados por sus propios hijos cercanos sesgan la brecha hacia cero.
- Choques de área (restricciones de transporte, mantenimiento de planta, 2020) afectan más a quien produce en el núcleo, donde también hay más hijos.
- Para el eje: la orientación de las filas de pads, el azimut de rama y la distribución de rumbos disponibles están correlacionados con el área y el operador.

**Comparaciones múltiples.** El eje se miró en 13 subconjuntos, 5 resultados alternativos, 8 grupos de años, 7 áreas y una prueba fuera de tiempo; la pretendencia en 7 meses y 4 desplazamientos. Ninguna corrección se aplicó. Además hubo decisiones tomadas viendo resultados (banda de 0,3 a 1 km, regla de "definido", sector del libro). Cualquier afirmación nueva tiene que salir de un análisis preregistrado en este documento.

**Dependencia espacial.** El bootstrap remuestrea pads hijo, pero un mismo padre aparece en varios eventos, pads vecinos comparten geología y desarrollo, y 1.210 de 3.448 pozos cambian de pad según cómo se agrupe. Si los conglomerados son demasiado finos, todos los IC son angostos de más, incluido el del eje (p 0,022 puede no sobrevivir a bloques espaciales).

**Supervivencia.** El análisis exige un padre que produzca; pozos abandonados después de un golpe salen del panel en meses posteriores (al mes 12 se cuentan como 0, pero en otros análisis se descartan). Los padres en zonas que el operador dejó de desarrollar tienen menos eventos.

**Límites del dato público.** No hay trayectorias ni coordenadas de fondo en el warehouse, ni zona de aterrizaje, ni presión de boca de pozo, ni datos diarios, ni orificio de estrangulamiento, ni registro de cierres preventivos. Algunas preguntas (separar cierre de daño en un pozo puntual, medir el espaciamiento real) no tienen respuesta con este dato y hay que decirlo.

## 3. Investigaciones siguientes, por valor por hora

Cada una lleva una regla de decisión fijada antes de correrla. "IC" es intervalo de 95% por bootstrap de pads hijo salvo que se diga otra cosa; todas usan semilla fija y escriben un mart nuevo sin tocar `sql/` ni `costo.py`.

### 3.1 Cierre o daño: días efectivos contra caudal por día (mecanismo)

- **Pregunta:** ¿qué fracción de la caída al mes 1 es menos días producidos y qué fracción es menos caudal por día producido?
- **Por qué importa:** decide si la afirmación central es "interferencia física" o "práctica operativa". Si casi todo es días, la huella es de gestión y el eje pierde sentido físico.
- **Método:** mismo estudio de eventos (k = -6 a 12, base -6 a -4, controles de igual edad), con cuatro resultados por padre y mes: índice de días efectivos, índice de caudal por día efectivo (petróleo / días, solo meses con días > 0), corte de agua, relación gas petróleo. Descomposición en logaritmos: log(índice de producción) = log(índice de días) + log(índice de caudal por día), brecha de cada parte con IC por pads hijo. Repetir en padres sin estado Parado Transitoriamente en k = 0 y 1.
- **Datos:** `stg_produccion` (`petroleo_m3`, `gas_miles_m3`, `agua_m3`, `dias_efectivos`, `estado`). Disponible.
- **Esfuerzo:** 5 h.
- **Falsa la hipótesis de daño si:** la brecha del caudal por día al mes 1 tiene un IC que incluye cero y la parte de días explica 80% o más de la brecha total.
- **Regla:** si el caudal por día explica 50% o más y su IC excluye cero, se escribe "la caída incluye pérdida de caudal por día, compatible con golpe de fractura"; si explica menos de 20%, se escribe "la huella es mayormente de días producidos, compatible con cierre preventivo" y el eje se describe como dirección de la gestión operativa, no de la interferencia; en el medio, se informan ambas partes sin elegir.

### 3.2 Potencia: ¿se puede separar 93 de 67,5 grados con este dato?

- **Pregunta:** ¿cuántos eventos harían falta para que el IC del eje excluya el SHmax si la diferencia real fuera de 25 grados, y cuándo los habrá?
- **Por qué importa:** si la respuesta es "más eventos de los que la cuenca generará en años", la pregunta de la dirección no tiene respuesta con datos públicos y hay que dejar de hacerla. Es la base de la regla de parada (sección 4).
- **Método:** con el semiancho actual (unos 26 grados a n = 1.734, error estándar circular cercano a 13 grados) y el supuesto de que escala con 1 sobre la raíz del número de pads hijo, calcular el n para un error estándar de 9 grados (necesario para separar 25 grados a 95%). Verificarlo con simulación: generar caídas con el modelo ajustado y eje real 67,5 o 93, remuestrear pads hasta n objetivo, 200 corridas por n, y medir la fracción de IC que excluye el otro valor. Proyectar n con el ritmo de eventos de 2025 y 2026 (unos 300 y 194 por año en la banda de 0,3 a 1 km).
- **Datos:** el mart de eventos existente. Disponible.
- **Esfuerzo:** 2 a 3 h.
- **Falsa la idea de que "faltan datos" si:** la simulación muestra potencia de 80% con menos de 1,5 veces los eventos actuales.
- **Regla:** si hacen falta más de 2 veces los eventos actuales (la cuenta aproximada da unas 2,2 veces, unos 3.800 eventos, más de una década al ritmo actual), el proyecto declara que la dirección no es separable del SHmax con este dato y deja de presentarla como hallazgo.

### 3.3 Controles negativos del eje y de la brecha (placebo)

- **Pregunta:** ¿aparecen el eje y la brecha donde no deberían?
- **Por qué importa:** si el eje aparece antes de la fractura, es selección o geometría, no interferencia.
- **Método:** tres pruebas, preregistradas juntas y con corrección de Holm sobre las tres.
  1. Eje en la ventana previa: mismo ajuste axial coseno, efectos fijos de área, eventos de 0,3 a 1 km, con resultado la caída del índice entre la base (-6 a -4) y k = -1. Permutación por bloques de pads hijo, 499 sorteos.
  2. Anillo lejano: padres a 5 a 10 km del hijo contra controles de 2 a 5 km. Debería dar brecha nula y ningún eje.
  3. Gradiente de distancia: brecha al mes 1 en bandas de 0 a 0,3, 0,3 a 0,6, 0,6 a 1, 1 a 2 y 2 a 5 km (contra 5 a 10 km). Debe ser monótona y llegar a cero.
- **Datos:** eventos y `stg_produccion`; hay que extender la búsqueda de padres más allá de 5 km. Disponible.
- **Esfuerzo:** 5 h.
- **Falsa la lectura de interferencia direccional si:** la ventana previa da un eje definido (IC menor de 90 grados y p menor de 0,10) a menos de 30 grados de 93, o el anillo lejano da una brecha con IC que excluye cero de más de 3 puntos.
- **Regla:** eje previo definido y cercano: el eje se reescribe como "dirección en la que los padres ya rendían menos", sin relación demostrada con la fractura. Anillo lejano con brecha: se investiga un choque de área antes de cualquier otra afirmación de magnitud. Gradiente no monótono: la banda de 0,3 a 1 km se vuelve a justificar o se abandona.

### 3.4 Eje de exposición: ¿la geometría de desarrollo alcanza para explicar el eje?

- **Pregunta:** ¿el eje de merma es distinto del eje que dicta la disposición de pads y la dirección probable de las ramas?
- **Por qué importa:** es la alternativa más fuerte al eje (sección 1.4) y la que haría interesante, o irrelevante, la comparación con el SHmax.
- **Método:** tres piezas.
  1. Eje de exposición por área: con todos los pares padre e hijo de 0,3 a 1 km (no solo los eventos con caída), ajustar el eje principal de la distribución de rumbos (media axial con momento de segundo orden); con los centros de pad, el eje principal de las filas (análisis de componentes principales de las posiciones dentro de cada desarrollo). Comparar con el eje de merma del área.
  2. Reponderación: reestimar el eje de merma con pesos inversos a la densidad de rumbos del área (bins de 15 grados), para que todas las direcciones pesen igual.
  3. Modelo de ramas: ubicar cada rama como un segmento que nace en la coordenada de superficie, con la longitud de `rama_horizontal_m` y azimut supuesto perpendicular al SHmax (157,5 grados), con las dos orientaciones posibles y una sensibilidad de ±20 grados. Calcular la distancia mínima entre segmentos de hijo y padre y comparar dos modelos de la caída: distancia entre ramas sin ángulo contra distancia de superficie más el término de rumbo. Comparación por validación cruzada por pads hijo (diferencia de RMSE con IC por bootstrap de pliegues).
- **Datos:** `int_pozo_ubicacion`, `int_pozo_pad`, `dim_fractura_pozo.rama_horizontal_m`. Azimut de rama y coordenadas de fondo: no disponibles en el warehouse; verificar si el padrón de pozos de la Secretaría de Energía o el organismo provincial de Neuquén publican coordenadas de fondo (no verificado; si no, decirlo). Los pilotos de espaciamiento publicados en SPE o URTeC sobre Loma Campana pueden dar el azimut típico de rama (buscar, no verificado aquí).
- **Esfuerzo:** 10 a 12 h.
- **Falsa la idea de un eje propio de la interferencia si:** el eje de merma cae dentro del IC del eje de exposición en Loma Campana y en la cuenca, o la reponderación deja el eje indefinido, o el modelo de distancia entre ramas sin ángulo predice igual o mejor que el de rumbo.
- **Regla:** si cualquiera de las tres se cumple, el texto dice "el eje de merma es compatible con la geometría de desarrollo; con datos públicos no se separa del SHmax ni de la disposición de los pads". Solo si las tres fallan se conserva "eje de merma distinto del de exposición", siempre sin llamarlo esfuerzo.

### 3.5 Tiempo dentro del mes: ¿la caída sigue a la fecha de fractura día a día?

- **Pregunta:** ¿la brecha en k = 0 crece con la fracción del mes posterior al inicio de la fractura, y la brecha en k = -1 depende de cuán temprano en el mes empieza?
- **Por qué importa:** es una prueba de dosis en el tiempo que un artefacto de calendario no reproduce, y separa la pretendencia por nivel de la anticipación operativa.
- **Método:** para cada evento, f0 = días del mes k = 0 desde `fecha_inicio` hasta fin de mes, sobre los días del mes. Brecha al k = 0 en terciles de f0 y regresión de la brecha del evento sobre f0 con efectos fijos de área y año, errores por pads hijo. Repetir con `fecha_fin` (fracturas que terminan en k = 1). Para la pretendencia: brecha en k = -1 de días efectivos y de caudal por día según el inicio caiga en los días 1 a 7 o después.
- **Datos:** `stg_fractura.fecha_inicio`, `fecha_fin`; `stg_produccion`. Disponible (5.064 trabajos con ambas fechas).
- **Esfuerzo:** 5 h.
- **Falsa la sincronía con la fractura si:** la pendiente sobre f0 tiene IC que incluye cero, o es negativa.
- **Regla:** pendiente positiva con IC que excluye cero: se agrega "la caída sigue a la fecha de fractura dentro del mes" como evidencia de sincronía. Brecha de días en k = -1 concentrada en inicios tempranos: la pretendencia se reescribe como anticipación operativa y el descuento a 19 o 20 puntos se reemplaza por una cota calculada con k = -2 como base.

### 3.6 Validación del eje sin reutilizar eventos (exigencia para el otro hilo)

- **Pregunta:** ¿el eje aparece en pares que no entraron en la estimación?
- **Por qué importa:** hoy toda la evidencia de consistencia (resultados alternativos, años, fuera de tiempo, subconjuntos) comparte eventos, padres o controles con la estimación principal.
- **Método:** dos réplicas, ninguna con eventos de la estimación.
  1. Anillo de 1 a 2 km: eventos nuevos (pares que no están en la banda de 0,3 a 1 km), mismo ajuste. Antes, la sección 3.3 tiene que mostrar que hay brecha a esa distancia; si no la hay, esta réplica no tiene potencia y no se corre.
  2. Prueba prospectiva congelada: se fija hoy el eje (93 grados), el SHmax (67,5) y el modelo, con el hash del código, y se evalúan solo los eventos con fractura del hijo posterior a 2026-09 a medida que entren. Métrica: mejora de la suma de cuadrados del eje congelado contra el SHmax y contra 200 ejes al azar, como en la validación actual. Se evalúa una sola vez, cuando haya 500 eventos nuevos; no antes.
- **Lo que se le exige al resultado del otro hilo:** (a) que el conjunto de prueba no comparta padres con el de entrenamiento (excluir padres que aparecen a ambos lados, o informar cuántos hay); (b) que todo el modelo, no solo el eje, salga del entrenamiento (coeficientes, efectos de área, índice de control); (c) que compare contra el SHmax y contra el eje de exposición de la sección 3.4, no solo contra ejes al azar; (d) que informe la diferencia con IC y no solo el punto; (e) que la regla de éxito esté escrita antes de correr.
- **Datos:** eventos existentes y datos futuros de la Secretaría. Disponible el anillo; la prospectiva requiere esperar (unos 2 años a 250 eventos por año).
- **Esfuerzo:** 4 h el anillo, 2 h congelar la prueba prospectiva.
- **Falsa el eje si:** en el anillo el eje queda definido a más de 45 grados de 93, o en la prospectiva el eje congelado no mejora al SHmax (diferencia con IC que incluye cero o negativa).
- **Regla:** el eje se presenta como replicado solo si queda definido en una réplica sin eventos compartidos y su IC excluye el SHmax; cualquier otro resultado mantiene "no firme, no separable del SHmax".

### 3.7 Inferencia espacial y controles contaminados

- **Pregunta:** ¿los IC y el p de 0,022 sobreviven a conglomerados más gruesos, y cambia la brecha si se limpian los controles?
- **Por qué importa:** es una prueba de robustez barata que puede bajar el eje a "sin evidencia" o mover la magnitud.
- **Método:** reestimar la brecha al mes 1 y el eje con bootstrap por: pads hijo agrupados por cercanía de 50 m (los 1.210 pozos que cambian de pad), pozo padre, bloques espaciales de 2 y 5 km, y área; y con conglomerado doble (pad hijo por padre). Para el eje, permutación por bloques espaciales. Controles: excluir los que tienen su propio hijo a menos de 1 km entre k = -6 y 6; informar cuántos son y la brecha con y sin ellos. Para el volumen, agregar por padre y mes sin superponer ventanas.
- **Datos:** `int_pozo_pad`, `int_pozo_ubicacion`, eventos. Disponible.
- **Esfuerzo:** 5 h.
- **Falsa la precisión publicada si:** con bloques de 5 km el p del eje pasa de 0,10 o el IC de la brecha se ensancha más de 50%.
- **Regla:** el README usa el IC de la especificación más conservadora que tenga al menos 30 conglomerados; si con ella el eje deja de estar definido en la cuenca, se escribe "sin evidencia de anisotropía con inferencia espacial".

### 3.8 Dosis y respuesta: diseño de la fractura del hijo y depleción del padre (mecanismo)

- **Pregunta:** ¿la caída crece con el tamaño del trabajo del hijo y con la depleción del padre, como predice la física de los golpes de fractura?
- **Por qué importa:** una respuesta monótona a la dosis es la prueba física más clara de que la huella es interferencia y no gestión; su ausencia la debilita. La literatura de la industria espera golpes más fuertes en padres más depletados (las fracturas del hijo crecen hacia la zona de menor presión) y con trabajos más grandes.
- **Método:** resultado en escala libre (brecha del índice al mes 1, y la parte de caudal por día de la sección 3.1), no en barriles. Cuatro variables preregistradas: arena por etapa, arena por metro de rama, presión máxima de tratamiento (`presion_maxima_psi`) y petróleo acumulado del padre por metro de rama hasta la fecha de fractura (depleción). Controles: distancia, edad del padre, caudal base, número de hijos simultáneos a menos de 1 km, efectos fijos de área por año. Primero gráficos por quintiles con IC; después un modelo con las cuatro a la vez y errores por pads hijo. Holm sobre las cuatro.
- **Datos:** `stg_fractura`, `dim_fractura_pozo`, `int_pozo_mop`. Disponible. Tipo de terminación (`terminacion`, 5 valores) como control o subconjunto.
- **Esfuerzo:** 8 h.
- **Falsa el mecanismo si:** ninguna de las cuatro tiene IC que excluya cero tras Holm y los quintiles no muestran orden.
- **Regla:** dos o más variables con el signo esperado y IC que excluye cero: se escribe "la caída crece con X y Y, como se espera de un golpe de fractura". Ninguna: se escribe que el dato público no muestra dosis y respuesta, lo que es compatible con cierre preventivo o con variables no observadas (espaciamiento real).

### 3.9 Incertidumbre honesta del costo (exigencia para el otro hilo)

- **Pregunta:** ¿cuál es la incertidumbre real del diferido por evento y del total, y qué factores sobreviven a una selección fuera de muestra?
- **Por qué importa:** hoy el modelo no le gana a la media, el intervalo supone independencia que no existe y ningún factor excluye cero. Mantenerlo como está invita a leer coeficientes que no dicen nada.
- **Método:** (1) el total diferido con IC por bloques espaciales de 5 km y en dos versiones (con y sin descuento de pretendencia); (2) resultado en fracción del caudal base (escala libre) y un modelo con contracción (ridge o jerárquico con agrupamiento parcial por área), elegido por validación cruzada por pads hijo; (3) un factor queda en el modelo solo si quitarlo empeora el RMSE fuera de muestra con IC por bootstrap de pliegues que excluye cero; (4) intervalos de predicción conformales por grupos (residuos fuera de muestra agrupados por pad hijo y remuestreados en bloque, para que los padres del mismo hijo compartan error); (5) cobertura empírica del intervalo de 80% en un pliegue reservado.
- **Lo que se le exige al resultado del otro hilo:** cobertura empírica informada (no solo el ancho), dependencia entre padres del mismo hijo incluida, comparación con la media del área como referencia obligatoria, y la operación del agente devolviendo la media del área cuando el modelo no la supera.
- **Datos:** marts de costo existentes. Disponible.
- **Esfuerzo:** 8 a 10 h.
- **Falsa el modelo si:** ningún modelo supera a la media del área en RMSE fuera de muestra con IC que excluya cero.
- **Regla:** si ninguno la supera, el proyecto publica el total con IC y la distribución por evento por área, y retira los coeficientes de la página como resultados (quedan en un anexo exploratorio). Si la cobertura empírica del 80% baja de 70%, el intervalo de la operación se reemplaza por el conformal por grupos.

### 3.10 Fuera del marco: el lado del hijo (¿el hijo rinde menos cerca de un padre depletado?)

- **Pregunta:** ¿un hijo fracturado cerca de padres que ya produjeron mucho rinde menos petróleo por metro a 12 meses que un hijo en zona virgen, a igualdad de área, cohorte y diseño?
- **Por qué importa:** para un ingeniero de reservorios la pérdida del hijo suele pesar más que el diferido del padre: decide el espaciamiento y el momento del infill, y es donde está el dinero. El proyecto hoy solo mide al padre. El docstring de `costo.py` registra un nulo preliminar con coordenadas de superficie, sin diseño formal.
- **Método:** unidad: pozo hijo. Exposición: petróleo acumulado de los pozos a menos de 1 km de superficie hasta la fecha de fractura del hijo, por metro de rama del hijo (continua) y en tres grupos (virgen, poco depletado, muy depletado). Resultado: petróleo de 12 meses por metro de rama (`mart_pozo_12m`). Controles: efectos fijos de área por cohorte, rama, arena por metro, etapas, operador. Errores por pad. Prueba de equilibrio: comparar diseño y ubicación entre grupos antes del resultado. Como control negativo, la misma exposición medida con pozos que empezaron a producir después de la fractura del hijo (no pueden haber depletado nada).
- **Datos:** `mart_pozo_12m`, `int_pozo_mop`, `int_pozo_ubicacion`, `dim_fractura_pozo`. Disponible.
- **Esfuerzo:** 8 h.
- **Falsa la degradación del hijo si:** el coeficiente del grupo muy depletado tiene IC que incluye cero y el punto es menor que 5% del rendimiento del grupo virgen, con el control negativo nulo.
- **Regla:** si el grupo muy depletado rinde menos con IC que excluye cero y el control negativo es nulo, se escribe "los hijos cerca de padres depletados rinden menos, asociación con control de diseño" y se informa en bbl por metro; si el control negativo también da efecto, la asociación es de ubicación (núcleo contra borde) y no de depleción.
- **Variante, si sobra tiempo:** ¿sirve el cierre preventivo? Comparar el déficit acumulado a 12 meses de padres con y sin Parado Transitoriamente declarado en k = 0, emparejando por distancia, edad, caudal base, trabajo del hijo y operador. Hay confusión por indicación fuerte (se cierra lo que se espera que sufra), así que el resultado es descriptivo; aun así es una pregunta que la industria discute y el dato la permite mirar.

## 4. Orden recomendado y regla de parada

**Primero (unas 12 horas):**
1. Sección 3.1 (cierre o daño). Define qué es la huella.
2. Sección 3.2 (potencia). Define si la pregunta de la dirección tiene respuesta.
3. Sección 3.3 (controles negativos). Define si el eje y la brecha aparecen donde no deberían.

**Después:** 3.5 y 3.7 (baratas, mueven magnitud e inferencia), 3.4 (la prueba decisiva de la geometría), 3.8 y 3.10 (mecanismo e interés de ingeniería), 3.9 y 3.6 en coordinación con el otro hilo.

**Regla de parada para el eje.** El proyecto deja de presentar un eje de interferencia y lo dice en el README, la página de anisotropía y `docs/verificacion.md` si se cumple cualquiera de:

- la potencia (3.2) pide más de 2 veces los eventos actuales para separar 93 de 67,5 grados; o
- la ventana previa (3.3) da un eje definido a menos de 30 grados de 93; o
- el eje de exposición o el modelo de ramas (3.4) explican el eje de merma; o
- con bloques espaciales de 5 km (3.7) el eje de la cuenca deja de estar definido.

La frase de reemplazo, sin adornos: "La caída de los padres cercanos no es igual en todas las direcciones de superficie en la muestra completa, pero con datos públicos esa dirección no se separa del SHmax publicado ni de la forma en que se disponen pads y ramas. No es un hallazgo sobre esfuerzos ni sobre la fractura." El hallazgo `anisotropia` del libro se renombra en consecuencia.

**Regla de parada para la magnitud.** Si 3.1 muestra que menos de 20% de la caída es caudal por día, los 23 puntos y los 10,7 millones de barriles se describen como "producción no entregada durante fracturas vecinas", sin la palabra interferencia en el titular.

**Lo que no se hace:** no se agregan subconjuntos nuevos al análisis del eje fuera de las pruebas preregistradas acá; cada corte extra es otra comparación sin corregir.

## 5. Qué convencería a un ingeniero de reservorios escéptico

La lista más corta, en este orden:

1. **Estudio de eventos descompuesto:** k = -6 a 12, brecha con IC en cuatro paneles (producción, días efectivos, caudal por día, corte de agua), con la base de -6 a -4 visible. Responde "¿es golpe o cierre?".
2. **Brecha contra distancia:** bandas de 0 a 0,3 hasta 5 a 10 km, con el anillo lejano en cero. Responde "¿decae como un efecto físico?".
3. **Sincronía dentro del mes:** brecha en k = 0 contra fracción del mes posterior al inicio de la fractura. Responde "¿sigue a la fecha real?".
4. **Dosis y respuesta:** caída contra depleción del padre y tamaño del trabajo del hijo, por quintiles. Responde "¿se comporta como dice la física?".
5. **Mapa de un desarrollo (Loma Campana):** pads, pares hijo y padre coloreados por caída, el eje de exposición, el eje de merma y el SHmax en la misma figura, con el modelo de ramas superpuesto. Responde "¿el eje es geometría?".
6. **Déficit acumulado a 24 meses** por padre, distribución completa con IC. Responde "¿es diferimiento o pérdida?".
7. **Una tabla de lo que no se mide** (trayectorias, zona de aterrizaje, presiones, datos diarios, cierres no declarados), puesta antes de los resultados y no al final.

Un ingeniero de reservorios va a desconfiar de cualquier afirmación direccional hecha con coordenadas de superficie. La figura 5 y la sección 3.4 son la respuesta honesta a esa objeción: o muestran que la dirección sobrevive a la geometría, o el proyecto la retira.
