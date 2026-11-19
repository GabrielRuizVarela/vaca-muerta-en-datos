# Hijos cerca de pozos depletados, dentro de celdas de 2 km

Página generada por `pipeline/hijo_celdas.py`. Repite la pregunta de [Hijos cerca de pozos depletados](hijo.md) comparando hijos del mismo cuadrado de 2 km: el que se fracturó cuando sus vecinos ya habían producido mucho contra el que se fracturó en zona virgen, con el año del primer petróleo, el diseño de la fractura, el operador y la densidad final de pozos alrededor como controles. Este diseño se fijó después de ver el resultado de [hijo.md](hijo.md), que quedó no firme porque su control negativo no es nulo; la regla se escribió antes de calcular nada con él y no cambia el veredicto de `hijo_depletado`.

## Resumen

Veredicto contra la regla fijada: **no firme**. La regla no permite concluir en ningún sentido. El control negativo del grupo que decide ahora es nulo, a diferencia de hijo.md, pero el hijo muy depletado queda en -11,2% del rendimiento virgen (IC 95%: -33,8% a 11,5%): el IC incluye cero y el punto supera el 5% del virgen. Con este dato no se puede afirmar ni descartar una degradación del hijo.

- Muy depletado contra virgen, dentro de celdas de 2 km: -9,4 bbl por metro de rama (IC 95%: -28,3 a 9,6), o sea -11,2% del rendimiento virgen (IC 95%: -33,8% a 11,5%), sobre 1.585 hijos en 261 celdas.
- Rendimiento de los hijos en zona virgen a 12 meses: mediana de 83,9 bbl por metro de rama.
- Control negativo, muy depletado contra virgen: 8,7 bbl por metro de rama (IC 95%: -1,4 a 18,9). Es nulo. El del grupo poco depletado, que la regla no usa, da 9,4 (IC 95%: 2,1 a 16,7), que no es nulo: el control queda limpio solo en el grupo que decide, y aun ahí su punto es positivo.
- Cota superior de la pérdida del hijo muy depletado: 28,3 bbl por metro de rama, o 33,8% del rendimiento virgen. Es la mayor pérdida compatible con el dato público (límite bajo del IC), no una estimación.
- Celdas que comparan: 52 celdas tienen a la vez hijos virgen y muy depletados, con 707 de los 1.585 hijos; las demás aportan a los controles pero no a la comparación.
- Con celdas de 5 km (descriptivo) el muy depletado da 1,2 bbl por metro (IC 95%: -5,2 a 7,6); con celdas de 1 km, -11,8 (IC 95%: -44,6 a 21,1). El signo depende del tamaño de la celda y ningún IC excluye cero.
- Dentro de las celdas, el hijo muy depletado es de cohorte más reciente (año medio 2022,92 contra 2021,81), con más etapas (42,3 contra 39,7) y más pozos alrededor (15,3 contra 7,2); el modelo los controla, pero cambios de práctica propios de un lugar quedan confundidos con la depleción.

## Qué le dice a un operador

Con datos públicos, la degradación del hijo no se puede medir con precisión útil: el punto dice que un hijo muy depletado rinde algo menos que uno en zona virgen del mismo lugar, pero el intervalo va de una pérdida grande a una ganancia. Lo que lo resolvería es dato interno: espaciamiento real entre ramas, zona de aterrizaje, trayectorias y presiones de reservorio al fracturar el hijo.

## Regla fijada antes de correr

Muestra, exposición, grupos y resultado son los de [hijo.md](hijo.md). Cambia el modelo: efectos fijos de un cuadrado de 2 km de una grilla fija, indicadores de año del primer petróleo, rama, arena por metro, etapas, operador y densidad final (pozos de shale a menos de 1 km en cualquier fecha), con errores agrupados por celda. El control negativo usa la misma exposición de pozos posteriores a la ventana del hijo. Veredicto con la regla de hijo.md; además se exigen 30 celdas con hijos virgen y muy depletados. Si el control negativo es nulo se publica el límite bajo del IC como cota superior de la pérdida.

