# Potencia del nulo de dosis y respuesta

Página generada por `pipeline/potencia_dosis.py`. Pregunta inversa de pipeline.dosis y pipeline.dosis_pad: cuánto efecto de la dosis podría haber pasado inadvertido con este tamaño de muestra, y qué dato interno haría falta para ver efectos más chicos. Todo en desvíos de la caída por desvío de la dosis.

## Veredicto

Resultado A: **no alcanza para 0,2**: el mayor MDE80 de Holm del modelo conjunto es de 0,31 desvíos de la caída por desvío de la dosis: un efecto de 0,2 desvíos de la caída por desvío de la dosis puede pasar inadvertido con este dato, y el nulo de pipeline.dosis no descarta efectos de ese tamaño ni menores.
Resultado B: **no alcanza para 0,2**: el mayor MDE80 de Holm del modelo conjunto es de 0,25 desvíos de la caída por desvío de la dosis: un efecto de 0,2 desvíos de la caída por desvío de la dosis puede pasar inadvertido con este dato, y el nulo de pipeline.dosis no descarta efectos de ese tamaño ni menores.

## Efecto mínimo detectable

MDE80: efecto mínimo con 80% de potencia, a dos colas con alfa 0,05, desde el IC 95% publicado. La versión con Holm es la conservadora (paso más exigente sobre 4 o 5 pruebas).

### Resultado A, modelo conjunto (n = 1.551, pads = 263)

| Variable | Coef (desvíos) | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |
| --- | ---: | ---: | ---: | ---: |
| arena por etapa | 0,012 | 0,068 | 0,190 | 0,226 |
| arena por metro de rama | -0,041 | 0,069 | 0,193 | 0,231 |
| presión máxima de tratamiento | 0,042 | 0,066 | 0,186 | 0,221 |
| depleción del padre | 0,054 | 0,094 | 0,262 | 0,313 |

### Resultado A, pad, muestra completa (n = 1.559, pads = 265)

| Variable | Coef (desvíos) | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |
| --- | ---: | ---: | ---: | ---: |
| arena total del pad | 0,094 | 0,094 | 0,262 | 0,312 |
| arena por metro de rama del pad | -0,132 | 0,086 | 0,241 | 0,288 |
| presión máxima del pad | 0,063 | 0,060 | 0,167 | 0,199 |
| depleción del padre | 0,077 | 0,090 | 0,253 | 0,301 |

### Resultado A, pad, cercania (n = 662, pads = 151)

| Variable | Coef (desvíos) | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |
| --- | ---: | ---: | ---: | ---: |
| arena total del pad | -0,049 | 0,113 | 0,317 | 0,387 |
| arena por metro de rama del pad | 0,009 | 0,127 | 0,356 | 0,435 |
| presión máxima del pad | 0,043 | 0,123 | 0,344 | 0,419 |
| depleción del padre | 0,095 | 0,165 | 0,463 | 0,565 |
| interacción depleción por cercanía | -0,051 | 0,079 | 0,221 | 0,270 |

### Resultado B, modelo conjunto (n = 1.402, pads = 248)

| Variable | Coef (desvíos) | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |
| --- | ---: | ---: | ---: | ---: |
| arena por etapa | 0,016 | 0,065 | 0,182 | 0,217 |
| arena por metro de rama | -0,022 | 0,059 | 0,166 | 0,198 |
| presión máxima de tratamiento | 0,039 | 0,071 | 0,200 | 0,238 |
| depleción del padre | 0,072 | 0,075 | 0,211 | 0,252 |

### Resultado B, pad, muestra completa (n = 1.407, pads = 249)

| Variable | Coef (desvíos) | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |
| --- | ---: | ---: | ---: | ---: |
| arena total del pad | 0,052 | 0,093 | 0,261 | 0,312 |
| arena por metro de rama del pad | -0,044 | 0,088 | 0,245 | 0,292 |
| presión máxima del pad | -0,025 | 0,060 | 0,167 | 0,199 |
| depleción del padre | 0,073 | 0,077 | 0,215 | 0,256 |

### Resultado B, pad, cercania (n = 587, pads = 140)

