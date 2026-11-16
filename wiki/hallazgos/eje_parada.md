# Regla de parada del eje de merma

Página generada por `pipeline/eje_parada.py`. Junta las cuatro patas de la regla de parada del plan de investigación (sección 4), fijada antes de correr, y dice si el eje de mayor merma se sigue presentando como hallazgo. No calcula nada nuevo: lee [la potencia](potencia.md), [los controles](eje_controles.md) y [la exposición](eje_exposicion.md).

## Veredicto

**La regla de parada se cumple** (4 de 4 patas disparan, y alcanza con una). El proyecto deja de presentar un eje de interferencia. Texto de reemplazo, el único que se usa:

> La caída de los padres cercanos no es igual en todas las direcciones de superficie en la muestra completa (con intervalos por pads), pero con datos públicos esa dirección no se separa del SHmax publicado ni de la forma en que se disponen los pads; la geometría de las ramas no se pudo probar. No es un hallazgo sobre esfuerzos ni sobre la fractura.

El hallazgo `anisotropia` del libro se renombra `asimetria_de_superficie` y queda no firme. El eje se conserva como descripción de la muestra (el número sigue en [anisotropia.md](anisotropia.md)), no como medición de esfuerzos ni de mecanismo.

## Las cuatro patas

| Pata | Prueba | Estado |
| ---: | --- | --- |
| 1 | Potencia: más de 2 veces los eventos actuales | dispara |
| 2 | Ventana previa: eje definido a menos de 30 grados de 93 | dispara |
| 3 | Exposición: el eje de merma no se separa del eje de exposición, o la reponderación lo deja indefinido | dispara |
| 4 | Bloques de 5 km: el eje de la cuenca deja de estar definido | dispara |

### Pata 1: dispara

M80 = 2,17 veces los eventos actuales (el múltiplo que da 80% de potencia); veredicto de la regla: no separable. Con el doble de eventos la potencia es de 78%. Cuenta analítica: unos 3.763 eventos. Al ritmo actual, unos 6,5 años hasta M80.

### Pata 2: dispara

definido y cercano: eje 111 grados, IC 81 a 138 (ancho 57), p de permutación 0,066, a 17,7 grados de 93.

### Pata 3: dispara

(i) merma de LC y Cuenca en IC de exposicion: se cumple (LC merma 101.5 en IC exp (87.7 a 117.2): si; Cuenca merma 92.9 en IC exp (90.0 a 102.1): si). (ii) reponderacion deja indefinido el eje de Cuenca: no se cumple (Cuenca reponderada: eje 91.8 IC 57.1 a 124.8 ancho 67.6 p 0.088, definido). La pieza 3 (modelo de ramas) no se hizo: no hay azimut de rama ni coordenadas de fondo en el warehouse.

### Pata 4: dispara

deja de estar definido: eje 93 grados, IC 63 a 129 (ancho 66), p de permutación 0,538. Diagnóstico agregado después de ver los resultados: el p de la regla intercambia solo bloques del mismo tamaño y 1.004 eventos están en bloques de tamaño único (hay 74 bloques), que no se mueven; con una permutación que rota los rumbos de cada bloque el p es 0,067. La regla, tal como se fijó, dispara; el diagnóstico dice que esta pata es la menos sólida de las cuatro.

## Qué no cambia

- La brecha del mes 1, su cierre a los 6 meses, la sincronía, la descomposición entre días y caudal por día, la validación por inyección y la replicación en Colorado no dependen del eje y no se tocan.
- La regla de parada es sobre la dirección. No dice que la caída sea falsa ni que el eje sea cero: dice que con datos públicos no se puede afirmar que la dirección sea propia de la fractura.
- Lo que haría falta para reabrirla: azimut de rama y coordenadas de fondo (para el modelo de ramas), o unas 2 veces los eventos actuales con un desarrollo distinto del de Loma Campana.
