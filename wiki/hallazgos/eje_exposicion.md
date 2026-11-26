# Eje de exposición

Página generada por `pipeline/eje_exposicion.py`. Compara el eje de mayor merma con el eje que implica la geometría de desarrollo (hacia dónde están los padres respecto del hijo) y reestima el eje de merma dándole a cada dirección el mismo peso.

## Resumen

- Veredicto: **geometria explica el eje**. Dispara la regla de parada.
- Condición (i): el eje de merma de Loma Campana (101 grados) cae dentro del IC de su eje de exposición (88 a 117): sí; el de la cuenca (93) dentro del suyo (90 a 101): sí. Se cumple.
- Condición (ii): la cuenca reponderada queda en 91 grados, IC 49 a 128 (ancho 79), p 0,200: sin definir. Se cumple.
- Loma Campana reponderada: 99 grados, IC 73 a 126, p 0,040 (definido).

## Eje de merma contra ejes de exposición

Por área: el eje de merma con su IC (mart_anisotropia_area), el eje de exposición (media axial de los rumbos) con su IC y concentración Rbar, y el eje de filas (primer eje principal de las posiciones de los pads hijo) con su IC y razón entre autovalores. Dist es la distancia axial en grados.

| Área | Eventos | Pads | Eje merma | IC merma | Eje exposición | IC exposición | Rbar | Eje filas | IC filas | Razón autovalores | Dist merma-exp | Merma en IC exp | Dist merma-filas | Merma en IC filas |
| --- | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | --- | ---: | ---: | --- | ---: | --- |
| Cuenca | 1.751 | 325 | 93 | 70 a 123 | 95 | 90 a 101 | 0,365 | 105 | 101 a 109 | 4,6 | 1,9 | sí | 11,4 | no |
| LOMA CAMPANA | 694 | 148 | 101 | 78 a 131 | 100 | 88 a 117 | 0,209 | 103 | 100 a 105 | 21,5 | 1,6 | sí | 1,3 | sí |
| LA AMARGA CHICA | 275 | 49 | 77 | 3 a 150 | 86 | 76 a 98 | 0,430 | 164 | 155 a 173 | 4,4 | 9,0 | sí | 86,1 | no |
| FORTIN DE PIEDRA | 143 | 27 | 62 | 50 a 88 | 82 | 73 a 89 | 0,644 | 43 | 38 a 47 | 18,9 | 20,1 | no | 19,2 | no |
| BAJADA DEL PALO OESTE | 132 | 13 | 22 | 130 a 105 | 86 | 80 a 95 | 0,804 | 70 | 65 a 108 | 11,2 | 64,1 | no | 47,8 | no |
| BANDURRIA SUR | 126 | 21 | 21 | 148 a 95 | 108 | 100 a 118 | 0,758 | 119 | 114 a 154 | 8,2 | 86,9 | no | 82,3 | no |
| LINDERO ATRAVESADO | 87 | 10 | 67 | 175 a 135 | 143 | 124 a 167 | 0,410 | 3 | 93 a 91 | 4,6 | 76,1 | no | 64,3 | sí |
| LA CALERA | 64 | 15 | 155 | 78 a 61 | 88 | 77 a 97 | 0,663 | 88 | 72 a 98 | 7,2 | 67,2 | no | 67,1 | no |

## Reponderación por dirección

Eje de merma reestimado con mínimos cuadrados ponderados (cada dirección pesa igual dentro de cada área), con dummies de área. El contraste es dos veces la amplitud, en puntos de índice.

| Área | Eventos | Eje (grados) | IC 95% (grados) | Ancho IC | Contraste (puntos) | p permutación | Definido |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| Cuenca | 1.751 | 91 | 49 a 128 | 79 | 11,6 | 0,200 | no |
| LOMA CAMPANA | 694 | 99 | 73 a 126 | 53 | 18,4 | 0,040 | sí |

## Pieza 3: modelo de ramas (no hecha)

La pieza 3 (modelo de ramas) no se hizo. Necesita azimut de rama y coordenadas de fondo, que no están en el warehouse; no se verificó si el padrón de pozos de la Secretaría de Energía o el organismo provincial los publican. Por eso un veredicto negativo no descarta la geometría de ramas.

## Regla fijada antes de correr

La muestra es la del eje principal (eventos de 0,3 a menos de 1 km, todos, tengan o no caída), para la cuenca y las áreas con al menos 60 eventos. El eje de exposición es la media axial de los rumbos con IC por bootstrap de pads (400 repeticiones); el eje de filas es el primer eje principal de las posiciones proyectadas de los pads hijo (cuenca centrada por área), también con IC por pads. La reponderación pesa cada evento por la inversa de los eventos de su área en su bin de rumbo (12 bins de 15 grados) y reestima con mínimos cuadrados ponderados y dummies de área, con IC por pads y p por permutación de pads completos (400 y 499 repeticiones) para la cuenca y Loma Campana. Un eje está definido si su p es menor que 0,10 y su IC mide menos de 90 grados. Dispara la regla si la merma de Loma Campana y de la cuenca caen en sus IC de exposición, o si la reponderación deja indefinido el eje de la cuenca.

## Qué no prueba

- El eje de exposición con pads de superficie es un proxy: no es la dirección de las ramas.
- Un eje de merma fuera del IC de exposición no lo separa del SHmax ni demuestra un mecanismo.
