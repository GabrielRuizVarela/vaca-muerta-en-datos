# Replicación por operador dentro de Vaca Muerta

Se mide la brecha del mes 1 (eventos cercanos a menos de 1 km menos controles a 2 a 5 km, mediana del índice) operador por operador, con los eventos cuyo padre es de ese operador en las dos bandas. Es la otra mitad de la prueba de sacar de a uno ([robustez_operador.md](robustez_operador.md)): allá se prueba que ningún operador produce la brecha por sí solo; acá, si la brecha aparece dentro de cada uno.

**Se replica en 5 de 7 operadores: YPF (se replica); Vista (se replica); Tecpetrol (no se replica: el placebo de fechas también da brecha); Pluspetrol (se replica); Pan American Energy (no se replica: el placebo de fechas también da brecha); Shell (se replica); Chevron (se replica).**

| Operador | Eventos cercanos | Eventos control | Brecha mes 1 (puntos) | IC 95% | Brecha previa (puntos) | Placebo de fechas (puntos) | Placebo, IC alto | Lectura |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| YPF | 1.338 | 13.841 | -23,5 | -29,5 a -17,5 | -8,5 | -3,0 | 0,9 | se replica |
| Vista | 180 | 1.219 | -9,2 | -22,3 a -2,9 | 6,6 | 7,5 | 14,0 | se replica |
| Tecpetrol | 154 | 1.021 | -25,6 | -46,2 a -7,1 | -5,7 | -15,2 | -1,5 | no se replica: el placebo de fechas también da brecha |
| Pluspetrol | 126 | 604 | -24,8 | -63,9 a -12,3 | 0,4 | 12,4 | 24,2 | se replica |
| Pan American Energy | 121 | 402 | -19,6 | -35,5 a -14,1 | -15,8 | -11,9 | -5,5 | no se replica: el placebo de fechas también da brecha |
| Shell | 71 | 845 | -20,6 | -29,6 a -1,1 | -4,0 | -3,6 | 7,1 | se replica |
| Chevron | 59 | 86 | -113,6 | -198,0 a -47,0 | -8,7 | -58,8 | 7,0 | se replica |

## Regla fijada antes de calcular

Fijada en el commit `de19052` (2026-11-27), antes de calcular ninguna brecha de un operador medido solo con sus eventos; el texto y las constantes están en `pipeline/replicacion_operadores.py` y en `docs/reglas-fijadas.md`.

- Se miden los operadores con al menos 50 eventos cercanos con índice del mes 1 observado (el conjunto de `pipeline.robustez_operador`, elegido por conteo y no por resultado).
- Un operador se replica si el IC 95% de su brecha del mes 1 queda entero bajo cero, su brecha previa limpia es menor en valor absoluto y su placebo de fechas (hijo corrido 12 meses antes) no da una brecha entera bajo cero.
- No se pudo medir con menos de 50 eventos de control con índice del mes 1 observado, o sin valor en la brecha, su IC, la brecha previa o el IC del placebo; cuenta en n con su motivo.
- La lectura de la familia es un recuento: no hay promedio, peso ni estimación conjunta, y se publica cualquiera sea k.

## Qué no prueba

- Dentro de un operador cambian el área y el año, así que la brecha por operador no separa al operador de su área.
- k de n es un recuento, no una prueba conjunta: cada operador se lee a 95% por separado.
- Un mismo padre puede estar en varios eventos; la clave de pad hijo no separa esa dependencia.
- El placebo de fechas se lee de una cola, como dice la regla: una brecha del placebo entera sobre cero no anula la réplica. La lectura con dos colas, fijada después de ver estas cifras, está en [replicacion_operadores_agua.md](replicacion_operadores_agua.md), con su etiqueta post hoc.
