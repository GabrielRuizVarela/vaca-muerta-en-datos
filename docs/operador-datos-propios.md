# Modo con datos propios

Un operador de Vaca Muerta puede correr el mismo estudio de eventos y el mismo modelo de dosis del dato público sobre sus propios pozos, sin que el dato salga de su máquina. No hay un estimador nuevo: `pipeline/local.py` arma en memoria las mismas tablas que usa el pipeline y llama al mismo código (`pipeline/sql/04_interferencia.sql`, `pipeline.placebo`, `pipeline.dosis`). La regla está fijada en el docstring del módulo y se commiteó antes de correrlo sobre cualquier dato.

## Comando

```
uv run python -m pipeline.local --wells pozos.csv --monthly mensual.csv --out salida/ [--reps N]
```

`--reps` cambia las repeticiones del bootstrap (por defecto las del estudio público). La salida es `resumen.json` (todas las cifras), `resumen.md` (el informe en español) y `eventos.csv` (un renglón por evento cercano). Nada se escribe fuera de `--out`.

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

`mensual.csv`, una fila por pozo y mes: `pozo_id`, `mes` (AAAA-MM o AAAA-MM-DD), `petroleo_m3`; opcional `dias_produccion` (se valida contra los días del mes y no se usa en la cuenta). Un archivo con errores de formato se rechaza con un mensaje que dice qué falla.

## Qué calcula

- La brecha del mes 1 y del mes 6: mediana del índice de los padres a menos de 1 km de un hijo recién fracturado menos la de los controles a 2 a 5 km, con IC 95% de percentiles por pads hijo.
- Las cuatro variables de dosis del estudio (arena por etapa, arena por metro de rama, presión máxima, depleción del padre), solo las que tienen al menos 30 eventos con valor y desvío mayor que cero, con IC, p y p de Holm. El informe no escribe un veredicto de dosis y respuesta ni "efecto descartado".
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
- Una brecha del mes 1 con datos mensuales no separa cierre preventivo de daño.
- Todos los pozos del archivo se toman como padres e hijos posibles; si el archivo es una parte del campo, la distancia al hijo más cercano ignora los pozos que faltan.

## Corrección de código posterior al registro de la regla

El docstring dice que `dim_fractura_pozo` tiene una fila por trabajo de fractura. En la implementación tiene una fila por pozo del archivo con su rama (`rama_m`), tenga o no fecha de fractura, porque un padre sin fecha de fractura igual aporta su rama a la depleción; sin esto la depleción quedaba fuera del modelo. No cambia ninguna regla de decisión ni ningún umbral; se encontró con datos sintéticos, antes de correr sobre dato real.
