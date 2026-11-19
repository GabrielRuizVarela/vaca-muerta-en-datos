# Potencia del nulo de dosis y respuesta

Página generada por `pipeline/potencia_dosis.py`. Pregunta inversa de pipeline.dosis y pipeline.dosis_pad: cuánto efecto de la dosis podría haber pasado inadvertido con este tamaño de muestra, y qué dato interno haría falta para ver efectos más chicos. Todo en desvíos de la caída por desvío de la dosis.

## Veredicto

Resultado A: **no alcanza para 0,2**: el mayor MDE80 de Holm del modelo conjunto es de 0,32 desvíos de la caída por desvío de la dosis: un efecto de 0,2 desvíos de la caída por desvío de la dosis puede pasar inadvertido con este dato, y el nulo de pipeline.dosis no descarta efectos de ese tamaño ni menores.
Resultado B: **no alcanza para 0,2**: el mayor MDE80 de Holm del modelo conjunto es de 0,26 desvíos de la caída por desvío de la dosis: un efecto de 0,2 desvíos de la caída por desvío de la dosis puede pasar inadvertido con este dato, y el nulo de pipeline.dosis no descarta efectos de ese tamaño ni menores.

## Efecto mínimo detectable

MDE80: efecto mínimo con 80% de potencia, a dos colas con alfa 0,05, desde el IC 95% publicado. La versión con Holm es la conservadora (paso más exigente sobre 4 o 5 pruebas).

### Resultado A, modelo conjunto (n = 1.544, pads = 262)

| Variable | Coef (desvíos) | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |
| --- | ---: | ---: | ---: | ---: |
| arena por etapa | 0,014 | 0,068 | 0,189 | 0,226 |
| arena por metro de rama | -0,040 | 0,068 | 0,192 | 0,229 |
| presión máxima de tratamiento | 0,041 | 0,066 | 0,184 | 0,220 |
| depleción del padre | 0,049 | 0,097 | 0,271 | 0,323 |

### Resultado A, pad, muestra completa (n = 1.552, pads = 264)

| Variable | Coef (desvíos) | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |
| --- | ---: | ---: | ---: | ---: |
| arena total del pad | 0,093 | 0,095 | 0,265 | 0,316 |
| arena por metro de rama del pad | -0,127 | 0,090 | 0,252 | 0,300 |
| presión máxima del pad | 0,063 | 0,058 | 0,164 | 0,195 |
| depleción del padre | 0,073 | 0,093 | 0,260 | 0,309 |

### Resultado A, pad, cercania (n = 658, pads = 150)

| Variable | Coef (desvíos) | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |
| --- | ---: | ---: | ---: | ---: |
| arena total del pad | -0,052 | 0,114 | 0,318 | 0,388 |
| arena por metro de rama del pad | 0,022 | 0,123 | 0,345 | 0,420 |
| presión máxima del pad | 0,044 | 0,125 | 0,351 | 0,428 |
| depleción del padre | 0,118 | 0,167 | 0,469 | 0,572 |
| interacción depleción por cercanía | -0,059 | 0,076 | 0,213 | 0,260 |

### Resultado B, modelo conjunto (n = 1.395, pads = 247)

| Variable | Coef (desvíos) | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |
| --- | ---: | ---: | ---: | ---: |
| arena por etapa | 0,011 | 0,063 | 0,176 | 0,210 |
| arena por metro de rama | -0,025 | 0,062 | 0,174 | 0,207 |
| presión máxima de tratamiento | 0,040 | 0,074 | 0,208 | 0,248 |
| depleción del padre | 0,073 | 0,078 | 0,218 | 0,260 |

### Resultado B, pad, muestra completa (n = 1.400, pads = 248)

| Variable | Coef (desvíos) | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |
| --- | ---: | ---: | ---: | ---: |
| arena total del pad | 0,054 | 0,095 | 0,266 | 0,317 |
| arena por metro de rama del pad | -0,049 | 0,087 | 0,243 | 0,290 |
| presión máxima del pad | -0,025 | 0,059 | 0,165 | 0,197 |
| depleción del padre | 0,073 | 0,075 | 0,210 | 0,251 |

### Resultado B, pad, cercania (n = 583, pads = 139)

| Variable | Coef (desvíos) | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |
| --- | ---: | ---: | ---: | ---: |
| arena total del pad | -0,028 | 0,122 | 0,341 | 0,416 |
| arena por metro de rama del pad | 0,047 | 0,104 | 0,291 | 0,356 |
| presión máxima del pad | -0,033 | 0,102 | 0,286 | 0,349 |
| depleción del padre | 0,140 | 0,165 | 0,461 | 0,563 |
| interacción depleción por cercanía | 0,055 | 0,077 | 0,216 | 0,263 |

