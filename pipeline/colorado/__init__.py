"""Colorado (cuenca DJ): ingesta y tablas base para replicar el estudio de eventos de la interferencia en otra cuenca.

Pivote P5 de la fase 4, tramo P5a. Este tramo baja los datos, arma las tablas base y concilia los conteos. NO corre el
estudio de interferencia ni calcula brecha ni rendimiento alguno: eso es P5b, con las reglas de abajo.

    uv run python -m pipeline.colorado.ingest    # baja a data/colorado/raw (git-ignorado) con manifiesto de sha256
    uv run python -m pipeline.colorado.build     # data/colorado/warehouse.duckdb y wiki/hallazgos/colorado_datos.md

REGLA FIJADA ANTES DE CORRER (2026-11-15, antes de calcular ninguna cifra de Colorado; no se cambia despues de ver
resultados; se publican todos los resultados, favorables o no). Fuentes: ECMC (produccion 2018 a 2024 y archivo de pozos) y
FracFocus (lista de divulgaciones). Memoria de factibilidad del pivote P5.

Identidad del pozo y sidetracks:
  * pozo_id = entero de condado (3 digitos) + secuencia (5 digitos) del API, por ejemplo 123 y 24638 dan 12324638.
  * Un sidetrack (los 2 digitos siguientes del API) sale de la misma ubicacion de superficie: sus filas de produccion se SUMAN al
    pozo. Los dias efectivos del mes son el maximo entre todas las filas (formaciones y sidetracks) del pozo en ese mes.
  * La clave del API de FracFocus (14 digitos, estado 05) se parte en estado(2) + condado(3) + secuencia(5) + sidetrack(2) +
    terminacion(2); el pozo es condado + secuencia, igual que en ECMC.

Unidades: petroleo y agua de barriles a m3 (x 0,158987); gas de Mcf a miles de m3 (x 0,0283168); agua de la divulgacion de
FracFocus de galones a m3 (x 0,00378541). Una fila de produccion por formacion y mes: se suman al pozo y mes.

Pozo horizontal (una sola vez, sin la capa de lineas direccionales, que no hay lector de shapefile entre las dependencias):
  * horizontal si Max_TVD > 1.000 ft y Max_MD - Max_TVD > 1.500 ft (archivo de pozos de ECMC). Falta cualquiera de los dos: no es
    horizontal. Largo de rama por proxy = (Max_MD - Max_TVD) x 0,3048 m; no hay etapas ni arena verdadera.

Hijo (el pozo que se fractura):
  * Primera divulgacion de FracFocus del pozo (la fecha de inicio de trabajo mas antigua entre todas sus divulgaciones, sea cual
    sea el ano), con el inicio del trabajo en un mes entre 2018-07 y 2024-06 (inclusive), el pozo en el archivo de pozos con
    coordenadas, y horizontal. Un refrac de un pozo con divulgacion anterior no es un hijo nuevo.
  * Fecha dudosa: si la fecha de la divulgacion cae mas de 30 dias despues del primer petroleo del pozo (inicio del primer mes
    con petroleo mayor que cero), el pozo se marca "fecha dudosa", se excluye de los hijos y se cuenta en la pagina.
  * El primer petroleo esta censurado en enero de 2018 (la produccion empieza ahi).

Padre (identico al estudio de Vaca Muerta, pipeline/sql/04_interferencia.sql):
  * Pozo con ubicacion, distinto del hijo, a menos de 5 km (distancia de 111,32 km por grado, la misma formula), con primer
    petroleo al menos 6 meses antes del mes de fractura, y caudal medio de petroleo por dia calendario en los meses -3 a -1
    mayor que 1 m3/d. El corte principal usa SOLO padres horizontales; el corte con todos los padres se publica al lado.
  * Evento = (padre, mes de fractura); el hijo mas cercano fija la banda: cercano a menos de 1 km, control de 2 a 5 km,
    intermedio de 1 a 2 km (no entra en la brecha). Mismos filtros para controles.

Lectura de la replicacion (fijada ahora; P5b la aplica sin cambiarla): hipotesis `replicacion_colorado`.
  * "Se sostiene" si la brecha del mes 1 (mediana del indice de los padres cercanos menos la de los controles, base de los meses
    -3 a -1) es negativa con un IC 95% que excluye cero (limite superior menor que 0) Y la brecha previa a la fractura con base
    limpia (mes -1, base de los meses -6 a -4) es menor, en valor absoluto, que la brecha del mes 1. Si no, "no se replica".
    Se publican las dos lecturas. Mismo estimador y mismo IC (bootstrap por pads hijo, percentiles 2,5 y 97,5) que placebo.py.
  * Valor de la hipotesis = max(limite superior del IC, |brecha previa limpia| - |brecha del mes 1|); se sostiene si es < 0.
  * P5b publica la tabla `mart_replicacion_colorado` (una fila con k = 1) con las columnas `brecha`, `ic_alto` y
    `brecha_previa_limpia`.

Que NO es: Colorado y Vaca Muerta difieren en convencion de reporte (una fila por formacion), fechas (formulario de
divulgacion frente a mes calendario de reporte) y poblacion (muchos padres verticales). Ninguna cifra de este tramo es
una brecha, ni un rendimiento, ni una afirmacion causal.
"""

# Reglas numericas (las usa pipeline.colorado.build; cambiarlas despues de ver resultados rompe la preregistracion).
HORIZONTAL_TVD_MIN_FT = 1000.0
HORIZONTAL_LATERAL_MIN_FT = 1500.0
VENTANA_FRAC = ("2018-07-01", "2024-06-30")
FECHA_DUDOSA_DIAS = 30
EDAD_MIN_MESES = 6
KM_CERCANO = 1.0
KM_CONTROL = (2.0, 5.0)
KM_MAX = 5.0
BASE_MIN_M3_D = 1.0
PAD_KM = 0.05
KM_POR_GRADO = 111.32
FT_A_M = 0.3048
BBL_A_M3 = 0.158987
MCF_A_MILES_M3 = 0.0283168
GAL_A_M3 = 0.00378541
ANIOS_PRODUCCION = tuple(range(2018, 2025))
ESTIMACION_SCOUT = {"hijos": 4817, "eventos_cercanos": 3866, "controles": 58139}
