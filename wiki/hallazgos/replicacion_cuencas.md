# Replicación en otras cuencas: lectura de la familia

Página generada por `pipeline/familia.py` a partir del veredicto de cada cuenca. Cada cuenca se lee con la misma regla, fijada antes de bajar o medir nada de Wyoming (`pipeline/familia.py` y `pipeline/wyoming/__init__.py`): la brecha del mes 1 es negativa con el límite superior del IC 95% por bloques de 5 km menor que cero, y la brecha previa con base limpia (mes -1) es menor, en valor absoluto, que la del mes 1. Mismo estimador, mismos filtros, mismas semillas.

## Lectura

**Se replica en 1 de 2 cuencas: Colorado (se replica); Wyoming (no se replica).**

k cuenta las cuencas que se replican y n todas las de la familia, las que no se pudieran medir incluidas. No hay promedio, peso ni estimación conjunta: es la validez externa de la huella de Vaca Muerta medida cuenca por cuenca, no un efecto común.

## Por cuenca

| Cuenca | Hijos | Eventos cercanos | Controles | Brecha del mes 1 (puntos) | IC 95% por bloques de 5 km | Brecha previa, mes -1 (puntos) | Valor de la hipótesis | Lectura |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |
| Colorado | 4.789 | 3.691 | 53.326 | -19,9 | -27,5 a -14,8 | -6,9 | -0,130 | se replica |
| Wyoming | 1.163 | 353 | 2.286 | -2,5 | -5,5 a 2,2 | -11,9 | 0,095 | no se replica |

Cada fila es la de la página de la cuenca: [Colorado](replicacion.md), [Wyoming](replicacion_wyoming.md). El valor es el mayor entre el límite superior del IC y la diferencia de valores absolutos (previa menos mes 1); la cuenca se replica si es menor que cero.

## Qué no es

- No es una estimación conjunta ni una probabilidad: k de n no dice cuánto se espera que se replique en una cuenca nueva.
- Son 2 cuencas: una lectura de 2 no distingue entre una huella que depende de la cuenca y una que se mide con más o menos ruido en cada una.
- Las cuencas no miden lo mismo: la fecha del hijo es el inicio de fractura de FracFocus en Colorado y la primera terminación del regulador en Wyoming, y difieren la convención de reporte y la población de pozos. No se probó cuánto de una diferencia entre cuencas sale de eso, y no se afirma que lo explique. Si la terminación cae después de la fractura, el mes 0 de Wyoming queda corrido hacia adelante respecto del de Colorado y la lectura no separa "no hay huella" de "el mes 0 está corrido".
- Una cuenca que no se replica no refuta el resultado de Vaca Muerta ni una que se replica lo prueba: la lectura se publica entera y el resultado de Vaca Muerta queda con sus cifras.

En Wyoming, el IC por bloques de 5 km de la brecha del mes 1 incluye cero y la brecha previa es mayor, en valor absoluto, que la del mes 1: los padres cercanos ya venían por debajo de los controles antes del mes 0, el mes de la terminación del hijo, y no se probó por qué.
