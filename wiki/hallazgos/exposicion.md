# Exposición: operador por área (D12)

¿El efecto del golpe sobre el corte de agua es de YPF o de la composición de pozos? Para responderlo, D12 vuelve a estimar el D2 dentro de celdas de operador y área: cada pozo golpeado se compara solo con controles del mismo operador y la misma área del mismo mes y la misma edad. La regla se fijó en 857d434 antes de calcular ninguna cifra ("regla fijada en 857d434 antes de calcular"), y los sorteos son los de D2 y D6, así que los números se pueden comparar.

| Resultado | dW (puntos porcentuales) | IC 95 % | Tratados | Celdas | Parte de los tratados de D2 |
|---|---|---|---|---|---|
| D12a, todos los tratados | +14,2 | +0,6 a +21,5 | 89 | 26 | 20 % |
| D12b, sin YPF | +11,0 | -1,0 a +22,9 | 6 | 2 | 1 % |
| D12c, solo YPF | +14,5 | -0,1 a +22,0 | 83 | 24 | 19 % |

- **D12a (dentro de operador y área):** sin muestra.
- **D12b (fuera de YPF):** sin muestra.

**Lo que no dice:** comparar dentro de cada celda saca la composición entre operadores y entre áreas, pero no la que queda adentro de cada operador y área.

## D10: golpes repetidos

Un pozo golpeado puede recibir otro golpe unos meses después, y entonces no sabés cuál de los dos mueve el agua. D10 repite la serie por mes de D5 sacando, desde el mes del segundo golpe, a todo tratado que recibe otro golpe a menos de 1 km entre los meses 2 y 12 después del primero (el mes 1 no cuenta: un pad que se fractura entre dos meses es el mismo evento). Los controles no tienen golpe a 2 km en toda la ventana. La regla se fijó en 857d434 antes de calcular ninguna cifra ("regla fijada en 857d434 antes de calcular").

| Mes desde el golpe (e) | dW (puntos porcentuales) | IC 95 % | Tratados que quedan |
|---|---|---|---|
| -6 | -1,1 | -2,6 a +0,5 | 335 |
| -5 | +0,2 | -0,6 a +1,0 | 335 |
| -4 | +0,9 | -0,6 a +2,0 | 332 |
| -3 | +0,9 | -0,9 a +2,7 | 325 |
| -2 | +1,3 | -0,6 a +3,2 | 329 |
| -1 | +2,3 | -0,2 a +5,1 | 319 |
| 0 | +4,7 | +1,7 a +8,3 | 292 |
| 1 | +17,8 | +12,3 a +25,2 | 296 |
| 2 | +18,0 | +12,9 a +24,1 | 291 |
| 3 | +15,4 | +11,6 a +20,2 | 296 |
| 4 | +14,5 | +10,9 a +19,5 | 274 |
| 5 | +13,0 | +9,7 a +18,4 | 280 |
| 6 | +14,1 | +10,3 a +19,3 | 267 |
| 7 | +11,7 | +8,1 a +16,9 | 278 |
| 8 | +10,5 | +6,3 a +15,5 | 262 |
| 9 | +11,3 | +6,6 a +17,5 | 258 |
| 10 | +8,4 | +3,5 a +15,0 | 254 |
| 11 | +8,5 | +3,4 a +14,0 | 256 |
| 12 | +8,9 | +3,4 a +13,9 | 241 |

- Media de dW entre los meses 6 y 12 (serie a 1 km): +10,5 (IC +6,8 a +15,4), con 241 tratados como mínimo; media de los meses 0 y 1: +11,2.
- Misma serie censurada a 2 km (la cuenta de D5, sin veredicto): media tardía +10,0 (IC +6,3 a +14,6), con 169 tratados como mínimo.
- Tratados que salen de la serie antes del mes 12: 62 de 341 a 1 km y 142 de 341 a 2 km.
- **Veredicto de D10: persiste.**

**Lo que no dice:** la censura no es al azar (los padres de zonas de relleno reciben más hijos); la serie censurada mide la primera fractura sola en los padres que no recibieron otra, no en todos.

## D11: exposición por rama y anillos

El golpe se mide por la distancia entre bocas de pozo, pero lo que pasa bajo tierra depende de cuánto se acercan las ramas horizontales. D11 hace tres cosas con los tratados de D2: parte el efecto según la distancia mínima entre las dos ramas (D11a), vuelve a estimarlo sin los controles que tienen una rama cerca de otro pozo recién fracturado (D11b) y mira anillos de distancia de boca más lejanos que los de D2 para ver si el efecto llega más lejos (D11c). La regla se fijó en 857d434 antes de calcular ninguna cifra ("regla fijada en 857d434 antes de calcular").

**D11a, dosis por rama.** La distancia de cada tratado es la menor distancia entre ramas con sus hijos del mes del golpe a menos de 1 km; solo entran los golpes de 2016 a 2023. De 312 tratados de D2 en esos años, 279 (89 %) tienen distancia.