## Pads y eventos para ver 0,1 y 0,2 desvíos

Pads y eventos necesarios para que el MDE80 llegue a cada objetivo, con el MDE sin ajustar y con el de Holm. Si el número necesario es menor que el actual (factor menor que 1), la muestra actual ya alcanza para ese objetivo. La cuenta supone eventos por pad constantes: el error baja como 1 sobre la raíz del número de pads.

### Resultado A, modelo conjunto (actual: n = 1.544, pads = 262)

| Variable | Pads 0,1 | Eventos 0,1 | Pads 0,1 Holm | Eventos 0,1 Holm | Pads 0,2 | Eventos 0,2 | Pads 0,2 Holm | Eventos 0,2 Holm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arena por etapa | 939 | 5.531 | 1.333 | 7.858 | 235 | 1.383 | 333 | 1.965 |
| arena por metro de rama | 964 | 5.681 | 1.370 | 8.071 | 241 | 1.420 | 342 | 2.018 |
| presión máxima de tratamiento | 889 | 5.242 | 1.264 | 7.447 | 222 | 1.310 | 316 | 1.862 |
| depleción del padre | 1.918 | 11.306 | 2.726 | 16.062 | 480 | 2.826 | 681 | 4.016 |

### Resultado A, pad, muestra completa (actual: n = 1.552, pads = 264)

| Variable | Pads 0,1 | Eventos 0,1 | Pads 0,1 Holm | Eventos 0,1 Holm | Pads 0,2 | Eventos 0,2 | Pads 0,2 Holm | Eventos 0,2 Holm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arena total del pad | 1.852 | 10.886 | 2.631 | 15.466 | 463 | 2.722 | 658 | 3.867 |
| arena por metro de rama del pad | 1.674 | 9.840 | 2.378 | 13.981 | 418 | 2.460 | 595 | 3.495 |
| presión máxima del pad | 709 | 4.166 | 1.007 | 5.918 | 177 | 1.041 | 252 | 1.480 |
| depleción del padre | 1.780 | 10.464 | 2.529 | 14.866 | 445 | 2.616 | 632 | 3.717 |

### Resultado A, pad, cercania (actual: n = 658, pads = 150)

| Variable | Pads 0,1 | Eventos 0,1 | Pads 0,1 Holm | Eventos 0,1 Holm | Pads 0,2 | Eventos 0,2 | Pads 0,2 Holm | Eventos 0,2 Holm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arena total del pad | 1.521 | 6.671 | 2.263 | 9.927 | 380 | 1.668 | 566 | 2.482 |
| arena por metro de rama del pad | 1.782 | 7.819 | 2.652 | 11.634 | 446 | 1.955 | 663 | 2.908 |
| presión máxima del pad | 1.844 | 8.091 | 2.744 | 12.039 | 461 | 2.023 | 686 | 3.010 |
| depleción del padre | 3.300 | 14.477 | 4.911 | 21.541 | 825 | 3.619 | 1.228 | 5.385 |
| interacción depleción por cercanía | 683 | 2.997 | 1.017 | 4.460 | 171 | 749 | 254 | 1.115 |

### Resultado B, modelo conjunto (actual: n = 1.395, pads = 247)

| Variable | Pads 0,1 | Eventos 0,1 | Pads 0,1 Holm | Eventos 0,1 Holm | Pads 0,2 | Eventos 0,2 | Pads 0,2 Holm | Eventos 0,2 Holm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arena por etapa | 767 | 4.333 | 1.090 | 6.156 | 192 | 1.083 | 272 | 1.539 |
| arena por metro de rama | 744 | 4.202 | 1.057 | 5.970 | 186 | 1.050 | 264 | 1.492 |
| presión máxima de tratamiento | 1.070 | 6.041 | 1.520 | 8.583 | 267 | 1.510 | 380 | 2.146 |
| depleción del padre | 1.177 | 6.645 | 1.672 | 9.440 | 294 | 1.661 | 418 | 2.360 |

### Resultado B, pad, muestra completa (actual: n = 1.400, pads = 248)

| Variable | Pads 0,1 | Eventos 0,1 | Pads 0,1 Holm | Eventos 0,1 Holm | Pads 0,2 | Eventos 0,2 | Pads 0,2 Holm | Eventos 0,2 Holm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arena total del pad | 1.758 | 9.926 | 2.498 | 14.101 | 440 | 2.481 | 624 | 3.525 |
| arena por metro de rama del pad | 1.464 | 8.266 | 2.080 | 11.743 | 366 | 2.066 | 520 | 2.936 |
| presión máxima del pad | 678 | 3.827 | 963 | 5.438 | 170 | 957 | 241 | 1.359 |
| depleción del padre | 1.095 | 6.184 | 1.556 | 8.785 | 274 | 1.546 | 389 | 2.196 |

