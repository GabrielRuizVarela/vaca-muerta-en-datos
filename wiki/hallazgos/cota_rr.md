# Cota de Rambachan y Roth: cuánto sesgo hace falta para borrar el efecto

Página generada por `pipeline/cota_rr.py`, regla fijada en el commit 857d434 antes de calcular.

La cota pregunta qué tan grande tendría que ser la violación de tendencias paralelas después del tratamiento, medida contra el mayor salto entre meses que ya se ve antes del tratamiento, para que el efecto deje de distinguirse de cero. Mbar es esa razón: con Mbar = 1 el sesgo puede saltar de un mes al siguiente tanto como el mayor salto previo; con Mbar = 0 no puede saltar. El conjunto identificado es el rango del efecto compatible con esa violación; el intervalo agrega la incertidumbre del bootstrap por bloques de 5 km (unión de los percentiles 2,5 y 97,5 de los extremos; esa unión no sale de una prueba con nivel conocido, así que no se sabe si es conservadora). El Mbar de quiebre es el menor Mbar con intervalo que contiene cero. Unidades: puntos de producción en D1 y puntos porcentuales de corte de agua en D2.

La misma pregunta con la prueba condicional e híbrida de Andrews, Roth y Pakes en lugar de la unión de bootstrap está en [cota_rr_condicional.md](cota_rr_condicional.md).

## D1, ATT(1)

Efecto estimado -25,8; previos b(-3) = -6,1, b(-2) = -3,6, b(-1) = -10,0; mayor salto previo m = 6,4; 468 tratados, 400 sorteos completos.

| Mbar | Conjunto identificado | Intervalo |
|---|---|---|
| 0,00 | -15,7 a -15,7 | -24,7 a -5,7 |
| 0,25 | -19,0 a -12,5 | -29,0 a 1,1 |
| 0,50 | -22,2 a -9,3 | -34,0 a 8,7 |
| 0,75 | -25,4 a -6,1 | -41,6 a 16,0 |
| 1,00 | -28,6 a -2,9 | -49,4 a 24,0 |
| 1,25 | -31,8 a 0,3 | -57,5 a 32,1 |
| 1,50 | -35,0 a 3,5 | -66,6 a 39,9 |
| 1,75 | -38,2 a 6,7 | -75,3 a 48,5 |
| 2,00 | -41,4 a 9,9 | -84,3 a 57,6 |

Mbar de quiebre: 0,20. Veredicto: **resiste solo con Mbar menor que 1**.

## D2, tau_W(1)

Efecto estimado 15,6; previos b(-3) = 1,1, b(-2) = 1,2, b(-1) = 1,0; mayor salto previo m = 1,1; 413 tratados, 400 sorteos completos.

| Mbar | Conjunto identificado | Intervalo |
|---|---|---|
| 0,00 | 14,6 a 14,6 | 10,7 a 19,7 |
| 0,25 | 14,0 a 15,2 | 9,9 a 20,7 |
| 0,50 | 13,5 a 15,7 | 9,1 a 22,1 |
| 0,75 | 12,9 a 16,3 | 8,0 a 23,4 |
| 1,00 | 12,4 a 16,8 | 6,7 a 25,1 |
| 1,25 | 11,8 a 17,4 | 5,1 a 27,0 |
| 1,50 | 11,3 a 18,0 | 3,8 a 28,6 |
| 1,75 | 10,7 a 18,5 | 2,2 a 30,6 |
| 2,00 | 10,1 a 19,1 | 0,5 a 32,6 |

Mbar de quiebre: mayor que 2,00. Veredicto: **resiste Mbar = 1**.

## D2, media tau_W(0,1)

Efecto estimado 9,7; previos b(-3) = 1,1, b(-2) = 1,2, b(-1) = 1,0; mayor salto previo m = 1,1; 410 tratados, 400 sorteos completos.

| Mbar | Conjunto identificado | Intervalo |
|---|---|---|
| 0,00 | 8,7 a 8,7 | 6,2 a 11,7 |
| 0,25 | 8,3 a 9,1 | 5,8 a 12,7 |
| 0,50 | 7,9 a 9,5 | 5,1 a 13,8 |
| 0,75 | 7,4 a 10,0 | 4,1 a 14,7 |
| 1,00 | 7,0 a 10,4 | 3,2 a 15,9 |
| 1,25 | 6,6 a 10,8 | 2,0 a 17,3 |
| 1,50 | 6,2 a 11,2 | 0,6 a 18,8 |
| 1,75 | 5,8 a 11,6 | -0,8 a 20,3 |
| 2,00 | 5,3 a 12,0 | -2,0 a 21,8 |

Mbar de quiebre: 1,62. Veredicto: **resiste Mbar = 1**.

## E, ATT(1)

La cota del estimador apilado la calcula `pipeline.stacked` con esta misma regla (c = 2) y queda en `mart_apilado` (fila `E_detalle`, `cota_quiebre`).

Mbar de quiebre: 0,32. Veredicto: **resiste solo con Mbar menor que 1**. El veredicto de E es «sin muestra», así que la cota no cambia lo que se publica del petróleo.

## Lo que queda como estaba

El veredicto de D1 ya fijado, que usa el M* simplificado de `pipeline/causal.py`, no cambia con esta cota y queda como registro. Esta cota lo reemplaza en el texto, no en lo que se fijó.

El estimando de máximo de D2 (W(g) o W(g+1), el mayor, menos la base) no es lineal en el efecto y no lleva esta cota.

## Lo que no dice

Supone que los meses previos no tienen efecto (sin anticipación). Con anticipación, restar b(-1) achica un efecto del mismo signo que la pretendencia y la cota es conservadora en ese caso, no en el contrario. El intervalo no es la prueba condicional e híbrida del paquete de Rambachan y Roth: es la unión de bootstrap fijada en la regla, y el máximo de los saltos previos no es suave cuando dos empatan.
