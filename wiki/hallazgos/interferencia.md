# Interferencia entre fracturas en Vaca Muerta

Huella medida de la interferencia: cuánto petróleo dejan de producir los pozos padre cuando se fractura un pozo hijo cercano, frente a pozos control de la misma edad.

## Brecha por grupo de edad

Índice de tasa mensual del pozo padre alrededor del mes de fractura del hijo (mes 0), menos el índice de los pozos control. Valores negativos indican producción por debajo del control.

| Grupo de edad | k | Eventos cercanos | Índice cercano | Índice control | Brecha |
|---|---|---|---|---|---|
| 06-11 | 0 | 471 | 0,749 | 0,809 | -0,060 |
| 06-11 | 1 | 471 | 0,591 | 0,737 | -0,146 |
| 06-11 | 2 | 468 | 0,583 | 0,675 | -0,092 |
| 06-11 | 4 | 468 | 0,611 | 0,593 | 0,018 |
| 06-11 | 6 | 441 | 0,539 | 0,532 | 0,006 |
| 12-23 | 0 | 655 | 0,803 | 0,918 | -0,115 |
| 12-23 | 1 | 658 | 0,662 | 0,872 | -0,209 |
| 12-23 | 2 | 654 | 0,722 | 0,840 | -0,118 |
| 12-23 | 4 | 648 | 0,717 | 0,765 | -0,048 |
| 12-23 | 6 | 627 | 0,699 | 0,706 | -0,008 |
| 24-47 | 0 | 587 | 0,702 | 0,949 | -0,247 |
| 24-47 | 1 | 587 | 0,699 | 0,919 | -0,220 |
| 24-47 | 2 | 583 | 0,797 | 0,902 | -0,105 |
| 24-47 | 4 | 578 | 0,787 | 0,847 | -0,060 |
| 24-47 | 6 | 547 | 0,822 | 0,795 | 0,026 |
| 48+ | 0 | 360 | 0,697 | 0,960 | -0,263 |
| 48+ | 1 | 361 | 0,695 | 0,937 | -0,242 |
| 48+ | 2 | 359 | 0,846 | 0,932 | -0,086 |
| 48+ | 4 | 355 | 0,840 | 0,908 | -0,068 |
| 48+ | 6 | 333 | 0,783 | 0,841 | -0,059 |

## Huella por año

| Año | Eventos cercanos | Brecha mes 1 |
|---|---|---|
| 2016 | 70 | -0,249 |
| 2017 | 58 | -0,240 |
| 2018 | 55 | -0,176 |
| 2019 | 80 | -0,162 |
| 2020 | 41 | -0,043 |
| 2021 | 137 | -0,207 |
| 2022 | 232 | -0,345 |
| 2023 | 213 | -0,197 |
| 2024 | 279 | -0,226 |
| 2025 | 372 | -0,324 |
| 2026 | 243 | -0,445 |

## Petróleo diferido

Petróleo diferido total (meses 0 a 6 desde la fractura, eventos cercanos): 10.723.754 bbl.

| Operador | Eventos cercanos | Petróleo diferido (bbl) |
|---|---|---|
| [YPF](../operador/ypf.md) | 1.338 | 7.848.447 |
| [Pluspetrol](../operador/pluspetrol.md) | 112 | 816.548 |
| [Pan American Energy](../operador/pan-american-energy.md) | 121 | 668.444 |
| [Chevron](../operador/chevron.md) | 59 | 533.763 |
| [Shell](../operador/shell.md) | 71 | 515.866 |

## Límites

Coordenadas de superficie (pads), no trayectoria de la rama. Un cierre o ahogo preventivo del operador se ve igual que un daño en datos mensuales. Es una huella medida, no una causa.

## Historial

- datos a 2026-09 (sha produccion 61cecc31c8dd): brecha mes 1 (todas las edades, mediana de eventos cercanos menos control) = -0,229; petróleo diferido total = 10.723.754 bbl

## Fuentes

Tablas consultadas: `mart_interferencia_brecha`, `mart_interferencia_anual`, `mart_interferencia_diferida`, `int_interferencia_mes`.

- produccion_no_convencional: sha256 `61cecc31c8dd`, cargado 2026-11-15T03:50:45+00:00.
- fractura_adjunto_iv: sha256 `ff95734bf485`, cargado 2026-11-15T03:51:02+00:00.
