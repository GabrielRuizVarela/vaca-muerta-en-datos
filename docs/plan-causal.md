# Plan causal: qué puede sostener como causa el dato público de Vaca Muerta

Fecha: 2026-11-21. Rama `t3/causal-diseno`. Este texto es también la cabecera de `pipeline/causal.py` y la base de la
página `wiki/hallazgos/causal.md`. El primer commit de la rama es la regla: cabecera, constantes y umbrales, sin ninguna
cifra calculada.

Lo que ya está publicado y no se rehace: la brecha del mes 1 (de -19 a -23 puntos, con pretendencia de -2,5, -3,6 y
-6,3 en los meses -3 a -1), las fechas falsas y la permutación, el gradiente por distancia, el alcance medido entre ramas
(hasta 1.000 m), el contraste costado menos punta (-28,0, "sostiene" como huella), los días perdidos (14,4 días más), la
lectura mixta de días y caudal (52 y 48%), el salto de corte de agua (0,187 más de proporción) y el cierre al mes 6. Todo
eso es descriptivo: compara padres cercanos con controles a 2 a 5 km de la misma edad, y los cercanos ya rendían menos
antes de la fractura. Lo que falta para leer una causa es un control que comparta la selección del tratado y una prueba
de cuánto puede deberse a esa selección.

## (a) Preguntas causales que el dato puede llegar a sostener

1. **Efecto de la primera fractura vecina sobre el caudal del padre.** ¿La primera fractura de un hijo a menos de 1 km
   baja el caudal de petróleo del padre al mes 1, frente a lo que habría producido sin esa fractura? Es la pregunta del
   estudio, ahora con un control que también está en zona de relleno.
2. **Comunicación física frente a cierre preventivo.** ¿La fractura del hijo mete fluido en el padre? Un cierre
   preventivo del operador baja los días producidos pero no puede subir el corte de agua del padre; una comunicación por
   la fractura sí. El corte de agua es el resultado que separa los dos canales, si se prueba que un cierre solo no lo sube.
3. **Daño persistente o solo diferido.** ¿Queda pérdida de caudal en los meses 7 a 24, o la brecha es diferido que se
   cierra? La recuperación final (EUR) no se observa; la persistencia del caudal es su sustituto medible, con cota.
4. **Geometría.** ¿La merma depende de estar al costado o en la punta de la rama del hijo? Ya hay una huella que
   "sostiene" (mecanismo.md), pero la posición no se asigna al azar y el placebo de 0 a 300 m no es plano. Aquí entra
   solo como heterogeneidad descriptiva del diseño 1 y 2, en la muestra de ramas (2016 a 2023).

## (b) Diseño de identificación que cada pregunta admite

