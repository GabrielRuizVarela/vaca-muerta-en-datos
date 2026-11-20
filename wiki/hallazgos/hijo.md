# Hijos cerca de pozos depletados

Página generada por `pipeline/hijo.py`. Pregunta si un pozo fracturado cerca de pozos que ya produjeron mucho rinde menos petróleo por metro de rama en sus primeros 12 meses que un pozo en zona virgen, a igualdad de área, cohorte y diseño de la fractura. Es el lado del hijo: las demás páginas miden al padre. Complementa [Interferencia entre fracturas](interferencia.md). La regla se fijó antes de correr y está en el libro de hallazgos como `hijo_depletado`.

## Resumen

Veredicto contra la regla fijada: **no firme**. La regla no permite concluir en ningún sentido. El IC del grupo muy depletado incluye cero y el punto es menor que 5% del rendimiento virgen, lo que sería una falsación de la degradación, pero la falsación exige un control negativo nulo y aquí no lo es: la misma exposición medida con pozos posteriores también se asocia con el rendimiento, con signo positivo, el contrario al de una degradación. Es compatible con que la ubicación, o un desarrollo posterior que sigue a los hijos que rindieron bien, empuje el rendimiento hacia arriba y tape una degradación; la versión continua del control negativo es nula, así que el control no nulo depende de los cortes por grupo. No permite leer el nulo del grupo muy depletado como ausencia de efecto.

- Rendimiento de los hijos en zona virgen a 12 meses: mediana de 84,2 bbl por metro de rama, sobre 778 hijos de 260 pads.
- Muy depletado contra virgen: -0,2 bbl por metro de rama (IC 95%: -12,6 a 12,2), o sea -0,2% del rendimiento virgen (IC 95%: -15,0% a 14,5%), sobre 1.612 hijos de 481 pads.
- Control negativo, muy depletado contra virgen: 8,9 bbl por metro de rama (IC 95%: 2,1 a 15,7), o sea 10,6% del rendimiento virgen (IC 95%: 2,5% a 18,6%). No es nulo.
- Exposición continua (descriptivo): -0,06 bbl por metro de rama por cada 100 bbl por metro de exposición (IC 95%: -0,86 a 0,75); con la exposición del control negativo: 0,08 (IC 95%: -0,08 a 0,25).
- Por operadora (descriptivo, muy depletado contra virgen): YPF 3,9 bbl por metro (IC 95%: -1,4 a 9,3); resto -11,5 bbl por metro (IC 95%: -52,9 a 29,9).
- Equilibrio (ubicación): el grupo muy depletado tiene 138 pozos de shale a menos de 5 km contra 80 del grupo virgen (p dentro de celdas 0,000), y 2.606 m de rama contra 2.580 m (p 0,000): se ubican en zonas de desarrollo más denso, que es lo que el control negativo ya muestra.
- El IC del modelo principal es ancho: en porcentaje del rendimiento virgen, no excluye una diferencia relevante en ninguno de los dos sentidos.
- Se publican todos los modelos calculados; el veredicto sale solo del modelo principal y su control negativo.

## Regla fijada antes de correr

La unidad es el pozo con 12 meses publicados, con rama, etapas, arena y fecha de primera fractura, cuyo primer petróleo llega entre 0 y 12 meses después del mes de la fractura. La exposición es el petróleo acumulado de los pozos de shale a menos de 1 km de distancia de superficie, contado solo hasta el mes anterior a la fractura del hijo y dividido por los metros de rama del hijo. Hay tres grupos: virgen (exposición cero), poco depletado (exposición positiva hasta la mediana de las positivas) y muy depletado (por encima de esa mediana). El resultado es el petróleo de 12 meses por metro de rama. El modelo es de mínimos cuadrados con efectos fijos de área por cohorte, rama, arena por metro, etapas y operador, con errores agrupados por pad.

El control negativo repite el modelo con la exposición de pozos que empezaron a producir después de la ventana de 12 meses del hijo: no pudieron depletarlo ni interferirlo. La regla pedía pozos posteriores a la fractura; se exige que empiecen después de la ventana porque un pozo que empieza dentro de ella podría afectar al hijo, que es el efecto de padre que este proyecto mide. Esa definición de la ventana se fijó antes de correr (commit 39c7dfe). La exposición de control se acumula hasta el último mes con datos, así que los hijos de cohortes recientes casi no tienen exposición de control y caen mecánicamente en el grupo virgen del control: las celdas de área por cohorte absorben el nivel, pero el control se apoya sobre todo en cohortes viejas.

- No se sostiene: el IC 95% del grupo muy depletado incluye cero, el punto es menor que 5% del rendimiento virgen y el control negativo es nulo (su IC incluye cero).
- Sostiene: el grupo muy depletado rinde menos con IC que excluye cero y el control negativo es nulo.
- Ubicación: igual que el anterior, pero el control negativo tampoco es nulo (núcleo contra borde, no depleción).
- No firme: cualquier otro caso. Sin muestra: menos de 50 hijos o de 20 pads en el grupo virgen o en el muy depletado, o menos de 100 pads.

## Grupos

El grupo poco depletado llega hasta 434 bbl por metro de exposición y el muy depletado empieza en 435; en el control negativo los cortes son los de sus propias exposiciones positivas. La exposición es el petróleo acumulado de los vecinos por metro de rama del hijo.

