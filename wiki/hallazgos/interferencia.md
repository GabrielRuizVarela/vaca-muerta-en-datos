# Interferencia entre fracturas en Vaca Muerta

Huella medida de la interferencia: cuánto petróleo dejan de producir los pozos padre cuando se fractura un pozo hijo cercano, frente a pozos control de la misma edad.

## Brecha por grupo de edad

Índice de tasa mensual del pozo padre alrededor del mes de fractura del hijo (mes 0), menos el índice de los pozos control. Valores negativos indican producción por debajo del control.

| Grupo de edad | k | Eventos cercanos | Índice cercano | Índice control | Brecha |
|---|---|---|---|---|---|
| 06-11 | 0 | 474 | 0,748 | 0,809 | -0,061 |
| 06-11 | 1 | 474 | 0,591 | 0,738 | -0,147 |
| 06-11 | 2 | 474 | 0,587 | 0,676 | -0,089 |
| 06-11 | 4 | 468 | 0,611 | 0,596 | 0,015 |
| 06-11 | 6 | 454 | 0,538 | 0,534 | 0,004 |
| 12-23 | 0 | 663 | 0,803 | 0,919 | -0,115 |
| 12-23 | 1 | 666 | 0,660 | 0,872 | -0,212 |
| 12-23 | 2 | 666 | 0,712 | 0,840 | -0,128 |
| 12-23 | 4 | 654 | 0,715 | 0,765 | -0,050 |
| 12-23 | 6 | 627 | 0,699 | 0,708 | -0,010 |
| 24-47 | 0 | 588 | 0,707 | 0,949 | -0,242 |
| 24-47 | 1 | 588 | 0,704 | 0,919 | -0,216 |
| 24-47 | 2 | 588 | 0,794 | 0,902 | -0,109 |
| 24-47 | 4 | 578 | 0,787 | 0,846 | -0,059 |
| 24-47 | 6 | 567 | 0,829 | 0,795 | 0,034 |
| 48+ | 0 | 365 | 0,698 | 0,960 | -0,262 |
| 48+ | 1 | 366 | 0,689 | 0,937 | -0,248 |
| 48+ | 2 | 366 | 0,844 | 0,931 | -0,087 |
| 48+ | 4 | 355 | 0,840 | 0,909 | -0,069 |
| 48+ | 6 | 348 | 0,788 | 0,849 | -0,062 |

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
| 2026 | 260 | -0,444 |

Las fracturas se cargan con rezago, así que a los últimos años les faltan pozos hijos y la tabla no se lee como tendencia. La comparación con la misma antigüedad de carga en todos los años está en [carga_anual.md](carga_anual.md).

## Petróleo diferido

Petróleo diferido total (meses 0 a 6 desde la fractura, eventos cercanos): 11.445.600 bbl.

| Operador | Eventos cercanos | Petróleo diferido (bbl) |
|---|---|---|
| [YPF](../operador/ypf.md) | 1.338 | 7.986.339 |
| [Pluspetrol](../operador/pluspetrol.md) | 126 | 1.215.603 |
| [Pan American Energy](../operador/pan-american-energy.md) | 121 | 675.835 |
| [Shell](../operador/shell.md) | 71 | 512.287 |
| [Chevron](../operador/chevron.md) | 59 | 506.792 |

## Límites

Coordenadas de superficie (pads), no trayectoria de la rama. Un cierre o ahogo preventivo del operador se ve igual que un daño en datos mensuales. Es una huella medida, no una causa.

## Historial

- datos a 2026-09 (sha produccion 61cecc31c8dd): brecha mes 1 (todas las edades, mediana de eventos cercanos menos control) = -0,229; petróleo diferido total = 10.723.754 bbl
- datos a 2026-10 (sha produccion b10e75214719): brecha mes 1 (todas las edades, mediana de eventos cercanos menos control) = -0,230; petróleo diferido total = 11.445.600 bbl

## Fuentes

Tablas consultadas: `mart_interferencia_brecha`, `mart_interferencia_anual`, `mart_interferencia_diferida`, `int_interferencia_mes`.

- produccion_no_convencional: sha256 `b10e75214719`, cargado 2026-11-20T16:50:17+00:00.
- fractura_adjunto_iv: sha256 `ff95734bf485`, cargado 2026-11-20T16:50:39+00:00.
