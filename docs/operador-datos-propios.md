# Modo con datos propios

Un operador de Vaca Muerta puede correr el mismo estudio de eventos y el mismo modelo de dosis del dato público sobre sus propios pozos, sin que el dato salga de su máquina. No hay un estimador nuevo: `pipeline/local.py` arma en memoria las mismas tablas que usa el pipeline y llama al mismo código (`pipeline/sql/04_interferencia.sql`, `pipeline.placebo`, `pipeline.dosis`). La regla está fijada en el docstring del módulo y se commiteó antes de correrlo sobre cualquier dato.

## Comando

```
uv run python -m pipeline.local --wells pozos.csv --monthly mensual.csv --out salida/ [--reps N] [--daily diario.csv] [--shutins cierres.csv]
```

`--reps` cambia las repeticiones del bootstrap (por defecto las del estudio público). La salida es `resumen.json` (todas las cifras), `resumen.md` (el informe en español), `eventos.csv` (un renglón por evento cercano) y la tarjeta, `tarjeta.json` y `tarjeta.md`. Nada se escribe fuera de `--out`. `--daily` y `--shutins` son opcionales y se pueden usar por separado: el modo los lee después de armar la base, los agrega y suma sus conteos a `resumen.json` (claves `diario` y `cierres`), a `resumen.md` y a los avisos, y escribe en `--out` las tablas por pozo y mes: `diario_mes.csv` y, si hay producción mensual, `diario_contra_mensual.csv` (con `--daily`), y `cierres_mes.csv` (con `--shutins`). Esos CSV llevan los ids de pozo, como `eventos.csv`. Sus rutas pasan por el mismo rechazo de rutas dentro del repositorio. Sin ellos la salida es la de siempre.

## Esquema de los CSV

`pozos.csv`, una fila por pozo:

| columna | obligatoria | contenido |
| --- | --- | --- |
| `pozo_id` | sí | identificador del pozo |
| `pad_id` | sí | identificador del pad (el conglomerado del bootstrap es el pad del hijo) |
| `lon`, `lat` | sí | coordenadas en grados |
| `fecha_fractura` | columna sí, valor puede faltar | inicio de la primera fractura (AAAA-MM-DD) |
| `arena_tn`, `etapas`, `rama_m`, `presion_max_psi` | columna sí, valor puede faltar | dosis y geometría de la fractura |
| `operador`, `area` | no | si faltan valen `propio` y `unica` |

`mensual.csv`, una fila por pozo y mes: `pozo_id`, `mes` (AAAA-MM o AAAA-MM-DD), `petroleo_m3`; opcionales `dias_produccion` (se valida contra los días del mes; sin `agua_m3` no se usa en la cuenta) y `agua_m3` (agua del mes, mayor o igual a cero). La tarjeta (`tarjeta.json` y `tarjeta.md`) lleva solo cifras agrupadas (sin pozo, pad, coordenada ni fecha; una cifra de menos de 10 pozos se suprime). Sin `agua_m3` dice "sin dato de agua". Con `agua_m3` el modo local corre además el diseño del corte de agua (D2 de `pipeline/causal.py`) sobre tus tablas y la tarjeta lo resume; sin `dias_produccion`, o con esa columna vacía, la tarjeta dice "sin prueba de cierre". La tarjeta no es una replicación independiente si tu operador ya está en el dato público. Un archivo con errores de formato se rechaza con un mensaje que dice qué falla.

`diario.csv` (opcional, `--daily`), una fila por pozo y día:

| columna | obligatoria | contenido |
| --- | --- | --- |
| `pozo_id` | sí | el mismo identificador de `pozos.csv` |
| `fecha` | sí | AAAA-MM-DD; el par (`pozo_id`, `fecha`) no se repite |
| `petroleo_m3` | sí | petróleo del día; vacío o negativo pasa a 0 |
| `agua_m3` | no | agua del día; negativa o no interpretable queda sin dato |
| `horas_produccion` | no | horas en producción ese día, de 0 a 24 |

`cierres.csv` (opcional, `--shutins`), una fila por intervalo de cierre:

| columna | obligatoria | contenido |
| --- | --- | --- |
| `pozo_id` | sí | el mismo identificador de `pozos.csv` |
| `inicio` | sí | AAAA-MM-DD HH:MM o AAAA-MM-DD |
| `fin` | columna sí, valor puede faltar | igual que `inicio`; vacío es un cierre abierto, que se cierra al final del último mes del mensual |
| `motivo` | no | texto libre; se guarda como categoría y no se interpreta |