### Resultado B, pad, cercania (actual: n = 583, pads = 139)

| Variable | Pads 0,1 | Eventos 0,1 | Pads 0,1 Holm | Eventos 0,1 Holm | Pads 0,2 | Eventos 0,2 | Pads 0,2 Holm | Eventos 0,2 Holm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arena total del pad | 1.620 | 6.795 | 2.411 | 10.111 | 405 | 1.699 | 603 | 2.528 |
| arena por metro de rama del pad | 1.181 | 4.952 | 1.757 | 7.369 | 295 | 1.238 | 439 | 1.842 |
| presión máxima del pad | 1.139 | 4.777 | 1.695 | 7.109 | 285 | 1.194 | 424 | 1.777 |
| depleción del padre | 2.958 | 12.407 | 4.402 | 18.461 | 740 | 3.102 | 1.100 | 4.615 |
| interacción depleción por cercanía | 648 | 2.718 | 964 | 4.044 | 162 | 679 | 241 | 1.011 |

## Simulación de planta y recupera (modelo conjunto, resultado A)

Potencia empírica: fracción de corridas en que la variable plantada se ve, con error de Monte Carlo. El nivel 0 es el tamaño (sin efecto plantado).

| Variable | Nivel | Delta (desvíos) | Regla | Corridas | Se ve | Potencia | Error MC |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| arena por etapa | 0 | 0,000 | Holm | 200 | 0 | 0,000 | 0,000 |
| arena por etapa | 0 | 0,000 | sin ajustar | 200 | 0 | 0,000 | 0,000 |
| arena por metro de rama | 0 | 0,000 | Holm | 200 | 2 | 0,010 | 0,007 |
| arena por metro de rama | 0 | 0,000 | sin ajustar | 200 | 3 | 0,015 | 0,009 |
| presión máxima de tratamiento | 0 | 0,000 | Holm | 200 | 2 | 0,010 | 0,007 |
| presión máxima de tratamiento | 0 | 0,000 | sin ajustar | 200 | 9 | 0,045 | 0,015 |
| depleción del padre | 0 | 0,000 | Holm | 200 | 0 | 0,000 | 0,000 |
| depleción del padre | 0 | 0,000 | sin ajustar | 200 | 3 | 0,015 | 0,009 |
| arena por etapa | 0,1 | 0,100 | Holm | 200 | 1 | 0,005 | 0,005 |
| arena por etapa | 0,1 | 0,100 | sin ajustar | 200 | 24 | 0,120 | 0,023 |
| arena por metro de rama | 0,1 | 0,100 | Holm | 200 | 9 | 0,045 | 0,015 |
| arena por metro de rama | 0,1 | 0,100 | sin ajustar | 200 | 37 | 0,185 | 0,027 |
| presión máxima de tratamiento | 0,1 | 0,100 | Holm | 200 | 29 | 0,145 | 0,025 |
| presión máxima de tratamiento | 0,1 | 0,100 | sin ajustar | 200 | 82 | 0,410 | 0,035 |
| depleción del padre | 0,1 | 0,100 | Holm | 200 | 5 | 0,025 | 0,011 |
| depleción del padre | 0,1 | 0,100 | sin ajustar | 200 | 31 | 0,155 | 0,026 |
| arena por etapa | 0,2 | 0,200 | Holm | 200 | 39 | 0,195 | 0,028 |
| arena por etapa | 0,2 | 0,200 | sin ajustar | 200 | 105 | 0,525 | 0,035 |
| arena por metro de rama | 0,2 | 0,200 | Holm | 200 | 59 | 0,295 | 0,032 |
| arena por metro de rama | 0,2 | 0,200 | sin ajustar | 200 | 145 | 0,725 | 0,032 |
| presión máxima de tratamiento | 0,2 | 0,200 | Holm | 200 | 104 | 0,520 | 0,035 |
| presión máxima de tratamiento | 0,2 | 0,200 | sin ajustar | 200 | 177 | 0,885 | 0,023 |
| depleción del padre | 0,2 | 0,200 | Holm | 200 | 37 | 0,185 | 0,027 |
| depleción del padre | 0,2 | 0,200 | sin ajustar | 200 | 90 | 0,450 | 0,035 |
| arena por etapa | mde_sin_ajustar | 0,189 | Holm | 200 | 27 | 0,135 | 0,024 |
| arena por etapa | mde_sin_ajustar | 0,189 | sin ajustar | 200 | 100 | 0,500 | 0,035 |
| arena por metro de rama | mde_sin_ajustar | 0,192 | Holm | 200 | 50 | 0,250 | 0,031 |
| arena por metro de rama | mde_sin_ajustar | 0,192 | sin ajustar | 200 | 129 | 0,645 | 0,034 |
| presión máxima de tratamiento | mde_sin_ajustar | 0,184 | Holm | 200 | 94 | 0,470 | 0,035 |
| presión máxima de tratamiento | mde_sin_ajustar | 0,184 | sin ajustar | 200 | 163 | 0,815 | 0,027 |
| depleción del padre | mde_sin_ajustar | 0,271 | Holm | 200 | 82 | 0,410 | 0,035 |
| depleción del padre | mde_sin_ajustar | 0,271 | sin ajustar | 200 | 144 | 0,720 | 0,032 |
| arena por etapa | mde_holm | 0,226 | Holm | 200 | 47 | 0,235 | 0,030 |
| arena por etapa | mde_holm | 0,226 | sin ajustar | 200 | 129 | 0,645 | 0,034 |
| arena por metro de rama | mde_holm | 0,229 | Holm | 200 | 86 | 0,430 | 0,035 |
| arena por metro de rama | mde_holm | 0,229 | sin ajustar | 200 | 169 | 0,845 | 0,026 |
| presión máxima de tratamiento | mde_holm | 0,220 | Holm | 200 | 121 | 0,605 | 0,035 |
| presión máxima de tratamiento | mde_holm | 0,220 | sin ajustar | 200 | 182 | 0,910 | 0,020 |
| depleción del padre | mde_holm | 0,323 | Holm | 200 | 129 | 0,645 | 0,034 |
| depleción del padre | mde_holm | 0,323 | sin ajustar | 200 | 179 | 0,895 | 0,022 |

