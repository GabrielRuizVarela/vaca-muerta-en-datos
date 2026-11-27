# Antecedentes leídos: qué dice cada fuente

Esta página acompaña a [`literatura.md`](../../wiki/hallazgos/literatura.md). Para cada trabajo publicado sobre interferencia entre pozos padre e hijo ("frac hits") dice qué parte pudimos leer, qué dice esa parte que importa para este estudio y cómo se relaciona con nuestro resultado. No es una revisión de la literatura, y donde solo se leyó un resumen o una nota de prensa se dice así.

Fecha de la lectura: 2026-11-26.

## Cómo leer los rótulos

- **Texto completo**: se leyó el trabajo entero (en el caso de Midland, las diapositivas de una presentación).
- **Resumen**: se leyó el resumen publicado, no el trabajo.
- **Nota**: se leyó una nota de prensa técnica que cita el trabajo.
- **Solo metadatos**: no se leyó ni el resumen; solo título, autores y DOI.

Nada se infiere del título. Cada cita entre comillas está copiada de la página o del PDF que se abrió. Solo se usaron accesos libres y gratuitos: el repositorio de la Universidad de Dakota del Norte (EERC), la presentación pública de SPE-GCS, la página de OGJ y la API pública de Crossref (metadatos y, cuando el editor lo depositó, el resumen). No se leyó nada de pago ni detrás de un login, salvo tres trabajos (Crespo 2020, Min 2023 y el URTeC 2690466 de 2017) cuyo PDF aportó el dueño del proyecto el 2026-11-26; esas copias no se guardan en el repositorio, y cada cita lleva la página. Los metadatos de los 13 trabajos vienen de Crossref.

---

## 1. Crespo, Pellicer, Crovetto, Gait (2020)