## Coeficientes

Diferencia de petróleo de 12 meses por metro de rama contra el grupo virgen (en el modelo continuo, por cada 100 bbl por metro de exposición), en bbl por metro, y en porcentaje de la mediana del virgen. IC de 95%; los errores se agrupan por celda salvo en la fila de errores por pad. Solo la fila principal del grupo muy depletado y su control negativo deciden.

| Modelo | Término | Coeficiente (bbl/m) | % del virgen | IC 95% (bbl/m) | Hijos | Conglomerados | p |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| Principal (celdas de 2 km) | poco depletado | -2,7 | -3,3 | -10,4 a 5,0 | 1.585 | 261 | 0,486 |
| Principal (celdas de 2 km) | muy depletado | -9,4 | -11,2 | -28,3 a 9,6 | 1.585 | 261 | 0,333 |
| Control negativo | poco depletado | 9,4 | 11,2 | 2,1 a 16,7 | 1.585 | 261 | 0,012 |
| Control negativo | muy depletado | 8,7 | 10,4 | -1,4 a 18,9 | 1.585 | 261 | 0,092 |
| Celdas de 1 km | poco depletado | -6,8 | -8,1 | -22,1 a 8,5 | 1.585 | 352 | 0,384 |
| Celdas de 1 km | muy depletado | -11,8 | -14,0 | -44,6 a 21,1 | 1.585 | 352 | 0,483 |
| Celdas de 5 km | poco depletado | 0,5 | 0,6 | -4,1 a 5,1 | 1.585 | 132 | 0,830 |
| Celdas de 5 km | muy depletado | 1,2 | 1,5 | -5,2 a 7,6 | 1.585 | 132 | 0,705 |
| Sin densidad final | poco depletado | -2,8 | -3,3 | -10,5 a 5,0 | 1.585 | 261 | 0,483 |
| Sin densidad final | muy depletado | -9,0 | -10,7 | -27,5 a 9,5 | 1.585 | 261 | 0,342 |
| Errores por pad | poco depletado | -2,7 | -3,3 | -10,1 a 4,6 | 1.585 | 474 | 0,467 |
| Errores por pad | muy depletado | -9,4 | -11,2 | -27,7 a 9,0 | 1.585 | 474 | 0,318 |
| Continua | por 100 bbl/m | -0,5 | -0,6 | -1,4 a 0,4 | 1.585 | 261 | 0,291 |
| Continua, control negativo | por 100 bbl/m | -0,2 | -0,2 | -0,4 a 0,1 | 1.585 | 261 | 0,199 |

## Equilibrio dentro de las celdas

Medias por grupo de exposición real y p de la prueba conjunta (Wald, errores por celda) de que los grupos poco y muy depletado no difieren del virgen dentro de las celdas de 2 km. Descriptivo: no condiciona el veredicto. Un p de 0,000 es menor que 0,0005.

| Variable | Virgen | Poco depletado | Muy depletado | p dentro de celdas |
| --- | ---: | ---: | ---: | ---: |
| Rama horizontal (m) | 2.550 | 2.508 | 2.604 | 0,000 |
| Etapas | 39,7 | 39,3 | 42,3 | 0,000 |
| Arena por metro (tn/m) | 3,68 | 3,50 | 3,76 | 0,000 |
| Cohorte (año del primer petróleo) | 2021,81 | 2021,20 | 2022,92 | 0,000 |
| Pozos a menos de 1 km (cualquier fecha) | 7,2 | 10,4 | 15,3 | 0,000 |

## Límites

- Los de [hijo.md](hijo.md): distancia de superficie, espaciamiento no observado, asociación y no causa, pozos recientes fuera.
- Dentro de una celda, el hijo depletado es casi siempre el que se fracturó después. El año se controla, pero cambios de práctica dentro del año o propios de un lugar se confunden con la depleción.
- El diseño se eligió después de ver el control negativo de hijo.md; se publican todos los modelos calculados, favorables o no, y los IC no tienen ajuste por comparaciones múltiples.
