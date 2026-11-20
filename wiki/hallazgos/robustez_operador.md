# Robustez por operador y por área: sacar de a uno

Se saca de a un grupo (el operador o el área del pozo padre) y se vuelve a medir la brecha del mes 1 (cercanos a menos de 1 km menos controles a 2 a 5 km, todas las edades, mediana del índice) y la del mes 6. Es una prueba de que ningún grupo grande produce el resultado por sí solo; no mueve el veredicto del estudio de eventos.

## Sacando de a un operador

La brecha del mes 1 se sostiene al sacar de a un operador: en las 7 salidas el IC 95% excluye el cero y la brecha puntual queda entre -24,1 y -22,2 puntos; el peor caso es sin Chevron (-22,2 puntos, IC 95% -26,1 a -17,6, cota superior -17,6). El cierre del mes 6 se sostiene: la brecha puntual del mes 6 queda entre -3,6 y -1,0 puntos, sin pasar de -5,0; el peor caso es sin Tecpetrol (-3,6 puntos).

| Sin | Eventos cercanos (mes 1) | Eventos control (mes 1) | Brecha mes 1 (puntos) | IC 95% | Brecha mes 6 (puntos) | IC 95% |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| (muestra completa) | 2.094 | 18.291 | -23,0 | -27,1 a -18,6 | -2,1 | -5,9 a 0,9 |
| Chevron | 2.035 | 18.205 | -22,2 | -26,1 a -17,6 | -2,0 | -6,0 a 1,1 |
| Pan American Energy | 1.973 | 17.889 | -23,2 | -27,5 a -19,2 | -1,0 | -4,8 a 2,0 |
| Pluspetrol | 1.968 | 17.687 | -23,0 | -27,8 a -17,8 | -1,6 | -5,6 a 1,7 |
| Shell | 2.023 | 17.446 | -23,1 | -27,5 a -17,3 | -2,1 | -5,8 a 1,2 |
| Tecpetrol | 1.940 | 17.270 | -23,0 | -26,8 a -18,2 | -3,6 | -7,1 a -0,2 |
| Vista | 1.914 | 17.072 | -24,1 | -29,1 a -19,5 | -2,8 | -6,7 a 0,9 |
| YPF | 756 | 4.450 | -23,0 | -29,8 a -15,5 | -2,7 | -7,9 a 1,8 |

Agregado después de ver los resultados (no cambia el veredicto): la cota superior más alta del IC 95% de la brecha del mes 1 entre las salidas es -15,5 puntos, sin YPF.

## Sacando de a un área

La brecha del mes 1 se sostiene al sacar de a un área: en las 9 salidas el IC 95% excluye el cero y la brecha puntual queda entre -29,3 y -20,2 puntos; el peor caso es sin LA AMARGA CHICA (-20,2 puntos, IC 95% -24,2 a -15,3, cota superior -15,3). El cierre del mes 6 se sostiene: la brecha puntual del mes 6 queda entre -3,6 y -1,0 puntos, sin pasar de -5,0; el peor caso es sin FORTIN DE PIEDRA (-3,6 puntos).

| Sin | Eventos cercanos (mes 1) | Eventos control (mes 1) | Brecha mes 1 (puntos) | IC 95% | Brecha mes 6 (puntos) | IC 95% |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| (muestra completa) | 2.094 | 18.291 | -23,0 | -27,1 a -18,6 | -2,1 | -5,9 a 0,9 |
| BAJADA DEL PALO OESTE | 1.928 | 17.229 | -24,0 | -29,3 a -19,3 | -2,9 | -6,6 a 0,8 |
| BAJO DEL CHOIQUE - LA INVERNADA | 2.036 | 18.195 | -23,3 | -27,5 a -18,1 | -2,4 | -6,3 a 0,7 |
| BANDURRIA SUR | 1.936 | 16.728 | -22,7 | -27,1 a -17,3 | -1,5 | -5,7 a 1,2 |
| EL TRAPIAL ESTE | 2.035 | 18.205 | -22,2 | -26,1 a -17,6 | -2,0 | -6,0 a 1,1 |
| FORTIN DE PIEDRA | 1.940 | 17.280 | -23,0 | -26,9 a -18,6 | -3,6 | -7,0 a 0,1 |
| LA AMARGA CHICA | 1.778 | 15.355 | -20,2 | -24,2 a -15,3 | -1,7 | -6,2 a 1,5 |
| LA CALERA | 2.026 | 17.783 | -22,8 | -27,1 a -17,8 | -1,4 | -5,3 a 1,4 |
| LINDERO ATRAVESADO | 1.997 | 18.030 | -23,5 | -28,2 a -19,1 | -1,0 | -5,2 a 2,8 |
| LOMA CAMPANA | 1.306 | 9.555 | -29,3 | -35,1 a -23,2 | -3,2 | -7,3 a 0,9 |

Agregado después de ver los resultados (no cambia el veredicto): la cota superior más alta del IC 95% de la brecha del mes 1 entre las salidas es -15,3 puntos, sin LA AMARGA CHICA.

## Regla fijada antes de correr

- Se saca de a uno cada operador y cada área con al menos 50 eventos cercanos con índice del mes 1 observado (un conteo, no un resultado).
- La brecha del mes 1 se sostiene si en todas las salidas el IC 95% excluye el cero y la brecha puntual queda al menos en la mitad de la completa.
- El cierre del mes 6 se sostiene si en todas las salidas la brecha del mes 6 queda por encima de -5,0 puntos; ese umbral se fijó conociendo la brecha completa del mes 6.
- Mismo marco, mismas repeticiones y misma semilla que el estudio de placebo.

## Colorado

El nulo de dosis no se replica en el Colorado: el dato público de esa cuenca no trae arena, etapas ni presión de tratamiento (las tres columnas quedan nulas en `pipeline/colorado/sql/02_core.sql`), y sin esas variables no hay con qué repetir el modelo. No se simula ni se imputa nada.

## Qué no prueba

- No prueba que otro operador u otra práctica de pad tenga la misma brecha; prueba que ninguno de estos grupos por sí solo la produce.
- Los grupos con menos de 50 eventos cercanos no se sacan solos y no hay corrección por comparaciones múltiples entre las salidas.
- Los IC conservan la dependencia por pad hijo pero no la de un mismo padre en varios eventos.
- El operador es el del padre del evento, no el del hijo: en una parte de los eventos control el hijo es de otro operador, así que sacar un operador saca sus padres y no necesariamente sus hijos.