- **Cita:** Crespo, P.; Pellicer, M.; Crovetto, C.; Gait, J. (2020). "Quantifying The Parent-Child Effect in Vaca Muerta Formation". Proceedings of the 8th URTeC. DOI [10.15530/urtec-2020-1035](https://doi.org/10.15530/urtec-2020-1035).
- **Qué leímos:** el texto completo (12 páginas), 2026-11-26. Hasta esa fecha solo teníamos los metadatos.
- **Qué dice que importa:**
  - Pan American Energy, un bloque del centro de la cuenca neuquina que el trabajo no nombra; petróleo liviano de 37 a 42 °API (p. 2). No usa datos públicos.
  - Observación de campo (p. 3-4): en 2019 se fracturaron dos hijos de 2.500 m de rama a 250 m entre sí, con microsísmica de superficie (66 etapas en cremallera). Un padre "located 750 m to the west, which had been on production for approximately 8 months" recibió golpes: "Some events were detected in the parent well (frac-hits) and because of this, the parent well was shut-in for safety reasons during the rest of the treatment." Los trazadores químicos lo confirmaron.
  - Método (p. 5-9): un modelo de un pozo (2.000 m de rama, 27 etapas) ajustado con "more than 8 months of production history"; después, un padre y un hijo de 700 m de rama y 10 etapas, con espaciamientos de 200, 300 y 400 m y depleción del padre de 0 (fractura simultánea) a 5 años: "summarizing a total of eighteen runs" (p. 7). El esfuerzo horizontal se recalcula con la presión de poro del padre (ecuación 1) y se mide el cambio del EUR del hijo a 30 años contra el caso de fractura simultánea.
  - Resultado (figura 10, p. 10; las cifras se leyeron del gráfico y son aproximadas): a 200 m, alrededor de -19% con 1 año de depleción, -22% con 2 y entre -27% y -30% con 3 a 5; a 300 m, de alrededor de -11% a -24%; a 400 m, de alrededor de -5% a -14%. La depleción del padre a 1 a 5 años es de 14%, 23%, 30%, 35% y 40%. Frases de origen: "The 200 m case has a severe impact even with depletion scenarios of 1 and 2 years" y "For the 400 m well spacing, the parent-child effect is very low compared to other spacing cases".
  - No hay pozos de control ni comparación de grupos: el contrafactual es otra corrida del simulador. No mide la producción del padre después del golpe.
- **Cómo se relaciona con este estudio:** no midió lo mismo. Crespo simula el EUR del hijo en un bloque, calibrado con un pozo; este estudio mide la producción mensual del padre en todos los eventos de la cuenca contra controles. Lo que Crespo tiene y este estudio no: el mecanismo (esfuerzos y crecimiento de la fractura hacia la zona depletada) y la microsísmica de un caso. El trabajo cuenta que el padre se cerró por seguridad durante el resto de un tratamiento; la lectura para este estudio es nuestra: un cierre así, si cae en el mes de la fractura del hijo, baja el caudal mensual del padre sin que haya daño. Del lado del hijo, su pérdida simulada (5% a 30%) cae dentro del intervalo de 95% de este estudio para hijos muy depletados ([`hijo_celdas.md`](../../wiki/hallazgos/hijo_celdas.md)), pero las cantidades no son la misma: EUR simulado a 30 años contra rendimiento medido a 12 meses por metro de rama.

## 2. Lerza, Cuervo, Malhotra (2021)

- **Cita:** Lerza, A.; Cuervo, S.; Malhotra, S. (2021). "Closing the Gap in Characterizing the Parent Child Effect for Unconventional Reservoirs - A Case of Study in Vaca Muerta Shale Formation". SPE-206001-MS, SPE Annual Technical Conference and Exhibition.
- **Qué leímos:** el resumen (depositado por SPE en Crossref): <https://api.crossref.org/works/10.2118/206001-ms>.
- **Qué dice que importa:**
  - Vaca Muerta, pozo padre y pozo hijo. El resumen no da número de pozos, operador ni período. Menciona "field observed data such as microseismic, tracers, daily production data and well head pressure measurements", sin cifras. No dice si los datos son propios o públicos.
  - Método: se calibró un modelo de fractura y yacimiento con datos de campo, se acopló a un simulador geomecánico y se simularon escenarios de espaciamiento, tiempo de depleción y diseño del hijo, "analyzed and contrasted against previously field observed data". No hay grupo de control en el resumen, así que no es un diseño causal según lo leído.
  - Resultado, sin cifras: "Results obtained from the characterization work suggests the parent child effect is generated by a combination of initial drainage area changes and stress magnitude and direction changes" y "the well spacing and parent's production timing, as well as parent's and child's completion design, significantly affect the magnitude of the expected parent child effect impact over the child's EUR."
  - En el resumen no aparecen "causal", "balance" ni "covariate". Si el texto completo usara conceptos de inferencia causal, no lo pudimos ver; por eso lo describimos como "simulación calibrada con datos de campo".
- **Cómo se relaciona con este estudio:** Lerza cubre cómo cambia el EUR del hijo con el espaciamiento, el calendario y la completación, por simulación calibrada con datos de un caso, y explica el mecanismo (drenaje y esfuerzos). Este estudio no simula: mide la producción mensual de todos los eventos de la cuenca frente a controles cercanos. Lo que Lerza hace y este estudio no: explicar el mecanismo. Lo que este estudio hace y Lerza no (según el resumen): medir en datos públicos de toda la cuenca.

## 3. Min, Chakhmakhchev, Yu, Azzolina, Schmidt, Kurz, Sorensen (2023)

- **Cita:** Min, K. S.; Chakhmakhchev, A. V.; Yu, X.; Azzolina, N. A.; Schmidt, D. D.; Kurz, B. A.; Sorensen, J. A. (2023). "Data-Driven Analysis for Causality of Parent-Child Interactions in the Bakken". URTeC 3862589 (EERC, Universidad de Dakota del Norte).
- **Qué leímos:** el texto completo (18 páginas), 2026-11-26. Antes, el resumen en la página del ítem del repositorio de la UND (<https://commons.und.edu/eerc-publications/3>) y la nota de JPT (13e).
- **Qué dice que importa:**
  - Bakken. Datos de la comisión de North Dakota (NDIC, públicos), de Enverus (DrillingInfo, comercial), del EERC y de producción mensual (p. 4); la clasificación de pozos es a marzo de 2022 (p. 5). "There are approximately 17,000 horizontal wells completed in the Bakken" (p. 1): es el total de la cuenca. El estudio usa 12.466 pozos, después de sacar las unidades con pozos no paralelos o de distinto largo (p. 4). De ellos, 2.393 padres (19%), 3.168 hijos (25%), 4.452 de codesarrollo (36%) y 2.453 sueltos (20%) (tabla 1, p. 5).
  - Lado del padre (p. 7-8): cambio medio de los 90 días antes contra los 90 días después de completar el hijo, en 2.393 padres: "Parent well oil rates increased by about 75%, GORs decreased about 8%, and WORs increased about 122%". Es un antes contra después sin grupo de control. El texto dice que la cuenta deja afuera a los refracturados ("investigated in 2393 parent wells (excluding refractured parent wells)", p. 7), pero la tabla 1 (p. 5) da 2.393 como el total de padres y la p. 8 nombra aparte 78 padres refracturados, así que el artículo no deja claro si esos 78 entran en el 75%. El trabajo explica la subida porque muchos padres se completaron con diseños viejos y chicos y el hijo los reestimula.
  - Lado del hijo (p. 12-13): "Production Impact (child well) = Actual Production (under parent–child interactions) – Predicted Production (no parent–child interactions)", con la producción de 12 meses predicha por un modelo XGBoost de 20 variables entrenado en pozos de codesarrollo (R² de 0,719 en la muestra de prueba). Sin padre refracturado, el impacto va de "−15.4% to +0.6%" entre menos de 400 y más de 1.200 pies de espaciamiento (figura 26); con padre refracturado, de "−9% to +5%" (figura 25) (p. 16).
  - Si es causal: es un contrafactual por modelo predictivo; vale si el modelo captura todo lo que separa a un hijo de un pozo de codesarrollo. La referencia sin interacción son los pozos de codesarrollo ("developed together with child wells", p. 13), a través de un modelo entrenado con una partición al azar de los pozos; no empareja cada hijo con controles de su zona y no tiene placebos.
- **Cómo se relaciona con este estudio:** Min mide los dos lados en una cuenca entera, como este estudio, pero con otro diseño: el padre antes contra después, sin control, y el hijo contra un modelo. En el Bakken el padre sube en promedio; en Vaca Muerta, con controles, el padre cercano cae al mes siguiente. Min cubre refracturas y diseño de completación, que este estudio no mide; este estudio tiene controles cercanos, placebos y reglas fijadas antes de calcular.

## 4. Magneres, Castello, Bertoldi, Griffin (2020)

- **Cita:** Magneres, R. D.; Castello, M.; Bertoldi, F.; Griffin, M. (2020). "Vaca Muerta Frac-Hit Occurrence and Magnitude Forecast Methodology". URTeC 2020-1522. DOI [10.15530/urtec-2020-1522](https://doi.org/10.15530/urtec-2020-1522).
- **Qué leímos:** solo metadatos (Crossref no tiene resumen depositado).
- **Qué dice que importa:** nada; dato, método y resultado no se leyeron.
- **Cómo se relaciona con este estudio:** sin comparación posible. El título sugiere un pronóstico de ocurrencia y magnitud de frac hits, pero eso es solo el título y no lo usamos.

## 5. Romero et al. (2020)

- **Cita:** Romero, A.; Campo, N.; Villagra, F.; Gonzalez Day, L.; Quezada, B.; Pol'la, M.; Barresi, M.; Bertoldi, F.; Baieli, F.; Álvarez Claramunt, J. I.; Rozzisi, M.; Martinez, G.; Silva, K.; Spairani, J. (2020). "Real Time Series Analysis for Early Frac-Hit Detection in Vaca Muerta's Natural Flowing Wells". URTeC 2020-1420. DOI [10.15530/urtec-2020-1420](https://doi.org/10.15530/urtec-2020-1420).
- **Qué leímos:** solo metadatos (Crossref no tiene resumen depositado).
- **Qué dice que importa:** nada; dato, método y resultado no se leyeron.
- **Cómo se relaciona con este estudio:** sin comparación posible. Por el título, el trabajo sería sobre detección temprana en tiempo real en pozos que fluyen naturalmente; no se afirma más que eso.

## 6. Suarez y Pichon (2016)

- **Cita:** Suarez, M.; Pichon, S. (2016). "Completion and Well Spacing Optimization for Horizontal Wells in Pad Development in the Vaca Muerta Shale". SPE-180956-MS, SPE Argentina Exploration and Production of Unconventional Resources Symposium.
- **Qué leímos:** el resumen (depositado por SPE en Crossref): <https://api.crossref.org/works/10.2118/180956-ms>.
- **Qué dice que importa:**
  - Vaca Muerta, pad de pozos horizontales. Es un modelo numérico: el resumen no menciona datos de campo, operador ni pozos reales.
  - Acopla fractura (con "material balance, geomechanics, interaction with natural fractures and stress shadowing") y simulación de yacimiento. La interferencia se mide comparando la producción pronosticada de "a lateral standalone (single well approach) against this same lateral while surrounded by offsets competing for production (multi well approach)". Es una simulación con contrafactual (el mismo pozo solo o rodeado), no un diseño causal sobre datos reales.
  - Sin cifras en el resumen. Frase de origen: "Production interference between horizontal wells might reduce the final recovery of each individual well."
- **Cómo se relaciona con este estudio:** Suarez da un contrafactual limpio, pero dentro de un simulador. Este estudio tiene datos reales de toda la cuenca y no puede aislar el efecto de la misma forma; lo que sí hace es comparar con controles a 2-5 km.

## 7. Irazuzta, Klix, Solís, Herrero Clar, Alvarez (2023)

- **Cita:** Irazuzta, V. L.; Klix, B.; Solís, D.; Herrero Clar, F.; Alvarez, M. G. (2023). "Understanding Well Spacing and Stacking in Vaca Muerta Fm. Using Interference Tests and Tracers". SPE-212416-MS (Crossref: sesión del 20 de marzo de 2023).
- **Qué leímos:** el resumen (depositado por SPE en Crossref): <https://api.crossref.org/works/10.2118/212416-ms>.
- **Qué dice que importa:**
  - La Calera (gas húmedo, cerca de Añelo, Neuquén). El resumen dice "There are currently 30 horizontal wells in production from Vaca Muerta formation, drilled at three different landings in 3-wells pads." El operador no figura en el resumen. El estudio es de un solo pad de 3 pozos, con datos propios de campo (presión en cabeza y de fondo, producción de gas y líquido, trazadores de agua).
  - Método: pruebas de interferencia repetidas en el tiempo (antes y después de estimular el hijo, y una cuarta entre padre e hijo). No hay grupo de control; es un experimento de campo sobre un solo pad, no un diseño causal.
  - Sin cifras de producción en el resumen. Frases de origen: "After two years of production, all three wells were closed to minimize frac hits effects from child wells being stimulated 350 m (1150 ft) apart." y "moderate interference was observed among the three wells even though there is a vertical offset of 120 m (400 ft) between the lower and upper landing."
- **Cómo se relaciona con este estudio:** Irazuzta mide la presión del padre cerrado en un solo pad, con mucho detalle del golpe. Este estudio no mide presión; mide la producción mensual de todos los eventos de la cuenca. Lo que Irazuzta tiene y este estudio no: el lado del golpe con sensores y trazadores.

## 8. Fasola, De Marzio, Suarez (2023)

- **Cita:** Fasola, M. E.; De Marzio, L.; Suarez, M. I. (2023). "Integrated Approaches for Wells Interference and Drainage Assessment in Vaca Muerta Shale Play, Argentina". URTeC 2023-3860660. DOI [10.15530/urtec-2023-3860660](https://doi.org/10.15530/urtec-2023-3860660).
- **Qué leímos:** solo metadatos (Crossref no tiene resumen depositado).
- **Qué dice que importa:** nada; dato, método y resultado no se leyeron.
- **Cómo se relaciona con este estudio:** sin comparación posible. El título menciona drenaje además de interferencia, pero eso es solo el título.

## 9. Mamani, Ortiz, Álvarez, Escobar, Biglia, Nuñez (2024)

- **Cita:** Mamani, M. A.; Ortiz, M.; Álvarez, M. F.; Escobar, R.; Biglia, H.; Nuñez, S. E. (2024). "Frac Hits Analysis in Development Field in Black Oil Window in Vaca Muerta." URTeC 4044716. DOI [10.15530/urtec-2024-4044716](https://doi.org/10.15530/urtec-2024-4044716).
- **Qué leímos:** solo metadatos (Crossref no tiene resumen depositado).
- **Qué dice que importa:** nada; dato, método y resultado no se leyeron.
- **Cómo se relaciona con este estudio:** sin comparación posible. Por el título, sería un análisis de frac hits en ventana de petróleo negro; no se afirma más.

## 10. Velo, Vicente, Romero (2026)

- **Cita:** Velo, R. D.; Vicente, M.; Romero, A. N. (2026). "Frac Hit Detection Methodologies in Vaca Muerta Wells: Bridging the Traditional with the Enlightened". SPE-230644-MS, SPE Hydraulic Fracturing Technology Conference and Exhibition.
- **Qué leímos:** el resumen (depositado por SPE en Crossref): <https://api.crossref.org/works/10.2118/230644-ms>.
- **Qué dice que importa:**
  - YPF, datos propios. El resumen dice "YPF has been systematically monitoring frac hits using wellhead gauges during fracturing operations over the past six years". Incluye un caso de fibra óptica descartable en un pozo confinado; no da número de pozos ni de eventos.
  - Método descriptivo: compara sensores de fibra con sensores de cabeza de pozo, por etapa. No hay grupo de control de producción.
  - Frases de origen: "fiber responses were observed in 80% of the cases" y "Preliminary findings indicate that varying volume per cluster significantly impacts interactions between sibling wells."
- **Cómo se relaciona con este estudio:** Velo es un trabajo de detección del golpe con datos de una operadora, sin producción. Este estudio mide la producción del padre con datos públicos. El resumen no dice cuántos eventos ni qué producción; no se puede comparar más.

## 11. Garbino, Zuloaga, Mellado, Moreno, Solis, Fowler (2026)

- **Cita:** Garbino, A.; Zuloaga, P.; Mellado, G.; Moreno, J. P.; Solis, D.; Fowler, G. (2026). "Modeling Parent-Child Effect in Vaca Muerta to Quantify the Impact of Infill Timing, Well Spacing and Completion Design on Child Performance". SPE-231225-MS, SPE Argentina Exploration and Production of Unconventional Resources Symposium.
- **Qué leímos:** el resumen (depositado por SPE en Crossref): <https://api.crossref.org/works/10.2118/spe-231225-ms>.
- **Qué dice que importa:**
  - Campo de gas condensado en Vaca Muerta; modelo de seis pozos (un pad padre de 3 y un pad hijo de 3). El operador no figura en el resumen. El modelo se calibró con datos de campo: "treating pressures and ISIP trends, frac hits, production rates and ratios, and pressure interference tests".
  - Método: simulación acoplada geomecánica, de fractura y de yacimiento, con historia ajustada; escenarios de calendario, espaciamiento y diseño. No es un diseño causal con controles.
  - Frases de origen: "The interference tests seem to show interference between wells decreasing with time" y "Child well EUR can be from 5% to 50% lower than parent wells within the ranges of well spacing, infill timing, and completion designs tested."
- **Cómo se relaciona con este estudio:** Garbino da el rango de pérdida del hijo por simulación calibrada en un campo; este estudio no simula y mide la producción del padre en la cuenca entera. Garbino no tiene controles de la cuenca; este estudio no tiene la historia de presión de un pad.

## 12. Lu et al. (2024), Applied Sciences

- **Cita:** Lu, X.; Li, S.; Han, R.; Jia, B.; Xian, C.; Ding, F.; Zhang, Y.; Zhong, S.; Xu, Q.; Zuo, X. (2024). "An Overview of Recent Developments and Understandings of Unconventionals in the Vaca Muerta Formation, Argentina". Applied Sciences 14(4):1366. DOI 10.3390/app14041366. Licencia CC BY 4.0 (según Crossref).
- **Qué leímos:** el texto completo, en el PDF de acceso abierto de MDPI (<https://mdpi-res.com/d_attachment/applsci/applsci-14-01366/article_deploy/applsci-14-01366.pdf>; la página del artículo, <https://www.mdpi.com/2076-3417/14/4/1366>, rechaza la descarga automática). Ronda 1 del plan siguiente-nivel, 2026-11-26.
- **Qué dice que importa:**
  - Es una revisión bibliográfica (geología, técnicas de extracción, impacto ambiental, economía). No trae pozos propios ni datos de producción en el resumen, y no es un diseño causal.
  - La sección 4.1 ("Child and Parent Well Effect") trae una cifra de interferencia citada de otro trabajo. Frases de origen: "On average, child wells exhibited a productivity reduction of approximately 35% per stimulated foot when compared to the parent well. However, this decline was less severe in child wells situated at greater distances from the parent well." y, sobre la mitigación, "pressurizing the parent well with water".
  - La cifra lleva la referencia [52]. En la lista de referencias, [52] es Sarhan, C.E.; Gavilan, J.M.; Pitz, J.M. "First Operator's Tested Strategies in Vaca Muerta to Prevent EUR Degradation by Parent Child Effects", URTeC 2023. El pie de la figura 4, que acompaña el pasaje, dice en cambio "Reprinted with permission from Ref. [52]. Copyright 2018, SPE": la fuente exacta de la cifra no queda clara. No leímos [52].
  - La sección 9.4 cita a Malhotra y otros [78] por un aumento de 50 a 100% del EUR con optimización; tampoco lo leímos.
- **Cómo se relaciona con este estudio:** es una revisión, sin pozos ni controles propios. La cifra de 35% es del hijo frente al padre, por pie estimulado; este estudio mide la producción del padre, así que no es la misma cantidad.

## 13. Dos afirmaciones que la página de literatura sostenía sin fuente

### 13a. Midland Basin, condado de Reagan, Texas

- **Cita:** McDowell, B.; Yoelin, A.; Pottebaum, B. (2019). "Production Effects From Frac-Driven Interactions in the Southeastern Midland Basin, Reagan County, Texas". Presentación de 33 páginas, fecha 4 de octubre de 2019, identificador de portada "URTeC-125". No se verificó un DOI.
- **Qué leímos:** texto completo, en diapositivas: <https://spegcs.org/files/15252> (PDF). Registro del evento: <https://spegcs.org/events/4449>.
- **Qué dice que importa:** la presentación dice "47 horizontal wells", "16 vertical wells" y "17 multi-well frac jobs", y concluye: "FDIs are not a significant risk to oil production in parent wells in SE Midland basin". Los efectos: "Usually limited to increased water production and lower GORs" y "Usually temporary (weeks to months)".
- **Qué no confirma:** que la mayor caída haya sido en el gas diario del padre, por un tiempo. En las diapositivas no aparece nada sobre gas diario; la única frase sobre gas es el GOR.
- **Cómo se relaciona con este estudio:** es la fuente de que el efecto suele ser temporario (semanas a meses), pero es otra cuenca y se midió sobre otra clase de efecto (petróleo, agua y GOR del padre).

### 13b. OGJ: Vaca Muerta, un pad, "las conexiones bajan después de 6 meses"

- **Cita:** Procyk, A. (2023). "Pilot projects reduce frac hits in Vaca Muerta formation". Oil & Gas Journal, 6 de noviembre de 2023.
- **Qué leímos:** una nota de prensa técnica, en la web de OGJ (acceso libre): <https://www.ogj.com/exploration-development/article/14301343/pilot-projects-reduce-frac-hits-in-vaca-muerta-formation>. De ella comprobamos dos pasajes, el del Pad A y el de Pan American Energy. Las demás afirmaciones que la página de literatura toma de esta nota, y las cifras de los trabajos URTeC que la nota cita, no se comprobaron una por una.
- **Qué dice que importa:**
  - Sobre el Pad A: "For Pad A, hits were strong when it was put on production, but interwell connections dropped after 6 months. Microseismic confirmed this interpretation." Los sensores: "Gauges were removed and interrogated after 1 and 6 months."
  - Alcance: es un solo pad (Pad A, zona Cocina). La nota describe un piloto con tres locaciones de tres pozos cada una; no dice el operador en la frase leída, aunque menciona a Phoenix Global Resources al evaluar activos.
  - Sobre Pan American Energy: "Pan American Energy LLC has been actively exploiting VM with infill drilling and has experienced substandard child-well performance."
- **Cómo se relaciona con este estudio:** apoya, para un solo pad de Vaca Muerta, que las conexiones entre pozos bajan con los meses. Es una observación de presión y trazadores de un pad, no una comparación de producción como la de este estudio.

### 13c. JPT: 41% de 1.210 casos del Eagle Ford (ronda 1, 2026-11-26)

- **Qué decía la página:** "un caso de estudio publicado en JPT cita que, en 1.210 casos del Eagle Ford, el padre tuvo un evento negativo de producción en alrededor del 41% de las veces".
- **Qué leímos:** la nota de JPT del 1 de octubre de 2023, <https://jpt.spe.org/study-reviews-eagle-ford-parent-well-frac-hit-analysis-prediction-and-mitigation>. No trae ni 41% ni 1.210; habla de más de 1.600 pozos de ConocoPhillips. No encontramos las dos cifras en otra fuente abierta.
- **Qué se hizo:** se quitaron de la página y de su tabla.

### 13d. JPT: la simulación de SLB a 1.320 y 660 pies (ronda 1, 2026-11-26)

- **Fuente:** Trent Jacobs, "Frac Hits Reveal Well Spacing May Be Too Tight, Completion Volumes Too Large", JPT, 31 de octubre de 2017, <https://jpt.spe.org/frac-hits-reveal-well-spacing-may-be-too-tight-completion-volumes-too-large>.
- **Frases de origen:** "Simulated child wells with 1,320-ft spacing saw only 5% less cumulative oil production vs. the parent well over 5 years" y "660-ft-spaced wells saw 24% less production over the same span."
- **Qué falta:** nada. La nota remite al URTeC 2690466 (Ajisafe, Solovyeva, Morales, Ejofodomi y Marongiu Porcu, Schlumberger, 2017, "Impact of Well Spacing and Interference on Production Performance in Unconventional Reservoirs, Permian Basin"), que se leyó completo el 2026-11-26 (16 páginas). Las dos cifras están en el original: "The child well produced 5% less cumulative oil production comparing the parent well production for the same period of time. For the spacing of 660 feet, a 24% decrease in cumulative oil child well production was observed within 5 years of production" (p. 14). Es una simulación de un pad de dos pozos en la lutita Avalon (cuenca Delaware): el padre produce un año, después se completa el hijo y los dos producen 5 años juntos, ajustada al perfil P50 de unos 300 pozos de Avalon (p. 13-14). Con el hijo 150 pies más abajo a 660 pies, la pérdida baja a 10% (p. 14). Aparte, con el dato público de IHS, los hijos a menos de 2.000 pies de un padre y con al menos 6 meses de diferencia rinden alrededor de 30% menos que sus padres en el petróleo de los mejores 3 y 6 meses por agente de sostén por pie (p. 4).

### 13e. JPT: el Bakken, 17.000 pozos y el impacto en el hijo (ronda 2, 2026-11-26)

- **Fuente:** Trent Jacobs, "Data From 17,000 Wells Tells a New Tale on Bakken's Oil-Boosting Frac Hits", JPT, 28 de agosto de 2023, <https://jpt.spe.org/data-from-17-000-wells-tells-a-new-tale-on-bakkens-oil-boosting-frac-hits>. Comenta el URTeC 3862589 de Min y otros (entrada 3).
- **Frases de origen:** "The research team used machine learning models to analyze data from over 17,000 horizontal wells" y, citando el trabajo: "in child wells where there was no refractured parent well, when well spacing ranged from less than 400 ft to greater than 1,200 ft, the child well production impact ranged from −15.4 to +0.6%, respectively" (con padre refracturado, "from −9 to +5%").
- **Qué falta:** nada; el URTeC se leyó completo el 2026-11-26 (entrada 3). Las cifras del hijo están en la p. 16 del original. La de los pozos no: el trabajo dice "approximately 17,000 horizontal wells completed in the Bakken" (p. 1), que es el total de la cuenca, y analiza 12.466 (p. 4). La nota dice "over 17,000" y lo presenta como los pozos analizados.

### 13f. EconoJournal: fibra óptica descartable de YPF (ronda 2, 2026-11-26)

- **Fuente:** Ignacio Ortiz, "YPF usó por primera vez fibra óptica descartable para el monitoreo de fracturas en Vaca Muerta", EconoJournal, 23 de junio de 2025, <https://econojournal.com.ar/oilgas/ypf-uso-por-primera-vez-fibra-optica-descartable-para-el-monitoreo-de-fracturas-en-vaca-muerta/>.
- **Frase de origen:** la nota cita a Horacio Marín, presidente de YPF: "esta tecnología ya se implementó en 27 etapas sin incidentes y permitió identificar 40 eventos de frac-hits sin registrarse horas perdidas". El servicio es de Halliburton.
- **Qué falta:** son palabras de la empresa en redes sociales, citadas por la nota; no hay un trabajo técnico detrás que hayamos leído, ni pérdidas de producción.

---

## Tabla

| fuente | rótulo | dato | método | ¿diseño causal? | dirección |
| --- | --- | --- | --- | --- | --- |
| Crespo et al. 2020, URTeC 2020-1035 | texto completo | Pan American Energy, un bloque; microsísmica de un pad; 18 corridas de simulación | simulación calibrada con un pozo; EUR del hijo contra fractura simultánea | no | https://doi.org/10.15530/urtec-2020-1035 |
| Lerza et al. 2021, SPE-206001 | resumen | Vaca Muerta; sin cifras de pozos | simulación calibrada con datos de campo | no (en el resumen) | https://api.crossref.org/works/10.2118/206001-ms |
| Min et al. 2023, URTeC 3862589 | texto completo | Bakken, 12.466 pozos (de unos 17.000); 2.393 padres y 3.168 hijos | padre: antes contra después, sin control; hijo: real contra predicho por XGBoost | no (contrafactual por modelo) | https://doi.org/10.15530/urtec-2023-3862589 |
| Magneres et al. 2020, URTeC 2020-1522 | solo metadatos | no leído | no leído | no determinado | https://doi.org/10.15530/urtec-2020-1522 |
| Romero et al. 2020, URTeC 2020-1420 | solo metadatos | no leído | no leído | no determinado | https://doi.org/10.15530/urtec-2020-1420 |
| Suarez y Pichon 2016, SPE-180956 | resumen | modelo numérico de pad | simulación con contrafactual (pozo solo vs. rodeado) | no | https://api.crossref.org/works/10.2118/180956-ms |
| Irazuzta et al. 2023, SPE-212416 | resumen | La Calera, 30 pozos, pads de 3; operador no nombrado | pruebas de interferencia repetidas, sin control | no | https://api.crossref.org/works/10.2118/212416-ms |
| Fasola et al. 2023, URTeC 2023-3860660 | solo metadatos | no leído | no leído | no determinado | https://doi.org/10.15530/urtec-2023-3860660 |
| Mamani et al. 2024, URTeC 4044716 | solo metadatos | no leído | no leído | no determinado | https://doi.org/10.15530/urtec-2024-4044716 |
| Velo et al. 2026, SPE-230644 | resumen | YPF, seis años de monitoreo; sin conteo | descriptivo, sensores de fibra y cabeza de pozo | no | https://api.crossref.org/works/10.2118/230644-ms |
| Garbino et al. 2026, SPE-231225 | resumen | gas condensado, modelo de 6 pozos; operador no nombrado | simulación calibrada, sin control | no | https://api.crossref.org/works/10.2118/spe-231225-ms |
| Lu et al. 2024, Applied Sciences 14(4):1366 | texto completo | revisión; sin datos propios; cita 35% menos del hijo por pie estimulado (de [52], no leído) | revisión bibliográfica | no | https://www.mdpi.com/2076-3417/14/4/1366 |
| Midland (Reagan), McDowell et al. 2019 | texto completo (diapositivas) | 47 horizontales, 16 verticales, 17 frac multipozo | descriptivo, criterio de FDI por cambios de petróleo, WOR y GOR | no | https://spegcs.org/files/15252 |
| OGJ, Procyk 2023 (un pad) | nota (se comprobaron los pasajes del Pad A y de Pan American Energy) | Pad A, zona Cocina; piloto de 3 pozos por locación | observación de presión y trazadores, 1 y 6 meses | no | https://www.ogj.com/exploration-development/article/14301343/pilot-projects-reduce-frac-hits-in-vaca-muerta-formation |
| JPT, Jacobs 2023 (Bakken) | nota (comprobada contra Min et al. 2023) | dice más de 17.000 pozos; el trabajo analiza 12.466 de unos 17.000; impacto en el hijo de -15,4% a +0,6% según espaciamiento (está en el original) | aprendizaje automático sobre datos de producción | no (ver Min et al. 2023) | https://jpt.spe.org/data-from-17-000-wells-tells-a-new-tale-on-bakkens-oil-boosting-frac-hits |
| Ajisafe et al. 2017, URTeC 2690466 | texto completo | lutita Avalon (Permian), pad de 2 pozos simulado; ~300 pozos para el perfil | simulación; hijo contra padre a 1.320 y 660 pies, 5 años | no | https://doi.org/10.15530/urtec-2017-2690466 |
| EconoJournal, Ortiz 2025 (YPF) | nota (palabras de YPF citadas) | 27 etapas, 40 eventos de frac-hit | fibra óptica descartable durante la fractura | no | https://econojournal.com.ar/oilgas/ypf-uso-por-primera-vez-fibra-optica-descartable-para-el-monitoreo-de-fracturas-en-vaca-muerta/ |

---

## Qué falta leer

- **Crespo 2020**: leído completo el 2026-11-26 (entrada 1). Ya no es un hueco.
- **Magneres 2020, Romero 2020, Fasola 2023, Mamani 2024**: solo metadatos.
- **Lerza, Suarez, Irazuzta, Velo, Garbino**: solo el resumen; los textos completos no se leyeron. Min se leyó completo el 2026-11-26 (entrada 3). En la ronda 1 (2026-11-26) se buscaron de nuevo Crespo 2020, el texto de Lerza 2021, Min, Magneres y Mamani: seguían sin texto abierto (Crespo y Min se leyeron después, de los PDF aportados el 2026-11-26); Romero y Fasola no aparecieron.
- **Sarhan, Gavilan y Pitz (URTeC 2023, DOI 10.15530/urtec-2023-3861789)**, la fuente que Lu y otros citan para el 35%: no leído. Uno de los PDF aportados el 2026-11-26 resultó ser otro trabajo (Alzahabi, Kamel y Trindade, URTeC 4048995, 2024, sobre el Wolfcamp), que solo cita a Sarhan.
- **URTeC 2690466**, el estudio de SLB que cita la nota de JPT de 2017: leído completo el 2026-11-26 (13d).
- **Gas diario del padre en Midland:** no aparece en las diapositivas.
- **Descripción de Lerza como "inferencia causal":** no aparece en el resumen; puede estar en el texto completo, que no leímos.
