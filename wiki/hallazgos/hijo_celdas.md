# Hijos cerca de pozos depletados, dentro de celdas de 2 km

Página generada por `pipeline/hijo_celdas.py`. Repite la pregunta de [Hijos cerca de pozos depletados](hijo.md) comparando hijos del mismo cuadrado de 2 km: el que se fracturó cuando sus vecinos ya habían producido mucho contra el que se fracturó en zona virgen, con el año del primer petróleo, el diseño de la fractura, el operador y la densidad final de pozos alrededor como controles. Este diseño se fijó después de ver el resultado de [hijo.md](hijo.md), que quedó no firme porque su control negativo no es nulo; la regla se escribió antes de calcular nada con él y no cambia el veredicto de `hijo_depletado`.

## Resumen

Veredicto contra la regla fijada: **no firme**. La regla no permite concluir en ningún sentido. El control negativo del grupo que decide ahora es nulo, a diferencia de hijo.md, pero el hijo muy depletado queda en -10,9% del rendimiento virgen (IC 95%: -33,4% a 11,6%): el IC incluye cero y el punto supera el 5% del virgen. Con este dato no se puede afirmar ni descartar una degradación del hijo.

- Muy depletado contra virgen, dentro de celdas de 2 km: -9,2 bbl por metro de rama (IC 95%: -28,1 a 9,8), o sea -10,9% del rendimiento virgen (IC 95%: -33,4% a 11,6%), sobre 1.612 hijos en 265 celdas.
- Rendimiento de los hijos en zona virgen a 12 meses: mediana de 84,2 bbl por metro de rama.
- Control negativo, muy depletado contra virgen: 7,0 bbl por metro de rama (IC 95%: -3,3 a 17,3). Es nulo. El del grupo poco depletado, que la regla no usa, da 8,1 (IC 95%: 0,9 a 15,4), que no es nulo: el control queda limpio solo en el grupo que decide, y aun ahí su punto es positivo.
- Cota superior de la pérdida del hijo muy depletado: 28,1 bbl por metro de rama, o 33,4% del rendimiento virgen. Es la mayor pérdida compatible con el dato público (límite bajo del IC), no una estimación.
- Celdas que comparan: 53 celdas tienen a la vez hijos virgen y muy depletados, con 715 de los 1.612 hijos; las demás aportan a los controles pero no a la comparación.
- Con celdas de 5 km (descriptivo) el muy depletado da 0,6 bbl por metro (IC 95%: -6,0 a 7,2); con celdas de 1 km, -11,1 (IC 95%: -44,0 a 21,7). El signo depende del tamaño de la celda y ningún IC excluye cero.
- Dentro de las celdas, el hijo muy depletado es de cohorte más reciente (año medio 2022,93 contra 2021,89), con más etapas (42,4 contra 40,3) y más pozos alrededor (15,4 contra 7,2); el modelo los controla, pero cambios de práctica propios de un lugar quedan confundidos con la depleción.

## Qué le dice a un operador

Con datos públicos, la degradación del hijo no se puede medir con precisión útil: el punto dice que un hijo muy depletado rinde algo menos que uno en zona virgen del mismo lugar, pero el intervalo va de una pérdida grande a una ganancia. Lo que lo resolvería es dato interno: espaciamiento real entre ramas, zona de aterrizaje, trayectorias y presiones de reservorio al fracturar el hijo.

## Regla fijada antes de correr

Muestra, exposición, grupos y resultado son los de [hijo.md](hijo.md). Cambia el modelo: efectos fijos de un cuadrado de 2 km de una grilla fija, indicadores de año del primer petróleo, rama, arena por metro, etapas, operador y densidad final (pozos de shale a menos de 1 km en cualquier fecha), con errores agrupados por celda. El control negativo usa la misma exposición de pozos posteriores a la ventana del hijo. Veredicto con la regla de hijo.md; además se exigen 30 celdas con hijos virgen y muy depletados. Si el control negativo es nulo se publica el límite bajo del IC como cota superior de la pérdida.

