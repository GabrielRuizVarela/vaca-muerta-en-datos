# Anisotropía de la interferencia y su costo

Página generada por `pipeline/costo.py`. Sale de eventos entre 0,3 y 1 km de distancia de superficie, con el índice del padre al mes 1 de la fractura del hijo restado al del control de igual edad. El rumbo es el del eje hijo a padre (0 grados es norte, 90 es este).

## Eje de máxima merma

En toda la cuenca (n = 1.734, efectos fijos de área) el eje de mayor merma queda en 93 grados (E-O), con intervalo de 95% de 70 a 122 grados. El contraste entre el eje y su perpendicular es de 14,2 puntos de índice (p de permutación 0,022).

| Área | n | Pads hijo | Eje (grados) | IC 95% | Ancho IC | Contraste (puntos) | p perm. | Latitud media | Eje definido |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| Cuenca | 1.734 | 324 | 93 | 70 a 122 | 53 | 14,2 | 0,022 | -38,29 | sí |
| LINDERO ATRAVESADO | 87 | 10 | 67 | 175 a 135 | 140 | 17,4 | 0,528 | -38,59 | no |
| FORTIN DE PIEDRA | 143 | 27 | 62 | 50 a 88 | 39 | 93,5 | 0,020 | -38,49 | sí |
| LOMA CAMPANA | 694 | 148 | 101 | 78 a 131 | 53 | 17,9 | 0,046 | -38,35 | sí |
| LA CALERA | 64 | 15 | 155 | 78 a 61 | 163 | 42,1 | 0,296 | -38,34 | no |
| BANDURRIA SUR | 126 | 21 | 21 | 148 a 95 | 127 | 87,4 | 0,346 | -38,29 | no |
| BAJADA DEL PALO OESTE | 132 | 13 | 22 | 130 a 105 | 155 | 11,0 | 0,880 | -38,22 | no |
| LA AMARGA CHICA | 275 | 49 | 77 | 3 a 150 | 147 | 15,5 | 0,376 | -38,20 | no |

![Mapa de ejes por área](anisotropia_mapa.svg)

Mapa: en cada área, segmento continuo oscuro si el eje está definido (con el cono de su IC de 95%) o gris punteado si no; la línea naranja es el SHmax publicado de 67,5 grados.

Las áreas van ordenadas de sur a norte y tienen al menos 60 eventos. Si el límite alto del intervalo es menor que el bajo, el intervalo cruza el norte (0 y 180 grados son el mismo eje). Un eje se da por definido si el p de permutación es menor que 0,10 y el intervalo mide menos de 90 grados; la amplitud del ajuste siempre es positiva, así que solo el p la separa del ruido. El intervalo sale de remuestrear pads de pozos hijo completos (los padres de un mismo hijo responden juntos), con semilla fija (400 repeticiones). Los ejes de áreas chicas dependen de pocos pads hijo.

## Comparación con lo publicado

