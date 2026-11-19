# Límites y robustez, en detalle

Página escrita a mano. El README lista los límites en una línea cada uno; acá está el detalle de cada uno, con sus cifras. Cada cifra de esta página se verifica contra el warehouse con `uv run python -m pipeline.claims`, y un test falla si aparece un número que ninguna verificación cubre.

## Lo que el dato público no trae

Coordenadas de superficie (pads), no la trayectoria de la rama.

Datos mensuales: un cierre preventivo del operador se ve igual que un daño por interferencia.

Datos públicos declarados por las operadoras; pueden rectificarse después.

## Lo que no se afirma

No se afirma causalidad: es una huella medida contra un control, con una brecha previa a la fractura.

El modelo de costo no predice un evento puntual: sus coeficientes describen asociaciones en la muestra.

## Intervalos y bloques espaciales

Los intervalos de las demás pruebas remuestrean pads hijo; con bloques espaciales de 5 km (144 bloques) el IC de la brecha del mes 1 es 1,29 veces más ancho y ningún veredicto cambia (`wiki/hallazgos/bloques.md`).

## Control de la brecha y cierre a los 6 meses

Control de la brecha: la brecha del mes 1 (de -22,9 a -24,5 puntos) y su cierre a los 6 meses no dependen de cuál de cuatro controles se use (2 a 5 km, 5 a 10 km, 2 a 10 km, y 2 a 5 km sin otro hijo a menos de 2 km); a los 6 meses la brecha queda dentro de 5 puntos con los cuatro (entre -2,1 y -4,7), pero con 3 de ellos su IC excluye cero, así que "se cierra" quiere decir menos de 5 puntos y no cero (`wiki/hallazgos/anillo.md`).

## Dirección de la merma

La caída de los padres cercanos no es igual en todas las direcciones de superficie en la muestra completa (con intervalos por pads), pero con datos públicos esa dirección no se separa del SHmax publicado ni de la forma en que se disponen los pads; la geometría de las ramas no se pudo probar. No es un hallazgo sobre esfuerzos ni sobre la fractura. La regla de parada fijada antes de correr se cumplió (`wiki/hallazgos/eje_parada.md`): la hipótesis del libro pasó de `anisotropia` a `asimetria_de_superficie`.

## Dosis y respuesta

Dosis y respuesta: con datos públicos no se ve que la caída del mes 1 crezca con la arena por etapa, la arena por metro de rama, la presión máxima de tratamiento ni la depleción del padre (modelo conjunto con Holm e intervalos por pads hijo: ninguna cumple y los quintiles no muestran orden; tampoco en la parte de caudal por día). Es compatible con cierre preventivo o con variables no observadas (espaciamiento real) y no dice que no haya golpes de fractura (`wiki/hallazgos/dosis.md`). Tampoco aparece una respuesta tardía en los meses 2 a 4 (16 pruebas con Holm; la más cercana es la depleción al mes 4, con p de 0,016 sin ajustar y de 0,26 ajustado; `wiki/hallazgos/dosis_meses.md`). Tampoco con la arena de todo el pad del hijo (pozos del pad fracturados en el mismo mes o a un mes) ni en los eventos a menos de 0,5 km con la interacción depleción por cercanía: ninguna de las nueve pruebas cumple tras Holm, y el límite alto de los intervalos llega a 0,29 desvíos de la caída en la muestra completa y a 0,43 (índice) o 0,54 (caudal por día) en el subconjunto cercano, así que no se descartan efectos de ese tamaño ni menores; cada variable sola da lo mismo y el FIV máximo es 2,6 (prueba agregada después de ver los resultados; `wiki/hallazgos/dosis_pad.md`).

Potencia del nulo de dosis: con 1.544 eventos en 262 pads hijo, el efecto mínimo detectable con 80% de potencia y corrección de Holm va de 0,22 a 0,32 desvíos de la caída por desvío de la dosis; un efecto de 0,2 puede pasar inadvertido con este dato, y la simulación de planta y recupera muestra que la cuenta analítica es optimista (`wiki/hallazgos/potencia_dosis.md`).

## Lado del hijo

Lado del hijo: el grupo muy depletado se ubica en zonas de desarrollo más denso y el control negativo da efecto, así que su nulo no se lee como ausencia de degradación. Comparando hijos del mismo lugar (diseño fijado después de ver ese control negativo y antes de correrlo), dentro de cuadrados de 2 km el hijo muy depletado da -11,2% del virgen (IC 95%: -33,8% a 11,5%) con el control negativo del grupo que decide nulo: sigue no firme, y la mayor pérdida compatible con el dato público es el límite inferior de ese intervalo (`wiki/hallazgos/hijo_celdas.md`).

## Por operador, por área y en otra cuenca

Robustez por operador y por área: sacando de a un operador (7) o de a un área (8) con al menos 50 eventos cercanos, la brecha del mes 1 queda entre -29,3 y -20,0 puntos con el IC 95% siempre por debajo de cero (sin YPF: -22,6) y el cierre del mes 6 queda dentro de 5 puntos; el nulo de dosis no se replica en el Colorado porque ese dato público no trae arena, etapas ni presión (`wiki/hallazgos/robustez_operador.md`).

Replicación en otra cuenca: se corrió en la cuenca DJ de Colorado con una regla fijada de antemano (`wiki/hallazgos/replicacion.md`); es validez externa de la huella y no una estimación conjunta. Colorado no tiene etapas ni arena, la rama es un proxy y los cierres aparecen como cero días producidos. `--with-colorado` es opcional.