| Diseño | Sirve para | Por qué sí o por qué no |
| --- | --- | --- |
| Diferencias en diferencias escalonadas (estilo Callaway y Sant'Anna 2021), con controles aún no tratados | 1, 2, 3 | La fecha de la primera fractura vecina varía entre padres; el control es un padre que también recibirá un hijo a menos de 1 km, pero más tarde, así que comparte la selección de zona de relleno. Se estima ATT(g, e) por cohorte de mes y grupo de edad y se agrega por eventos: evita los pesos negativos del modelo de dos efectos fijos. |
| Estudio de eventos con nunca tratados | 1, 2 | Solo como sensibilidad: un padre nunca alcanzado está en zona menos densa, que es justo la selección que se quiere quitar. |
| Control sintético o pareado por evento | 1 | El caudal mensual de un pozo es ruidoso y cae por declinación; con miles de eventos el promedio por celdas de cohorte y edad hace el mismo trabajo con menos grados de libertad. No se usa. |
| Discontinuidad en la distancia o en el solape | 1, 4 | No hay una regla que asigne el tratamiento de golpe a un umbral (ni regulatoria ni operativa conocida): la distancia es una dosis continua. No es aplicable; el gradiente por distancia ya está publicado como descripción. |
| Gradiente de geometría a igual distancia (costado contra punta) | 4 | Ya corrido como huella (mecanismo.md). La posición depende del diseño del pad del operador, no es exógena; se informa dentro del diseño 1 como heterogeneidad, sin veredicto propio. |
| Instrumento | ninguno | No hay uno creíble: la fecha de perforación o de equipo disponible del hijo afecta al padre por el mismo camino que la fractura (y por la perforación misma), así que no cumple la exclusión. Se dice que no existe. |
| Cotas de Lee (2009) para caudal por día producido | 2 (descriptivo) | El caudal por día producido solo se observa en meses producidos, y la fractura cambia qué meses se producen. Lee recorta para acotar el efecto en los padres que producirían en cualquier caso. Supone monotonía (la fractura solo baja la chance de producir el mes entero). Se publica sin veredicto. |

## (c) Supuestos de cada diseño y cuáles se pueden probar

| Supuesto | Diseño 1 y 3 (caudal) | Diseño 2 (agua) | ¿Se prueba con el dato? |
| --- | --- | --- | --- |
| Tendencias paralelas condicionales a cohorte de mes y edad (en proporción a la base propia) | sí | sí, en corte de agua | En parte: pretendencia en los meses -3 a -1 y cota de sensibilidad (sección d). No se puede probar después de la fractura. |
| Sin anticipación más allá de 3 meses | sí | sí | La base es la de los meses -6 a -4 (admite anticipación en -3 a -1); la pretendencia mide si la hay. |
| Sin derrame sobre los controles (SUTVA) | sí | sí | Se exige al control no tener ningún hijo a menos de 2 km en los 12 meses previos ni durante el horizonte. El derrame de 2 a 5 km publicado (anillo.md) queda fuera del control. Lo que no se ve: hijos sin fecha cargada. |
| Exogeneidad de la fecha de la fractura dentro de la cohorte | sí | sí | No directamente: la fecha la decide el operador. Placebo de fechas falsas y de nunca tratados. |
| Un cierre preventivo sin comunicación no sube el corte de agua | no aplica | sí, es la exclusión clave | Sí: placebo de cierre (meses con un cierre de más de la mitad del mes sin hijos a menos de 2 km). |
| Monotonía (Lee) | no aplica | descriptivo | No; se declara. |

## (d) Pruebas que romperían cada diseño

Regla común de rotura: un placebo rompe el diseño si su IC 95% excluye cero **y** su valor absoluto es de 5 puntos o más
(2 puntos porcentuales de corte de agua en el diseño 2).

- **Fechas falsas:** cada tratado con su fecha corrida 12 meses hacia atrás (cae entera antes de la fractura real), con
  la misma regla de limpieza y de controles.
- **Distancia falsa:** padres cuyo primer hijo cae a 3 a 5 km (y ninguno a menos de 2 km en la ventana) tratados como si
  fueran cercanos.
- **Nunca tratados:** padres que nunca tienen un hijo a menos de 1 km, con fechas sorteadas de la distribución de
  cohortes de los tratados (semilla fija).
- **Pretendencia con potencia:** ATT en los meses -3, -2 y -1 contra la base -6 a -4, y la pendiente previa mínima que se
  detectaría con 80% de potencia (Roth 2022), informada.
- **Sensibilidad a tendencias no paralelas (inspirada en Rambachan y Roth 2023, "magnitudes relativas", versión
  simplificada y conservadora, no su implementación exacta):** se supone que la brecha previa del mes -1 sigue entera
  después y que cada uno de los dos pasos siguientes (de -1 a 0 y de 0 a 1) puede desviarse hasta M veces el mayor paso
  previo observado. Sesgo máximo B(M) = |β(-1)| + 2·M·m, con m = max(|β(-3)|, |β(-2) - β(-3)|, |β(-1) - β(-2)|).
  Intervalo robusto = [IC bajo - B(M), IC alto + B(M)]. M* es el mayor M con el intervalo robusto entero bajo cero.
- **Dejar un operador afuera:** se repite el ATT(1) sin cada operador del padre con 50 tratados o más.
- **Placebo de cierre (diseño 2):** meses de padres no tratados con días producidos bajo la mitad del mes (y base de
  0,8 o más), sin hijos a menos de 2 km en los 12 meses previos ni en el siguiente, contra meses sin cierre del mismo
  mes calendario y grupo de edad. Si el cierre solo sube el corte de agua, el agua no separa los canales.
- **Resultado de control negativo:** no hay uno creíble en el dato público (el gas y el agua responden a la misma
  fractura). La distancia falsa cumple esa función: mismo mes, mismo operador, sin la fractura cerca.
- **Rosenbaum o E-valor:** no encajan (no hay pares emparejados ni razón de riesgos); se usa la cota de magnitudes
  relativas.

## (e) Qué datos faltan y qué tendría que conseguir el dueño

| Dato | Para qué | Dónde estaría |
| --- | --- | --- |
| Presión de boca o de fondo del padre durante la fractura del hijo | Es la prueba física directa de comunicación; con ella el diseño 2 deja de depender del agua | Operadoras (no es público) |
| Producción diaria y motivo de cada parada | Separa un cierre preventivo de un golpe dentro del mes; vuelve exacto el canal de días | Operadoras; la Secretaría solo publica el mes y el estado |
| Cronograma de etapas de la fractura del hijo (día y etapa) | Fija la fecha del tratamiento al día y la dosis por etapa | Carga de fractura detallada (hoy hay fecha de inicio y fin, etapas, arena, agua y presión máxima por pozo) |
| Trayectorias 2024 y 2025 | La muestra de ramas cubre 76 a 97% de 2016 a 2023 pero 39% de 2024 y 25% de 2025: la geometría es sobre todo de 2016 a 2023 | Secretaría (carga pendiente) |
| Trazadores químicos o análisis de agua producida | Confirma qué agua viene de la fractura del hijo | Operadoras |
| Producción hasta el abandono | EUR real en lugar del sustituto de 24 meses | Tiempo |

## (f) Diseños elegidos y la regla fijada antes de calcular

Orden: **D1** (caudal, diferencias en diferencias escalonadas con aún no tratados) es el principal; **D2** (corte de
agua, canal físico) es el segundo; **D1b** (persistencia, meses 7 a 24) es la extensión de D1 a la pregunta 3. La
geometría y las cotas de Lee se publican sin veredicto.

Por qué estos: D1 cambia el control por uno que comparte la selección de zona de relleno y le pone una cota numérica a
la tendencia previa, que es el punto que hoy impide leer causa. D2 ataca el límite "cierre preventivo y daño se ven igual"
con un resultado que el cierre no puede mover, y prueba esa exclusión. D1b responde si hay pérdida o solo diferido con
una cota del mayor daño compatible.

Qué se sabía al fijar la regla (regla informada en esto): las cifras publicadas listadas arriba, en particular la
pretendencia y el salto de agua. Ningún número de D1, D1b ni D2 se calculó antes de este commit.

### Definiciones comunes

- Universo: pozos de `int_pozo_ubicacion` (Vaca Muerta, shale, con ubicación). Hijos y meses de fractura de
  `int_frac_hijo`. Distancia de superficie con la fórmula de `int_par_padre_hijo` (111,32 km por grado).
- Golpe a d km de un pozo i en el mes m: un hijo fracturado en m a menos de d km de i, después del primer mes de petróleo
  de i (sin la restricción de 6 meses de edad, para ver también golpes de pozos jóvenes).
- Cohorte g_i: primer mes con golpe a 1 km. Tratado: edad en g de 6 meses o más, ningún golpe a 2 km en los 12 meses
  previos a g, base con los tres meses -6 a -4 presentes y media de más de 1 m3/d de petróleo por día calendario.
- Índice I_i(e) = petróleo por día calendario en g + e sobre la base; recortado arriba en 3; mes sin fila: falta.
- Control de (g, grupo de edad, horizonte H): padre j del mismo grupo de edad en g (6 a 11, 12 a 23, 24 a 47, 48 o
  más meses), con la misma base válida, sin golpe a 2 km en [g - 12, g + H], y con su propio primer golpe a 1 km después
  de g + H dentro de los datos (aún no tratado y alguna vez tratado). Sensibilidad S1: suma los nunca tratados.
- ATT(g, a, e) = media del índice de tratados menos media de controles de la celda (al menos 1 tratado y 5 controles
  con dato). ATT(e) promedia las celdas pesadas por tratados. En puntos (x 100).
- IC 95%: bootstrap de percentiles por bloques de 5 km de la ubicación del padre (`pipeline.bloques.clave_bloque`), 400
  repeticiones, semilla fija, las mismas para todas las cantidades.

### D1. Primera fractura a menos de 1 km y caudal del padre

- Estimando: ATT(1), H = 6. Serie e = -3 a 6.
- Veredicto, en este orden:
  - **sin muestra**: menos de 300 tratados con dato en e = 1 en celdas con control, o menos de 30 bloques.
  - **no sobrevive a su placebo**: rompe la fecha falsa, la distancia falsa o los nunca tratados.
  - **sostiene como causal bajo tendencias paralelas condicionales**: el IC de ATT(1) queda entero bajo -10 puntos, M*
    es 1 o más, y sin cada operador grande el IC sigue bajo cero.
  - **no firme**: cualquier otro caso, con el motivo.

### D1b. Persistencia: meses 7 a 24

- Estimando: diferencia de la media del índice de los meses 7 a 24 (al menos 15 de 18 meses con dato), H = 24, con
  tratados y controles sin otro golpe a 2 km en los meses 1 a 24.
- Veredicto: **sin muestra** con menos de 200 tratados; **pérdida persistente** si el IC alto queda bajo -|β(-1)| (más
  allá de la brecha previa); **solo diferido (cota)** si el IC incluye cero y el bajo es mayor que -5 puntos (el IC bajo
  es la mayor pérdida compatible); **no firme** en cualquier otro caso.

### D2. Comunicación física: corte de agua

- Resultado: ΔW = max(W(g), W(g + 1)) - media de W en g - 6 a g - 4 (al menos 2 meses), W = agua / (agua + petróleo), en
  puntos porcentuales. Mismas celdas y controles que D1.
- Veredicto, en este orden:
  - **sin muestra**: menos de 300 tratados con ΔW.
  - **no sobrevive a su placebo**: rompe el previo (ΔW en los meses -2 y -1), la fecha falsa o la distancia falsa (con el
    umbral de 2 puntos).
  - **no separa el cierre de la comunicación**: el placebo de cierre tiene IC que excluye cero y vale la mitad del ATT o
    más.
  - **sostiene: comunicación física causal bajo tendencias paralelas**: el IC de ATT_W queda entero sobre +2 puntos.
  - **no firme**: cualquier otro caso.

### Sin veredicto, publicado

- Heterogeneidad por posición (costado, punta) en la muestra con ramas, para D1 y D2.
- Cotas de Lee del caudal por día producido en e = 1 (producido: días efectivos de 0,9 del mes o más).
- S1 (con nunca tratados), medianas en lugar de medias, e = 0.

## Qué no va a poder decir ningún resultado

Aun con "sostiene", es causa bajo supuestos nombrados, no un hecho físico medido: sin presión ni producción diaria la
causa queda condicionada a tendencias paralelas y a la exclusión del placebo de cierre. Un "no firme" o un "no sobrevive"
también es un resultado: dice que el dato público no carga la causa y la tabla (e) dice qué la cargaría.
