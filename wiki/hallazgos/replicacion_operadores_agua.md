# Replicación del corte de agua por operador

Se mide el corte de agua de D2 (ATT_W, en puntos porcentuales) operador por operador, con solo los tratados y solo los controles de ese operador en cada celda, y con sus propios placebos. Es la pregunta de [replicacion_operadores.md](replicacion_operadores.md) aplicada al agua, el único resultado con lectura causal, que en D6 ([causal_profundo.md](causal_profundo.md)) depende de YPF.

## Cómo se lee

La regla se fijó en el commit `b1479a8` (2026-11-27), antes de calcular ninguna de estas cifras; el texto y las constantes están en `pipeline/replicacion_operadores_agua.py` y en `docs/reglas-fijadas.md`. Se miden los operadores con 50 o más tratados en las celdas de D2. Un operador se replica si ninguno de sus tres placebos (previo, fecha falsa y distancia falsa, sobre sus celdas propias) rompe y el IC 95% de su ATT_W queda entero sobre cero. Un placebo rompe si su IC excluye el cero, de cualquier lado, y su valor absoluto llega a 2 puntos (dos colas). No se pudo medir con menos de 50 tratados con dW o con algún valor faltante. Si el extremo bajo del IC pasa además 2 puntos (el umbral del veredicto de D2) se publica como dato, sin lectura.

**Se replica en 1 de 4 operadores: YPF (se replica); Pluspetrol (no se pudo medir: 12 tratados con dW en las celdas propias, menos de 50); Tecpetrol (no se pudo medir: 3 tratados con dW en las celdas propias, menos de 50); Vista (no se pudo medir: 1 tratado con dW en las celdas propias, menos de 50).**

Donde no se pudo medir, la tabla no muestra el ATT_W, su IC ni los placebos: salen de muy pocos pozos. Quedan en `mart_replicacion_operadores_agua`.

| Operador | Tratados en D2 | Tratados / controles propios | ATT_W (puntos) | IC 95% | Pasa el umbral de D2 | Placebo previo (IC) | Placebo fecha falsa (IC) | Placebo distancia falsa (IC) | Lectura |
| --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- |
| YPF | 389 | 206 / 572 | 14,7 | 7,1 a 20,7 | sí | 2,4 (-1,6 a 6,2) | -0,1 (-2,2 a 1,5) | 2,5 (-4,2 a 8,9) | se replica |
| Pluspetrol | 61 | 12 / 23 | n/d | n/d | n/d | n/d | n/d | n/d | no se pudo medir: 12 tratados con dW en las celdas propias, menos de 50 |
| Tecpetrol | 55 | 3 / 7 | n/d | n/d | n/d | n/d | n/d | n/d | no se pudo medir: 3 tratados con dW en las celdas propias, menos de 50 |
| Vista | 52 | 1 / 8 | n/d | n/d | n/d | n/d | n/d | n/d | no se pudo medir: 1 tratado con dW en las celdas propias, menos de 50 |

## Petróleo: el placebo de fechas leído con dos colas (post hoc)

Esta lectura se fijó después de ver las cifras: el placebo de fechas de [replicacion_operadores.md](replicacion_operadores.md) se leía de una cola, y sus extremos ya se conocían. No cambia el 5 de 7 de la regla de `de19052`, que sigue siendo la cifra que se cita; se publica al lado, con esta etiqueta. Con dos colas el placebo rompe si su IC 95% excluye el cero de cualquier lado.

**Con el placebo de dos colas, se replica en 3 de 7 operadores: YPF (se replica con dos colas); Vista (no se replica con dos colas: el placebo de fechas da brecha de un lado); Tecpetrol (no se replica: el placebo de fechas también da brecha); Pluspetrol (no se replica con dos colas: el placebo de fechas da brecha de un lado); Pan American Energy (no se replica: el placebo de fechas también da brecha); Shell (se replica con dos colas); Chevron (se replica con dos colas).**

| Operador | Placebo de fechas (puntos) | IC 95% | Rompe con dos colas | Se replica (de19052) | Se replica con dos colas | Lectura |
| --- | ---: | --- | --- | --- | --- | --- |
| YPF | -3,0 | -6,4 a 0,9 | no | sí | sí | se replica con dos colas |
| Vista | 7,5 | 1,4 a 14,0 | sí | sí | no | no se replica con dos colas: el placebo de fechas da brecha de un lado |
| Tecpetrol | -15,2 | -25,0 a -1,5 | sí | no | no | no se replica: el placebo de fechas también da brecha |
| Pluspetrol | 12,4 | 3,3 a 24,2 | sí | sí | no | no se replica con dos colas: el placebo de fechas da brecha de un lado |
| Pan American Energy | -11,9 | -18,1 a -5,5 | sí | no | no | no se replica: el placebo de fechas también da brecha |
| Shell | -3,6 | -14,0 a 7,1 | no | sí | sí | se replica con dos colas |
| Chevron | -58,8 | -308,8 a 7,0 | no | sí | sí | se replica con dos colas |

## Qué no prueba

- Dentro de un operador cambian el área y el año, así que el ATT_W por operador no separa al operador de su área.
- k de n es un recuento, no una prueba conjunta: cada operador se lee a 95% por separado, sin ajuste por comparaciones múltiples.
- Con solo sus propios controles, un operador chico pierde celdas, y su IC es más ancho que el del corte de D6.