| Variable | Coef (desvíos) | SE (desvíos) | MDE80 sin ajustar | MDE80 Holm |
| --- | ---: | ---: | ---: | ---: |
| arena total del pad | -0,027 | 0,122 | 0,341 | 0,416 |
| arena por metro de rama del pad | 0,045 | 0,104 | 0,291 | 0,355 |
| presión máxima del pad | -0,034 | 0,102 | 0,285 | 0,347 |
| depleción del padre | 0,124 | 0,164 | 0,459 | 0,560 |
| interacción depleción por cercanía | 0,064 | 0,083 | 0,232 | 0,283 |

## Pads y eventos para ver 0,1 y 0,2 desvíos

Pads y eventos necesarios para que el MDE80 llegue a cada objetivo, con el MDE sin ajustar y con el de Holm. Si el número necesario es menor que el actual (factor menor que 1), la muestra actual ya alcanza para ese objetivo. La cuenta supone eventos por pad constantes: el error baja como 1 sobre la raíz del número de pads.

### Resultado A, modelo conjunto (actual: n = 1.551, pads = 263)

| Variable | Pads 0,1 | Eventos 0,1 | Pads 0,1 Holm | Eventos 0,1 Holm | Pads 0,2 | Eventos 0,2 | Pads 0,2 Holm | Eventos 0,2 Holm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arena por etapa | 949 | 5.597 | 1.348 | 7.952 | 237 | 1.399 | 337 | 1.988 |
| arena por metro de rama | 984 | 5.805 | 1.398 | 8.247 | 246 | 1.451 | 350 | 2.062 |
| presión máxima de tratamiento | 908 | 5.355 | 1.290 | 7.609 | 227 | 1.339 | 323 | 1.902 |
| depleción del padre | 1.811 | 10.679 | 2.573 | 15.171 | 453 | 2.670 | 643 | 3.793 |

### Resultado A, pad, muestra completa (actual: n = 1.559, pads = 265)

| Variable | Pads 0,1 | Eventos 0,1 | Pads 0,1 Holm | Eventos 0,1 Holm | Pads 0,2 | Eventos 0,2 | Pads 0,2 Holm | Eventos 0,2 Holm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arena total del pad | 1.819 | 10.702 | 2.585 | 15.205 | 455 | 2.676 | 646 | 3.801 |
| arena por metro de rama del pad | 1.545 | 9.089 | 2.195 | 12.912 | 386 | 2.272 | 549 | 3.228 |
| presión máxima del pad | 739 | 4.346 | 1.050 | 6.175 | 185 | 1.087 | 262 | 1.544 |
| depleción del padre | 1.690 | 9.940 | 2.400 | 14.122 | 422 | 2.485 | 600 | 3.530 |

### Resultado A, pad, cercania (actual: n = 662, pads = 151)

| Variable | Pads 0,1 | Eventos 0,1 | Pads 0,1 Holm | Eventos 0,1 Holm | Pads 0,2 | Eventos 0,2 | Pads 0,2 Holm | Eventos 0,2 Holm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arena total del pad | 1.520 | 6.664 | 2.262 | 9.916 | 380 | 1.666 | 565 | 2.479 |
| arena por metro de rama del pad | 1.918 | 8.410 | 2.854 | 12.514 | 480 | 2.103 | 714 | 3.129 |
| presión máxima del pad | 1.785 | 7.827 | 2.656 | 11.646 | 446 | 1.957 | 664 | 2.911 |
| depleción del padre | 3.239 | 14.199 | 4.819 | 21.128 | 810 | 3.550 | 1.205 | 5.282 |
| interacción depleción por cercanía | 740 | 3.243 | 1.101 | 4.826 | 185 | 811 | 275 | 1.206 |

### Resultado B, modelo conjunto (actual: n = 1.402, pads = 248)

| Variable | Pads 0,1 | Eventos 0,1 | Pads 0,1 Holm | Eventos 0,1 Holm | Pads 0,2 | Eventos 0,2 | Pads 0,2 Holm | Eventos 0,2 Holm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arena por etapa | 822 | 4.648 | 1.168 | 6.603 | 206 | 1.162 | 292 | 1.651 |
| arena por metro de rama | 687 | 3.881 | 975 | 5.514 | 172 | 970 | 244 | 1.379 |
| presión máxima de tratamiento | 987 | 5.580 | 1.402 | 7.928 | 247 | 1.395 | 351 | 1.982 |
| depleción del padre | 1.108 | 6.265 | 1.575 | 8.901 | 277 | 1.566 | 394 | 2.225 |