## Coeficientes

Diferencia de petróleo de 12 meses por metro de rama contra el grupo virgen (en el modelo continuo, por cada 100 bbl por metro de exposición), en bbl por metro, y en porcentaje de la mediana del virgen. IC de 95%; los errores se agrupan por celda salvo en la fila de errores por pad. Solo la fila principal del grupo muy depletado y su control negativo deciden.

| Modelo | Término | Coeficiente (bbl/m) | % del virgen | IC 95% (bbl/m) | Hijos | Conglomerados | p |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| Principal (celdas de 2 km) | poco depletado | -2,9 | -3,4 | -10,5 a 4,8 | 1.612 | 265 | 0,461 |
| Principal (celdas de 2 km) | muy depletado | -9,2 | -10,9 | -28,1 a 9,8 | 1.612 | 265 | 0,342 |
| Control negativo | poco depletado | 8,1 | 9,7 | 0,9 a 15,4 | 1.612 | 265 | 0,028 |
| Control negativo | muy depletado | 7,0 | 8,3 | -3,3 a 17,3 | 1.612 | 265 | 0,181 |
| Celdas de 1 km | poco depletado | -6,5 | -7,8 | -21,6 a 8,6 | 1.612 | 357 | 0,396 |
| Celdas de 1 km | muy depletado | -11,1 | -13,2 | -44,0 a 21,7 | 1.612 | 357 | 0,507 |
| Celdas de 5 km | poco depletado | -1,3 | -1,6 | -6,6 a 4,0 | 1.612 | 132 | 0,625 |
| Celdas de 5 km | muy depletado | 0,6 | 0,7 | -6,0 a 7,2 | 1.612 | 132 | 0,861 |
| Sin densidad final | poco depletado | -2,9 | -3,5 | -10,6 a 4,8 | 1.612 | 265 | 0,458 |
| Sin densidad final | muy depletado | -8,7 | -10,3 | -27,2 a 9,8 | 1.612 | 265 | 0,356 |
| Errores por pad | poco depletado | -2,9 | -3,4 | -10,2 a 4,4 | 1.612 | 481 | 0,442 |
| Errores por pad | muy depletado | -9,2 | -10,9 | -27,5 a 9,2 | 1.612 | 481 | 0,326 |
| Continua | por 100 bbl/m | -0,4 | -0,5 | -1,3 a 0,5 | 1.612 | 265 | 0,370 |
| Continua, control negativo | por 100 bbl/m | -0,2 | -0,2 | -0,4 a 0,1 | 1.612 | 265 | 0,153 |

## Equilibrio dentro de las celdas

Medias por grupo de exposición real y p de la prueba conjunta (Wald, errores por celda) de que los grupos poco y muy depletado no difieren del virgen dentro de las celdas de 2 km. Descriptivo: no condiciona el veredicto. Un p de 0,000 es menor que 0,0005.

| Variable | Virgen | Poco depletado | Muy depletado | p dentro de celdas |
| --- | ---: | ---: | ---: | ---: |
| Rama horizontal (m) | 2.580 | 2.512 | 2.606 | 0,000 |
| Etapas | 40,3 | 39,4 | 42,4 | 0,000 |
| Arena por metro (tn/m) | 3,68 | 3,50 | 3,76 | 0,000 |
| Cohorte (año del primer petróleo) | 2021,89 | 2021,24 | 2022,93 | 0,000 |
| Pozos a menos de 1 km (cualquier fecha) | 7,2 | 10,3 | 15,4 | 0,000 |

## Límites

- Los de [hijo.md](hijo.md): distancia de superficie, espaciamiento no observado, asociación y no causa, pozos recientes fuera.
- Dentro de una celda, el hijo depletado es casi siempre el que se fracturó después. El año se controla, pero cambios de práctica dentro del año o propios de un lugar se confunden con la depleción.
- El diseño se eligió después de ver el control negativo de hijo.md; se publican todos los modelos calculados, favorables o no, y los IC no tienen ajuste por comparaciones múltiples.
