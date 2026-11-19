# Rezago de carga de las fracturas

Descriptivo, sin veredicto: este análisis mide cuánto tarda cada fractura en aparecer en el dato público de fracturas (Adjunto IV), contando desde el mes en que empezó hasta el mes en que el operador cargó el registro. No evalúa si el rezago es razonable ni lo atribuye a una causa, y no cambia ningún otro resultado del repositorio.

Edición del archivo de fracturas (U, último mes de carga): 2026-11. La carga empieza en 2019-06 (P0); las 970 fracturas de hijos que empezaron antes se cargaron de golpe después y quedan fuera de toda estadística de rezago. Hay 0 hijos con carga anterior al inicio: se cuentan aquí y quedan fuera de la curva.

## Curva de carga

Proporción de los hijos de cohortes maduras (inicio entre 2019-06 y 2024-11) ya cargados a L meses del inicio. Es una cota superior de la completitud real: las cargas posteriores a lo observado no se ven.

| L (meses) | Cargados hasta L |
| ---: | ---: |
| 0 | 0,1 % |
| 1 | 2,9 % |
| 2 | 13,6 % |
| 3 | 34,1 % |
| 6 | 69,6 % |
| 12 | 78,9 % |
| 18 | 86,4 % |
| 24 | 89,9 % |

## Por operador

Hijos de cohortes maduras con al menos 30 hijos por operador. El rezago está en meses.

| Operador | Hijos | Rezago mediano | Cargados en 3 meses | Cargados en 12 meses |
| --- | ---: | ---: | ---: | ---: |
| YPF | 699 | 4,0 | 39,9 % | 94,8 % |
| Vista | 139 | 3,0 | 74,1 % | 100,0 % |
| Pan American Energy | 127 | 23,0 | 21,3 % | 38,6 % |
| Shell | 119 | 9,0 | 0,8 % | 69,7 % |
| Tecpetrol | 104 | 20,0 | 3,8 % | 23,1 % |
| Pluspetrol | 88 | 4,0 | 42,0 % | 88,6 % |
| TotalEnergies | 42 | 4,0 | 31,0 % | 97,6 % |
| Pampa Energía | 36 | 5,5 | 33,3 % | 91,7 % |
| Phoenix Global Resources | 34 | 34,0 | 0,0 % | 0,0 % |

## Por año de inicio

Incluye todos los hijos con carga desde P0, también los de cohortes que todavía no maduraron, así que los años recientes subestiman el rezago. La completitud estimada es la del último mes del año (con tope en U).

| Año | Hijos con carga | Rezago mediano (meses) | Cargados en 3 meses | Completitud estimada |
| ---: | ---: | ---: | ---: | ---: |
| 2019 | 113 | 4,0 | 33,6 % | 89,9 % |
| 2020 | 87 | 6,0 | 19,5 % | 89,9 % |
| 2021 | 261 | 4,0 | 28,4 % | 89,9 % |
| 2022 | 296 | 4,0 | 28,4 % | 89,9 % |
| 2023 | 334 | 5,0 | 33,8 % | 89,9 % |
| 2024 | 355 | 4,0 | 48,2 % | 89,4 % |
| 2025 | 457 | 3,0 | 57,1 % | 77,9 % |
| 2026 | 246 | 3,0 | 64,6 % | 0,1 % |

## Meses de inicio con carga incompleta

Meses de inicio con completitud estimada menor que 0,80.

| Mes de inicio | Hijos cargados | Completitud estimada |
| --- | ---: | ---: |
| 2025-11 | 32 | 78,9 % |
| 2025-12 | 40 | 77,9 % |
| 2026-01 | 42 | 77,5 % |
| 2026-02 | 51 | 76,5 % |
| 2026-03 | 34 | 73,7 % |
| 2026-04 | 34 | 72,5 % |
| 2026-05 | 33 | 69,6 % |
| 2026-06 | 33 | 65,9 % |
| 2026-07 | 9 | 54,6 % |
| 2026-08 | 7 | 34,1 % |
| 2026-09 | 3 | 13,6 % |
| 2026-10 | 0 | 2,9 % |
| 2026-11 | 0 | 0,1 % |

## Límites

- F es una cota superior de la completitud real: lo que se carga después de U no está en el archivo.
- Una sola curva para todos los operadores, aunque el rezago difiere mucho por operador.
- El mes de carga es cuando se cargó el registro, no cuando se informó la producción.