Las filas de pozos que no están en `pozos.csv` se ignoran y se cuentan en los avisos. Un archivo con errores (columna obligatoria ausente, duplicados, horas fuera de rango, `fin` anterior a `inicio`) se rechaza con código 2 y un mensaje que nombra columnas y conteos, nunca valores de las celdas.

## Qué calcula

- La brecha del mes 1 y del mes 6: mediana del índice de los padres a menos de 1 km de un hijo recién fracturado menos la de los controles a 2 a 5 km, con IC 95% de percentiles por pads hijo.
- Las cuatro variables de dosis del estudio (arena por etapa, arena por metro de rama, presión máxima, depleción del padre), solo las que tienen al menos 30 eventos con valor y desvío mayor que cero, con IC, p y p de Holm. El informe no escribe un veredicto de dosis y respuesta ni "efecto descartado".
- Con `--daily`: por pozo y mes, los días registrados, los días con producción, el petróleo y el agua del mes, y cuántos meses del diario difieren del mensual en más del 2%. Con `--shutins`: por pozo y mes, las horas cerradas (los intervalos que se superponen se fusionan y se cortan en el límite del mes) y los días cerrados completos. Las tablas quedan en `diario_mes.csv`, `diario_contra_mensual.csv` y `cierres_mes.csv`. Solo se leen y se agregan: la brecha, el modelo de dosis y la tarjeta no cambian.
- Avisos de muestra chica: menos de 30 cercanos o 10 pads para la brecha; con menos de 100 eventos o 20 pads hijo el modelo de dosis no se corre.

## Garantía de privacidad

El módulo se niega a correr (código de salida 2, con el motivo) si cualquier ruta de entrada o de salida está dentro del repositorio y versionada, o no está ignorada por git. Fuera del repositorio no hay restricción. Los datos se cargan en una base en memoria que no se guarda y no hay llamadas de red.

## Validación con el dato público

Se exportaron las tablas públicas del warehouse (3.448 pozos con su pad, la primera fractura de cada pozo y `fct_produccion`) a CSV fuera del repo y se corrió el modo con 2.000 repeticiones (con los datos de septiembre de 2026; no se repitió con los de octubre):

| cifra | estudio público | modo local sobre el mismo dato |
| --- | --- | --- |
| brecha del mes 1 | -22,9 puntos | -22,9 puntos (IC -26,8 a -18,5) |
| cercanos del mes 1 | 2.077 | 2.077 (380 pads) |
| brecha del mes 6 | -2,1 puntos | -2,1 puntos (IC -5,8 a 1,0) |

La estimación puntual y los n coinciden. El IC difiere de los publicados (-27,4 a -18,1 en el mes 1) porque son otras repeticiones y otra semilla de remuestreo. Las cuatro variables de dosis dan IC que incluyen cero (p de Holm 1,000 en las cuatro); no se comparan coeficiente a coeficiente con el estudio público porque el archivo local no trae la dummy de terminación.

## Qué no prueba

- Es el mismo estimador del dato público: no corrige por nada que el operador sepa y no esté en las columnas (espaciamiento real, geometría, presión de fondo). Con esas columnas, el modelo de dosis es el lugar donde agregarlas.
- Con pocos eventos el IC es ancho; un IC que incluye cero no dice que no haya efecto (ver `wiki/hallazgos/potencia_dosis.md`).
- Una brecha del mes 1 con datos mensuales no separa cierre preventivo de daño. El diario y los cierres se leen y se agregan, pero el modo local no los cruza con las fracturas ni parte la caída en días y caudal: eso es un análisis aparte, con su propia regla fijada antes.
- Con la columna opcional `agua_m3` lee el agua mensual y calcula con ella el diseño del corte de agua; con `--daily` y `--shutins` lee además el diario de producción y el registro de cierres y los agrega; no estima ningún efecto con ellos.
- Todos los pozos del archivo se toman como padres e hijos posibles; si el archivo es una parte del campo, la distancia al hijo más cercano ignora los pozos que faltan.

## Corrección de código posterior al registro de la regla

El docstring dice que `dim_fractura_pozo` tiene una fila por trabajo de fractura. En la implementación tiene una fila por pozo del archivo con su rama (`rama_m`), tenga o no fecha de fractura, porque un padre sin fecha de fractura igual aporta su rama a la depleción; sin esto la depleción quedaba fuera del modelo. No cambia ninguna regla de decisión ni ningún umbral; se encontró con datos sintéticos, antes de correr sobre dato real.