La simulación no valida la cuenta analítica: la potencia empírica en el MDE80 (con su regla) queda fuera de 0,70 a 0,90 en alguna variable, así que la cuenta analítica es optimista; el veredicto sigue siendo el analítico.
Agregado después de ver los resultados (no cambia el veredicto): parte de la diferencia puede venir de la resolución del bootstrap de la simulación. Con B = 300 el p mínimo posible es 2 sobre 301, y con Holm sobre cuatro pruebas una variable solo pasa si ningún sorteo cae del lado contrario, un umbral más exigente que el normal de la cuenta analítica; así que la simulación puede subestimar la potencia, y la cuenta analítica no es necesariamente tan optimista como parece.
Tamaño (nivel 0, sin efecto plantado): la fracción que se ve va de 0,000 a 0,045 con la regla sin ajustar y de 0,000 a 0,010 con Holm, entre las cuatro variables.

## Qué dato interno achicaría el error

El mayor MDE80 de Holm del modelo conjunto A es de 0,32 desvíos: si un dato interno explicara una parte R2 de la varianza que hoy queda sin explicar, el error bajaría como la raíz de (1 menos R2). Ilustración, no estimación: las R2 son entradas, no una predicción de cuánto explicaría un dato real.

| R2 que explicaría el dato interno | MDE80 de Holm (desvíos) |
| ---: | ---: |
| 0,10 | 0,31 |
| 0,25 | 0,28 |
| 0,50 | 0,23 |

Datos internos que podrían achicar el error:

- espaciamiento real entre ramas
- geometría de la fractura
- presión de monitoreo del pozo padre durante la fractura del hijo
- registros de cierre con fecha y hora
- tamaño de la ventana de cierre

## Regla fijada antes de correr

- Error estándar desde el IC 95% publicado: (alto menos bajo) sobre (2 por 1,96); todo en desvíos de la caída.
- MDE80 sin ajustar y versión conservadora con Holm sobre 4 pruebas (conjunto y pad completo) o 5 (cercanía).
- Pads y eventos necesarios con factor (MDE sobre objetivo) al cuadrado, a 0,1 y 0,2 desvíos, sin ajustar y con Holm.
- Simulación de planta y recupera solo en el modelo conjunto A: 200 corridas con deltas 0, 0,1, 0,2 y los dos MDE de cada variable.
- Veredicto con el mayor MDE80 de Holm del conjunto; el resultado B se informa aparte.

## Qué no prueba

- La potencia es sobre el efecto lineal de la dosis estandarizada con la forma del modelo; no dice nada de efectos no lineales, de umbrales ni de interacciones que no están en el modelo (salvo la interacción de pad_cercania).
- El SE sale de un IC de percentiles; la simulación valida solo el modelo conjunto A, no los de pad ni el resultado B.
- Supone que un dato nuevo se parece al actual (mismas áreas, mismo ruido, eventos por pad parecidos).
- No dice que el efecto exista: dice cuán grande tendría que ser para verse con este dato.
