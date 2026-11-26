# Potencia del eje

## Resumen

El eje de mayor merma de la cuenca es 93,2 grados (IC 95% de 69,6 a 122,8), con 1.751 eventos en 325 pads hijo, y el SHmax publicado es 67,5 grados. Para separar un valor del otro con 80% de potencia harian falta 2,43 veces la muestra actual (escenario principal). Veredicto: no separable.

## Potencia por multiplo

Fraccion de corridas que separan, en %, promediada sobre los dos mundos (eje verdadero 67,5 o 93,0):

| Veces la muestra (M) | Escenario principal | Amplitud media |
| ---: | ---: | ---: |
| 1,0 | 51,7 | 28,2 |
| 1,5 | 65,3 | 29,5 |
| 2,0 | 72,8 | 32,0 |
| 2,5 | 81,2 | 36,2 |
| 3,0 | 89,2 | 43,8 |
| 4,0 | 93,8 | 50,2 |

## Cuenta analitica y calendario

La cuenta analitica de referencia pide 3.888 eventos (M = 2,22).
El ritmo actual es de 329 eventos por ano: media de 297 eventos en 2025 (12 meses) y 211 en 2026 (7 meses, llevado a ano completo: 362).
A ese ritmo, juntar M80 veces la muestra llevaria 7,6 anos.

## Regla fijada antes de correr

La regla se fijo el 2026-11-16, antes de calcular ninguna cifra de potencia, y no se cambia con los resultados:

* Se parte de los eventos del eje de la cuenca (distancia de 0,3 a menos de 1 km, efectos fijos de area, controles de km y log de la edad, caida acotada a [0, 2]).
* Se ajusta el modelo con el eje y se guardan la parte de controles y area, los residuos y la amplitud R.
* Se simulan dos mundos, con eje verdadero 67,5 o 93,0: controles mas R cos(2 (rumbo menos TH0)) mas residuo.
* Cada corrida sortea con reemplazo M veces los pads hijo; cada copia trae sus filas y residuos juntos y vale como un pad nuevo.
* En cada corrida se estima eje e IC 95% por pads (200 remuestreos, sin permutacion); separa si el IC excluye el otro valor.
* La potencia es el promedio sobre los dos mundos; grilla M en (1, 1,5, 2, 2,5, 3, 4), 200 corridas por punto.
* La sensibilidad con R/2 solo se informa; el veredicto usa el escenario principal.
* M80 interpola linealmente el primer cruce de 80%; si no cruza hasta M = 4, es mas de 4.
* Veredicto: M80 mayor a 2 (o mas de 4) declara la direccion no separable del SHmax; hasta 1,5 es pronto, en el medio lleva de 1,5 a 2 veces.
* Todas las semillas derivan de 20261115 por (multiplo, mundo, corrida); se publican todos los resultados.

## Que no prueba

* Supone que los eventos nuevos se parecen a los actuales (mismas areas, misma amplitud, mismo ruido); Loma Campana aporta 694 de los 1.734 eventos y el desarrollo futuro puede cambiar el reparto.
* No dice si el eje es real: dice si este tipo de dato podria separarlo del SHmax, aunque lo fuera.
* Solo mira el eje de la cuenca, no los de las areas.