### Resultado B, pad, muestra completa (actual: n = 1.407, pads = 249)

| Variable | Pads 0,1 | Eventos 0,1 | Pads 0,1 Holm | Eventos 0,1 Holm | Pads 0,2 | Eventos 0,2 | Pads 0,2 Holm | Eventos 0,2 Holm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arena total del pad | 1.701 | 9.613 | 2.417 | 13.658 | 425 | 2.403 | 604 | 3.415 |
| arena por metro de rama del pad | 1.499 | 8.471 | 2.130 | 12.035 | 375 | 2.118 | 532 | 3.009 |
| presión máxima del pad | 696 | 3.935 | 989 | 5.591 | 174 | 984 | 247 | 1.398 |
| depleción del padre | 1.150 | 6.497 | 1.634 | 9.231 | 287 | 1.624 | 408 | 2.308 |

### Resultado B, pad, cercania (actual: n = 587, pads = 140)

| Variable | Pads 0,1 | Eventos 0,1 | Pads 0,1 Holm | Eventos 0,1 Holm | Pads 0,2 | Eventos 0,2 | Pads 0,2 Holm | Eventos 0,2 Holm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| arena total del pad | 1.631 | 6.840 | 2.427 | 10.178 | 408 | 1.710 | 607 | 2.544 |
| arena por metro de rama del pad | 1.187 | 4.975 | 1.766 | 7.403 | 297 | 1.244 | 441 | 1.851 |
| presión máxima del pad | 1.134 | 4.753 | 1.687 | 7.073 | 283 | 1.188 | 422 | 1.768 |
| depleción del padre | 2.946 | 12.353 | 4.384 | 18.381 | 737 | 3.088 | 1.096 | 4.595 |
| interacción depleción por cercanía | 754 | 3.163 | 1.123 | 4.707 | 189 | 791 | 281 | 1.177 |

## Simulación de planta y recupera (modelo conjunto, resultado A)

Potencia empírica: fracción de corridas en que la variable plantada se ve, con error de Monte Carlo. El nivel 0 es el tamaño (sin efecto plantado).