El SHmax publicado para la cuenca es OSO-ENE (RAGA 2024, https://revista.geologica.org.ar/raga/article/view/1793), es decir un eje cercano a 67,5 grados en esta convención. La literatura describe además una rotación regional del campo de esfuerzos entre el sur y el norte de la cuenca. Esta página no la cuantifica: pone los ejes estimados por área junto a la latitud para que se compare. No encontramos publicaciones que infieran la dirección de SHmax a partir de producción, y el eje de merma no es una medición de esfuerzos.

## Costo por evento

Modelo lineal de los barriles diferidos en los meses 0 a 6 contra el control de igual edad, con 2.077 eventos cercanos (R2 0,09), efectos fijos de área y errores robustos. El eje de cada evento se estima sin su propio pliegue de pads hijo (validación cruzada) y el intervalo sale de remuestrear pads hijo y re-estimar los ejes, con semilla fija.

| Factor | Efecto | IC 95% | Unidad | Efecto por 1 desvío estándar (bbl) |
| --- | ---: | --- | --- | ---: |
| km | 7.780 | -1.775 a 15.848 | bbl por km de distancia | 2.169 |
| desvio_eje_10 | -963 | -1.841 a 231 | bbl por 10 grados de desvio respecto del eje (0 = sobre el eje) | -2.490 |
| edad_anios | -723 | -2.974 a 1.717 | bbl por año de edad del padre | -1.439 |
| base_10m3d | 571 | -1.518 a 3.445 | bbl por 10 m3/d de caudal base del padre | 2.715 |
| hijos_1km | 479 | -991 a 1.790 | bbl por hijo adicional a menos de 1 km | 776 |
| arena_1000tn | 1.327 | -451 a 3.669 | bbl por 1.000 tn de arena del hijo | 5.518 |
| etapas_10 | -1.846 | -7.369 a 663 | bbl por 10 etapas del hijo | -3.474 |
| parado | 1.976 | -1.100 a 6.071 | bbl si el padre figura Parado Transitoriamente en el mes 0 | 686 |

En palabras: cada efecto es lo que cambian los barriles diferidos de un padre en los meses 0 a 6 si ese factor sube una unidad y los demás quedan fijos. Medidos por desvío estándar, los tres factores que más pesan son arena_1000tn, etapas_10, base_10m3d; con intervalo que no cruza cero: ninguno. Los demás no permiten afirmar el signo.

Cada 10 grados que el padre se aparta del eje de mayor merma cambia el diferido en -963 bbl (negativo: sobre el eje se difiere más). El intervalo cruza cero: es una tendencia, no una conclusión. El eje de cada evento se estima sin los eventos de su propio pliegue de pads hijo (validación cruzada) y el intervalo re-estima los ejes en cada repetición; es el de su área si está definido y, si no, el de la cuenca. Un padre con el estado Parado Transitoriamente no se distingue de un golpe en estos datos.

## Incertidumbre del costo

Validación cruzada en 5 pliegues de pads hijo completos (2.077 eventos con todos los datos): en cada pliegue se reestiman los ejes y los coeficientes sin los eventos de prueba y se predicen esos eventos. La lista de áreas con eje propio y la de áreas con efecto fijo salen de la muestra completa y no se rehacen en cada pliegue. Las métricas son sobre esas predicciones fuera de muestra, con semilla fija.

| Modelo | n | MAE (bbl) | RMSE (bbl) | R2 fuera de muestra | Predicho bajo cero |
| --- | ---: | ---: | ---: | ---: | ---: |
| Modelo completo | 2.077 | 14.846 | 29.373 | -0,153 | 26,6% |
| Modelo completo, acotado en cero | 2.077 | 14.416 | 29.211 | -0,140 | no aplica |
| Referencia: media del entrenamiento | 2.077 | 15.028 | 27.375 | -0,002 | no aplica |
| Referencia: media del área | 2.077 | 14.840 | 27.232 | 0,009 | no aplica |
| Modelo sin el término de ángulo | 2.077 | 14.656 | 29.412 | -0,156 | 25,3% |

El modelo no supera a las referencias en R2 ni en RMSE fuera de muestra: su R2 es -0,153 contra -0,002 de la media del entrenamiento y 0,009 de la media del área, y su RMSE es 29.373 bbl contra 27.375 y 27.232. En MAE queda parecido: 14.846 bbl, o 14.416 con la salida acotada en 0 (el estimador de la operación), contra 15.028 y 14.840 de las referencias. El modelo explica poco de la variación entre eventos y tiene peor R2 y RMSE que la media simple: el intervalo es ancho y el valor puntual no debe leerse como una predicción precisa. El término de ángulo respecto del eje no mejora el R2 fuera de muestra (diferencia de 0,003 contra el modelo sin ese término). El 26,6% de los eventos se predice por debajo de cero; el estimador puntual de la operación los acota en 0.

Calibración: eventos ordenados por la predicción fuera de muestra y agrupados en deciles. Si el modelo estuviera bien calibrado, el observado medio acompañaría al predicho medio.

| Decil | n | Predicho medio (bbl) | Observado medio (bbl) | Residual p10 (bbl) | Residual p90 (bbl) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 208 | -7.576 | 670 | -5.484 | 25.351 |
| 2 | 208 | -2.543 | 758 | -6.922 | 12.006 |
| 3 | 208 | -316 | 2.088 | -5.602 | 14.286 |
| 4 | 207 | 1.641 | 1.184 | -12.715 | 12.201 |
| 5 | 208 | 3.397 | 1.398 | -11.267 | 8.618 |
| 6 | 208 | 5.053 | 2.493 | -18.388 | 14.231 |
| 7 | 207 | 7.443 | 3.227 | -31.428 | 23.744 |
| 8 | 208 | 10.863 | 10.311 | -26.585 | 34.422 |
| 9 | 208 | 15.289 | 13.312 | -31.102 | 33.681 |
| 10 | 207 | 26.702 | 16.213 | -50.143 | 59.068 |

El decil más bajo promedia -7.576 bbl predichos contra 670 observados; el más alto, 26.702 contra 16.213. El residual es el observado menos el predicho.

Intervalo de 80%: los residuales fuera de muestra se agrupan por tercil de la predicción y, para un padre, el intervalo es su predicción más los cuantiles 10 y 90 de los residuales de su tercil, acotado en 0. Para la suma sobre los padres de un pad, la operación `costo_interferencia` sortea 2.000 veces un residual por padre (semilla fija), acota cada padre en 0 y toma los percentiles 10 y 90 de la suma. Supone errores independientes entre padres; si los de un mismo hijo se mueven juntos, el intervalo real es más ancho. Es un intervalo de predicción de un modelo de asociación, no del efecto causal de una fractura.

| Tercil de predicción | n | Residual p10 (bbl) | Residual p90 (bbl) |
| ---: | ---: | ---: | ---: |
| 1 | 693 | -6.768 | 16.745 |
| 2 | 692 | -16.965 | 14.124 |
| 3 | 692 | -33.530 | 36.531 |

## Cola de pérdida permanente

Al mes 12, 41,8% de los padres cercanos (n = 1.760) no vuelve al 90% de la trayectoria mediana del control de su edad, contra 43,7% de los controles (n = 15.406). El exceso es de -1,9 puntos (IC 95% de -5,1 a 1,2). Los meses sin dato cuentan como índice 0. El umbral es relativo a la mediana del control, así que una parte de los controles queda por debajo por construcción: lo que importa es el exceso.

| Edad del padre | n cercanos | No recupera (cercanos) | No recupera (controles) | Exceso (puntos) |
| --- | ---: | ---: | ---: | ---: |
| todos | 1.760 | 41,8% | 43,7% | -1,9 |
| 06-11 | 408 | 41,2% | 43,4% | -2,2 |
| 12-23 | 590 | 38,6% | 42,2% | -3,6 |
| 24-47 | 484 | 42,8% | 42,7% | 0,0 |
| 48+ | 278 | 47,5% | 45,9% | 1,6 |

## Límites

- No se identifica la pérdida del pozo hijo por la depleción del padre: solo se mide el lado del padre.
- No se identifica el espaciamiento lateral entre ramas: solo hay coordenadas de superficie.
- Un cierre preventivo del padre se ve igual que un golpe en datos mensuales; el estado declarado (Parado Transitoriamente) los separa solo en parte.
- El eje es la dirección de la merma observada, no del esfuerzo, y solo se estimó entre 0,3 y 1 km: no se midió cómo cambia el patrón con la distancia.
- El modelo es lineal y de asociación: los coeficientes no son efectos causales.