| Exposición | Grupo | Hijos | Pads | Exposición mínima (bbl/m) | Exposición máxima (bbl/m) | Mediana a 12 meses (bbl/m) | Media a 12 meses (bbl/m) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Exposición real | virgen | 778 | 260 | 0 | 0 | 84,2 | 88,0 |
| Exposición real | poco depletado | 417 | 151 | 0 | 434 | 84,5 | 87,6 |
| Exposición real | muy depletado | 417 | 105 | 435 | 11.926 | 95,1 | 97,0 |
| Exposición de control negativo | virgen | 925 | 277 | 0 | 0 | 84,1 | 87,1 |
| Exposición de control negativo | poco depletado | 344 | 101 | 2 | 817 | 87,7 | 88,9 |
| Exposición de control negativo | muy depletado | 343 | 124 | 817 | 20.898 | 97,8 | 100,0 |

## Coeficientes

Cada coeficiente es la diferencia de petróleo de 12 meses por metro de rama contra el grupo virgen (en el modelo continuo, por cada 100 bbl por metro de exposición), en bbl por metro. El porcentaje es contra la mediana del grupo virgen del modelo. El IC es de 95% con errores agrupados por pad; el p, con tres decimales, es el de la prueba normal de cada coeficiente.

| Modelo | Término | Coeficiente (bbl/m) | % del virgen | IC 95% (bbl/m) | Hijos | Pads | p |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| Principal | poco depletado | 2,3 | 2,7 | -4,5 a 9,0 | 1.612 | 481 | 0,512 |
| Principal | muy depletado | -0,2 | -0,2 | -12,6 a 12,2 | 1.612 | 481 | 0,974 |
| Control negativo | poco depletado | 0,2 | 0,2 | -6,6 a 7,0 | 1.612 | 481 | 0,963 |
| Control negativo | muy depletado | 8,9 | 10,6 | 2,1 a 15,7 | 1.612 | 481 | 0,010 |
| Continua | por 100 bbl/m | -0,1 | -0,1 | -0,9 a 0,7 | 1.612 | 481 | 0,889 |
| Continua, control negativo | por 100 bbl/m | 0,1 | 0,1 | -0,1 a 0,2 | 1.612 | 481 | 0,334 |
| Solo YPF | poco depletado | 4,0 | 4,9 | -1,5 a 9,6 | 1.001 | 269 | 0,156 |
| Solo YPF | muy depletado | 3,9 | 4,7 | -1,4 a 9,3 | 1.001 | 269 | 0,147 |
| Resto | poco depletado | -2,9 | -3,4 | -19,3 a 13,5 | 611 | 212 | 0,729 |
| Resto | muy depletado | -11,5 | -13,4 | -52,9 a 29,9 | 611 | 212 | 0,587 |

## Equilibrio entre grupos, antes del resultado

Medias de diseño y de ubicación por grupo de exposición real. El p es el de la prueba conjunta (Wald, errores por pad) de que los grupos poco y muy depletado no difieren del virgen: dentro de las celdas de área por cohorte, que es lo que el modelo ajusta, y sin celdas. Un p de 0,000 es menor que 0,0005. Una variable que no varía dentro de las celdas (la cohorte, y el operador, que en este dato coincide con el área) no tiene p dentro de ellas (n/d).

| Variable | Virgen | Poco depletado | Muy depletado | p dentro de celdas | p sin celdas |
| --- | ---: | ---: | ---: | ---: | ---: |
| Rama horizontal (m) | 2.580 | 2.512 | 2.606 | 0,000 | 0,544 |
| Etapas | 40,3 | 39,4 | 42,4 | 0,011 | 0,210 |
| Arena por metro (tn/m) | 3,68 | 3,50 | 3,76 | 0,532 | 0,003 |
| Cohorte (año del primer petróleo) | 2021,89 | 2021,24 | 2022,93 | n/d | 0,000 |
| YPF (% de los hijos) | 55,0 | 62,8 | 74,6 | n/d | 0,003 |
| Latitud (grados) | -38,281 | -38,260 | -38,276 | 0,999 | 0,753 |
| Longitud (grados) | -68,624 | -68,663 | -68,653 | 0,241 | 0,127 |
| Pozos de shale a menos de 5 km | 80 | 110 | 138 | 0,000 | 0,000 |

## Muestra

- Paso 1, mart_pozo_12m (petrolíferos de shale con 12 meses): 2.100 hijos.
- Paso 2, con área, pad, coordenadas y primer petróleo: 2.100 hijos.
- Paso 3, con rama, etapas y arena: 1.653 hijos.
- Paso 4, con fecha de primera fractura: 1.653 hijos.
- Paso 5, primer petróleo entre 0 y 12 meses después de la fractura: 1.612 hijos.

## Límites

- La distancia es de superficie: no hay trayectorias ni zona de aterrizaje. Con ramas de 1.500 a 3.200 m, un vecino a menos de 1 km de superficie puede estar a 100 m o a 3 km en el subsuelo, y puede estar en otra zona apilada.
- El espaciamiento entre ramas no se observa, así que no se separa depleción de espaciamiento.
- Núcleo contra borde: el desarrollo denso está donde la roca y la infraestructura son distintas. El control negativo mira ese riesgo con pozos posteriores, pero no lo elimina: la ubicación futura y la pasada no son la misma.
- Es una asociación con control de diseño, no una afirmación causal.
- El libro de hallazgos tiene su propio estado no firme: el estado de `hijo_depletado` sale del veredicto de arriba (confirmado si sostiene, refutado si no se sostiene, no firme en cualquier otro caso), no del valor.
- El resultado de 12 meses deja fuera a los pozos recientes, que todavía no tienen 12 meses publicados.
- Los intervalos no tienen ajuste por comparaciones múltiples: se publican todos los modelos calculados, favorables o no. Los coeficientes descriptivos entran en el conteo de pruebas del proyecto de [Bloques espaciales](bloques.md); los p de la prueba de equilibrio, que es un diagnóstico de la muestra, no.