| Distancia entre ramas | dW (puntos porcentuales) | IC 95 % | Tratados |
|---|---|---|---|
| menos de 250 m | +26,3 | +15,6 a +36,7 | 41 |
| 250 m a 1 km | +14,0 | +8,1 a +19,2 | 198 |
| 1 km o más | -0,8 | -8,9 a +5,1 | 22 |
| 250 m o más (las dos bandas juntas) | +12,6 | +7,3 a +17,6 | 220 |
| Diferencia, menos de 250 m menos 250 m o más | +13,7 | +3,5 a +25,8 | |

- **Veredicto de D11a: sin muestra.**

**D11b, controles limpios por rama.** En la misma submuestra, se sacan de cada celda los controles con una rama a menos de 250 m de un hijo fracturado entre 12 meses antes y 6 después del golpe, y los que no tienen rama medida. Sin veredicto.

| Controles | dW (puntos porcentuales) | IC 95 % | Tratados | Controles |
|---|---|---|---|---|
| Todos los de D2 | +14,7 | +10,1 a +19,7 | 261 | 1283 |
| Sin rama cercana con hijo en la ventana ni sin rama medida | +14,4 | +9,4 a +19,6 | 250 | 1096 |
| Diferencia, limpios menos todos | -0,3 | -1,6 a +1,1 | | |

**D11c, anillos (Butts, 2021).** Cada cohorte es el primer mes en que el golpe más cercano cae en el anillo, sin golpes más cerca en la ventana; los controles no tienen golpe a menos de 5 km en la ventana. La fila de 0 a 1 km es D2 con esos controles limpios.

| Anillo (km del golpe más cercano) | dW (puntos porcentuales) | IC 95 % | Tratados | I(1) (puntos de índice) | IC 95 % | Tratados |
|---|---|---|---|---|---|---|
| 0 a 1 (los tratados de D2) | +10,9 | +0,3 a +25,4 | 72 | -24,3 | -46,6 a +1,7 | 90 |
| 1 a 2 | +2,2 | -5,8 a +12,5 | 130 | -5,9 | -31,4 a +17,9 | 145 |
| 2 a 3 | +0,6 | -5,0 a +8,1 | 68 | -20,8 | -39,9 a +11,4 | 80 |
| 3 a 5 | +4,7 | -4,4 a +13,5 | 70 | -5,1 | -31,5 a +38,0 | 83 |

- **Veredicto de D11c: sin muestra.**
- Mismo criterio sobre I(1), con el IC alto menor que cero (sin veredicto): sin muestra.

**Lo que no dice:** `m_min` es la geometría declarada de la rama, no la red de fracturas; la submuestra con rama es sobre todo de 2016 a 2023.

## D14: el golpe definido por la distancia entre ramas

D2 define el golpe por la distancia entre bocas de pozo (un hijo a menos de 1 km). D14 repite D2 definiendo el golpe por la distancia entre las ramas horizontales, que es la que importa bajo tierra: un padre es tratado si un hijo fracturado en su mes g tiene una rama a menos de 250 m de la suya, sin importar la distancia de boca (hasta 5 km), y solo entran los golpes de 2016 a 2023, los años en que hay ramas medidas. Los controles son los de D2 sin ninguna rama a menos de 1000 m ni hijo cercano sin rama medida en la ventana. D14 cambia solo la definición del golpe: usa la identificación de D2 y sus placebos son los de D2, no se repitieron. La regla se fijó en 5002094 (con su aclaración en f1b1e08) antes de calcular ninguna cifra ("regla fijada en 5002094 antes de calcular").

| Definición del golpe | ATT_W de dW (puntos porcentuales) | IC 95 % | Tratados | Controles | Celdas |
|---|---|---|---|---|---|
| D14: rama a menos de 250 m | +13,3 | +6,2 a +23,0 | 114 | 810 | 60 |
| D2 de 2016 a 2023: boca a menos de 1 km (sin veredicto) | +15,1 | +10,5 a +20,3 | 290 | 1440 | 79 |

- **Veredicto de D14: sin muestra.**
- Tratados de D14 que no son tratados de D2 de 2016 a 2023 en una celda con controles: 65.
- Tratados de D2 de 2016 a 2023 que no son tratados de D14: 242.
- Tratados en los dos: 64.
- Estos tres recuentos toman a todos los tratados de celdas con controles. La tabla cuenta solo a los que entran a la estimación, con el corte de agua medido y en celdas con suficientes controles que también lo tengan; por eso los recuentos suman más que los tratados de la tabla.

**Lo que no dice:** `m_min` es la distancia entre ramas medidas, no la geometría de la fractura; un hijo sin rama medida puede estar cerca igual (queda fuera de los controles, pero no de los otros golpes de un padre tratado); la ventana es solo 2016 a 2023.
