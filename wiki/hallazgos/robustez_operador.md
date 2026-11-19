# Robustez por operador y por área: sacar de a uno

Se saca de a un grupo (el operador o el área del pozo padre) y se vuelve a medir la brecha del mes 1 (cercanos a menos de 1 km menos controles a 2 a 5 km, todas las edades, mediana del índice) y la del mes 6. Es una prueba de que ningún grupo grande produce el resultado por sí solo; no mueve el veredicto del estudio de eventos.

## Sacando de a un operador

La brecha del mes 1 se sostiene al sacar de a un operador: en las 7 salidas el IC 95% excluye el cero y la brecha puntual queda entre -24,0 y -22,1 puntos; el peor caso es sin Chevron (-22,1 puntos, IC 95% -26,2 a -17,1, cota superior -17,1). El cierre del mes 6 se sostiene: la brecha puntual del mes 6 queda entre -3,6 y -1,0 puntos, sin pasar de -5,0; el peor caso es sin Tecpetrol (-3,6 puntos).

| Sin | Eventos cercanos (mes 1) | Eventos control (mes 1) | Brecha mes 1 (puntos) | IC 95% | Brecha mes 6 (puntos) | IC 95% |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| (muestra completa) | 2.077 | 18.262 | -22,9 | -26,7 a -19,1 | -2,1 | -5,8 a 1,1 |
| Chevron | 2.018 | 18.176 | -22,1 | -26,2 a -17,1 | -2,0 | -5,7 a 1,2 |
| Pan American Energy | 1.956 | 17.860 | -23,0 | -27,6 a -18,2 | -1,0 | -5,7 a 2,1 |
| Pluspetrol | 1.965 | 17.666 | -22,9 | -28,0 a -18,0 | -1,7 | -5,8 a 1,3 |
| Shell | 2.006 | 17.417 | -22,8 | -28,2 a -17,8 | -2,0 | -5,8 a 1,0 |
| Tecpetrol | 1.923 | 17.241 | -22,8 | -27,3 a -17,8 | -3,6 | -7,4 a 0,3 |
| Vista | 1.897 | 17.045 | -24,0 | -28,9 a -19,3 | -2,9 | -7,4 a 1,2 |
| YPF | 739 | 4.438 | -22,6 | -28,7 a -14,8 | -2,7 | -7,3 a 1,7 |

Agregado después de ver los resultados (no cambia el veredicto): la cota superior más alta del IC 95% de la brecha del mes 1 entre las salidas es -14,8 puntos, sin YPF.

## Sacando de a un área

La brecha del mes 1 se sostiene al sacar de a un área: en las 8 salidas el IC 95% excluye el cero y la brecha puntual queda entre -29,3 y -20,0 puntos; el peor caso es sin LA AMARGA CHICA (-20,0 puntos, IC 95% -24,2 a -15,3, cota superior -15,3). El cierre del mes 6 se sostiene: la brecha puntual del mes 6 queda entre -3,6 y -1,0 puntos, sin pasar de -5,0; el peor caso es sin FORTIN DE PIEDRA (-3,6 puntos).

| Sin | Eventos cercanos (mes 1) | Eventos control (mes 1) | Brecha mes 1 (puntos) | IC 95% | Brecha mes 6 (puntos) | IC 95% |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| (muestra completa) | 2.077 | 18.262 | -22,9 | -26,7 a -19,1 | -2,1 | -5,8 a 1,1 |
| BAJADA DEL PALO OESTE | 1.911 | 17.200 | -23,8 | -28,5 a -20,0 | -2,9 | -7,3 a 1,1 |
| BANDURRIA SUR | 1.919 | 16.699 | -22,3 | -27,3 a -17,2 | -1,6 | -5,8 a 1,6 |
| EL TRAPIAL ESTE | 2.018 | 18.176 | -22,1 | -26,2 a -17,1 | -2,0 | -5,7 a 1,2 |
| FORTIN DE PIEDRA | 1.923 | 17.251 | -22,8 | -26,1 a -17,9 | -3,6 | -7,2 a 0,2 |
| LA AMARGA CHICA | 1.761 | 15.326 | -20,0 | -24,2 a -15,3 | -1,5 | -5,3 a 1,7 |
| LA CALERA | 2.009 | 17.754 | -22,5 | -27,6 a -17,6 | -1,5 | -5,5 a 1,3 |
| LINDERO ATRAVESADO | 1.980 | 18.001 | -23,3 | -28,5 a -18,9 | -1,0 | -5,3 a 1,9 |
| LOMA CAMPANA | 1.289 | 9.526 | -29,3 | -35,5 a -23,6 | -3,2 | -7,7 a 0,7 |

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