| Variable | Nivel | Delta (desvíos) | Regla | Corridas | Se ve | Potencia | Error MC |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| arena por etapa | 0 | 0,000 | Holm | 200 | 0 | 0,000 | 0,000 |
| arena por etapa | 0 | 0,000 | sin ajustar | 200 | 0 | 0,000 | 0,000 |
| arena por metro de rama | 0 | 0,000 | Holm | 200 | 1 | 0,005 | 0,005 |
| arena por metro de rama | 0 | 0,000 | sin ajustar | 200 | 4 | 0,020 | 0,010 |
| presión máxima de tratamiento | 0 | 0,000 | Holm | 200 | 0 | 0,000 | 0,000 |
| presión máxima de tratamiento | 0 | 0,000 | sin ajustar | 200 | 7 | 0,035 | 0,013 |
| depleción del padre | 0 | 0,000 | Holm | 200 | 1 | 0,005 | 0,005 |
| depleción del padre | 0 | 0,000 | sin ajustar | 200 | 3 | 0,015 | 0,009 |
| arena por etapa | 0,1 | 0,100 | Holm | 200 | 2 | 0,010 | 0,007 |
| arena por etapa | 0,1 | 0,100 | sin ajustar | 200 | 20 | 0,100 | 0,021 |
| arena por metro de rama | 0,1 | 0,100 | Holm | 200 | 15 | 0,075 | 0,019 |
| arena por metro de rama | 0,1 | 0,100 | sin ajustar | 200 | 45 | 0,225 | 0,030 |
| presión máxima de tratamiento | 0,1 | 0,100 | Holm | 200 | 19 | 0,095 | 0,021 |
| presión máxima de tratamiento | 0,1 | 0,100 | sin ajustar | 200 | 79 | 0,395 | 0,035 |
| depleción del padre | 0,1 | 0,100 | Holm | 200 | 6 | 0,030 | 0,012 |
| depleción del padre | 0,1 | 0,100 | sin ajustar | 200 | 26 | 0,130 | 0,024 |
| arena por etapa | 0,2 | 0,200 | Holm | 200 | 35 | 0,175 | 0,027 |
| arena por etapa | 0,2 | 0,200 | sin ajustar | 200 | 104 | 0,520 | 0,035 |
| arena por metro de rama | 0,2 | 0,200 | Holm | 200 | 72 | 0,360 | 0,034 |
| arena por metro de rama | 0,2 | 0,200 | sin ajustar | 200 | 136 | 0,680 | 0,033 |
| presión máxima de tratamiento | 0,2 | 0,200 | Holm | 200 | 101 | 0,505 | 0,035 |
| presión máxima de tratamiento | 0,2 | 0,200 | sin ajustar | 200 | 167 | 0,835 | 0,026 |
| depleción del padre | 0,2 | 0,200 | Holm | 200 | 40 | 0,200 | 0,028 |
| depleción del padre | 0,2 | 0,200 | sin ajustar | 200 | 94 | 0,470 | 0,035 |
| arena por etapa | mde_sin_ajustar | 0,190 | Holm | 200 | 30 | 0,150 | 0,025 |
| arena por etapa | mde_sin_ajustar | 0,190 | sin ajustar | 200 | 96 | 0,480 | 0,035 |
| arena por metro de rama | mde_sin_ajustar | 0,193 | Holm | 200 | 71 | 0,355 | 0,034 |
| arena por metro de rama | mde_sin_ajustar | 0,193 | sin ajustar | 200 | 134 | 0,670 | 0,033 |
| presión máxima de tratamiento | mde_sin_ajustar | 0,186 | Holm | 200 | 92 | 0,460 | 0,035 |
| presión máxima de tratamiento | mde_sin_ajustar | 0,186 | sin ajustar | 200 | 161 | 0,805 | 0,028 |
| depleción del padre | mde_sin_ajustar | 0,262 | Holm | 200 | 73 | 0,365 | 0,034 |
| depleción del padre | mde_sin_ajustar | 0,262 | sin ajustar | 200 | 135 | 0,675 | 0,033 |
| arena por etapa | mde_holm | 0,226 | Holm | 200 | 54 | 0,270 | 0,031 |
| arena por etapa | mde_holm | 0,226 | sin ajustar | 200 | 122 | 0,610 | 0,034 |
| arena por metro de rama | mde_holm | 0,231 | Holm | 200 | 103 | 0,515 | 0,035 |
| arena por metro de rama | mde_holm | 0,231 | sin ajustar | 200 | 164 | 0,820 | 0,027 |
| presión máxima de tratamiento | mde_holm | 0,221 | Holm | 200 | 119 | 0,595 | 0,035 |
| presión máxima de tratamiento | mde_holm | 0,221 | sin ajustar | 200 | 176 | 0,880 | 0,023 |
| depleción del padre | mde_holm | 0,313 | Holm | 200 | 108 | 0,540 | 0,035 |
| depleción del padre | mde_holm | 0,313 | sin ajustar | 200 | 175 | 0,875 | 0,023 |

La simulación no valida la cuenta analítica: la potencia empírica en el MDE80 (con su regla) queda fuera de 0,70 a 0,90 en alguna variable, así que la cuenta analítica es optimista; el veredicto sigue siendo el analítico.
Agregado después de ver los resultados (no cambia el veredicto): parte de la diferencia puede venir de la resolución del bootstrap de la simulación. Con B = 300 el p mínimo posible es 2 sobre 301, y con Holm sobre cuatro pruebas una variable solo pasa si ningún sorteo cae del lado contrario, un umbral más exigente que el normal de la cuenta analítica; así que la simulación puede subestimar la potencia, y la cuenta analítica no es necesariamente tan optimista como parece.
Tamaño (nivel 0, sin efecto plantado): la fracción que se ve va de 0,000 a 0,035 con la regla sin ajustar y de 0,000 a 0,005 con Holm, entre las cuatro variables.

## Qué dato interno achicaría el error

El mayor MDE80 de Holm del modelo conjunto A es de 0,31 desvíos: si un dato interno explicara una parte R2 de la varianza que hoy queda sin explicar, el error bajaría como la raíz de (1 menos R2). Ilustración, no estimación: las R2 son entradas, no una predicción de cuánto explicaría un dato real.

| R2 que explicaría el dato interno | MDE80 de Holm (desvíos) |
| ---: | ---: |
| 0,10 | 0,30 |
| 0,25 | 0,27 |
| 0,50 | 0,22 |

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
