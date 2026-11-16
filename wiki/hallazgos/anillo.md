# Anillo de control: mes 1 y mes 6 con cuatro controles distintos

Página generada por `pipeline/anillo.py`. Pregunta si la brecha del mes 1 y su cierre a los 6 meses dependen de usar como control a los padres cuyo hijo más cercano está a 2 a 5 km.
Los cercanos son siempre los mismos (menos de 1 km); lo único que cambia entre variantes es el control.
Cada variante informa la brecha en k = 1 y k = 6 con IC 95% por pads hijo.

## Veredicto

**robusto a la eleccion del control**: en las cuatro variantes la brecha del mes 1 es menor que -0,10 con IC 95% que excluye cero y el valor absoluto de la brecha del mes 6 es menor que 0,05: ni la brecha del mes 1 ni su cierre a los 6 meses dependen del control usado.

Control de consistencia: V0 reproduce el libro: libro k=1 -0,2293 contra V0 -0,2293 (dif 0,0000), libro k=6 -0,0210 contra V0 -0,0210 (dif 0,0000); tolerancia 0,005.

## Brechas por variante

| Variante | Control | k | n cercano | n control | Brecha | IC 95% |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| V0 | 2 a 5 km | 1 | 2.077 | 18.262 | -0,229 | -0,275 a -0,178 |
| V0 | 2 a 5 km | 6 | 1.948 | 17.026 | -0,021 | -0,055 a 0,012 |
| V1 | 5 a 10 km, limpio a 1 km | 1 | 2.077 | 26.753 | -0,245 | -0,284 a -0,191 |
| V1 | 5 a 10 km, limpio a 1 km | 6 | 1.948 | 24.545 | -0,040 | -0,075 a -0,008 |
| V2 | 2 a 10 km, limpio a 1 km | 1 | 2.077 | 41.434 | -0,240 | -0,284 a -0,187 |
| V2 | 2 a 10 km, limpio a 1 km | 6 | 1.948 | 38.173 | -0,035 | -0,074 a -0,002 |
| V3 | 2 a 5 km, limpio a 2 km | 1 | 2.077 | 9.469 | -0,239 | -0,291 a -0,191 |
| V3 | 2 a 5 km, limpio a 2 km | 6 | 1.948 | 8.730 | -0,047 | -0,085 a -0,010 |

## Qué no prueba

- No dice que el cierre sea recuperación de la producción: con datos mensuales un cierre preventivo y un daño se ven igual.
- Los controles más lejanos comparan zonas distintas (geología, operador); una brecha distinta puede ser un gradiente entre zonas y no un cambio en la huella.
- El IC es por pads hijo, sin ajuste por comparaciones múltiples (hay cuatro variantes y dos meses).
