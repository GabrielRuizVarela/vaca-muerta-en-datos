# Anillo de control: mes 1 y mes 6 con cuatro controles distintos

Página generada por `pipeline/anillo.py`. Pregunta si la brecha del mes 1 y su cierre a los 6 meses dependen de usar como control a los padres cuyo hijo más cercano está a 2 a 5 km.
Los cercanos son siempre los mismos (menos de 1 km); lo único que cambia entre variantes es el control.
Cada variante informa la brecha en k = 1 y k = 6 con IC 95% por pads hijo.
Prueba agregada después de ver los resultados anteriores: la regla se fijó antes de correr, pero la pregunta nació de ellos.

## Veredicto

**robusto a la eleccion del control**: en las cuatro variantes la brecha del mes 1 es menor que -0,10 con IC 95% que excluye cero y el valor absoluto de la brecha del mes 6 es menor que 0,05: ni la brecha del mes 1 ni su cierre a los 6 meses dependen del control usado.

Control de consistencia: V0 reproduce el libro: libro k=1 -0,2305 contra V0 -0,2305 (dif 0,0000), libro k=6 -0,0214 contra V0 -0,0214 (dif 0,0000); tolerancia 0,005.

## Brechas por variante

| Variante | Control | k | n cercano | n control | Brecha | IC 95% |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| V0 | 2 a 5 km | 1 | 2.094 | 18.291 | -0,230 | -0,275 a -0,183 |
| V0 | 2 a 5 km | 6 | 1.996 | 17.455 | -0,021 | -0,061 a 0,007 |
| V1 | 5 a 10 km, limpio a 1 km | 1 | 2.094 | 26.756 | -0,246 | -0,286 a -0,197 |
| V1 | 5 a 10 km, limpio a 1 km | 6 | 1.996 | 25.250 | -0,041 | -0,078 a -0,009 |
| V2 | 2 a 10 km, limpio a 1 km | 1 | 2.094 | 41.454 | -0,241 | -0,282 a -0,198 |
| V2 | 2 a 10 km, limpio a 1 km | 6 | 1.996 | 39.278 | -0,035 | -0,076 a -0,008 |
| V3 | 2 a 5 km, limpio a 2 km | 1 | 2.094 | 9.482 | -0,240 | -0,283 a -0,187 |
| V3 | 2 a 5 km, limpio a 2 km | 6 | 1.996 | 9.028 | -0,048 | -0,092 a -0,017 |

## Qué no prueba

- No dice que el cierre sea recuperación de la producción: con datos mensuales un cierre preventivo y un daño se ven igual.
- Los controles más lejanos comparan zonas distintas (geología, operador); una brecha distinta puede ser un gradiente entre zonas y no un cambio en la huella.
- El IC es por pads hijo, sin ajuste por comparaciones múltiples (hay cuatro variantes y dos meses).
