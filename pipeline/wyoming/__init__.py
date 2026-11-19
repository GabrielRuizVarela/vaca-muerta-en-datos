"""Wyoming: la segunda cuenca de la replicacion fuera de Vaca Muerta, con la regla fijada antes de bajar o medir nada.

Fuente: Wyoming Oil and Gas Conservation Commission (WOGCC), descargas del regulador: ZIP de encabezados de pozos (APINO, LON y
LAT de superficie, FIRSTCOMP, TD, MD) y ZIP de produccion mensual por pozo y anio. Entra por la regla de elegibilidad de
`pipeline/fuentes_mundo.py` y nada mas (auditoria del 2026-11-19, `wiki/hallazgos/fuentes_mundo.md`).

    uv run python -m pipeline.wyoming.ingest    # baja a data/wyoming/raw (git-ignorado) con manifiesto de sha256
    uv run python -m pipeline.wyoming.build     # data/wyoming/warehouse.duckdb y wiki/hallazgos/wyoming_datos.md

REGLA FIJADA ANTES DE CORRER (2026-11-19, antes de bajar la produccion de Wyoming y antes de calcular ninguna cifra de Wyoming; no
se cambia despues de ver resultados; se publican todos los resultados, favorables o no). Es la misma regla de
`pipeline/colorado/__init__.py` y de `pipeline/replicacion.py`: este archivo solo dice como se leen los campos de WOGCC dentro de
ella. Los filtros, la lectura y las semillas no se tocan: las constantes de abajo se importan de Colorado y un test las compara.

Identidad del pozo:
  * pozo_id = APINO como entero: condado (3 digitos) y secuencia (5 digitos), por ejemplo 705000 y 720921, igual que en Colorado. El
    APINO de WOGCC no trae digitos de sidetrack: no hay nada que sumar por ahi. Si el archivo de produccion trae varias filas de un
    mismo pozo y anio, se SUMAN al pozo; los dias efectivos del mes son el maximo entre sus filas.

Unidades: petroleo de barriles a m3 (x 0,158987), como en Colorado. La unidad de WOGCC es la convencion del regulador y no esta
escrita en el archivo; se toma como barriles y la pagina de datos lo dice.

Pozo horizontal (una sola vez): la columna de direccion del encabezado (HORIZ_DIR) NO se usa, porque marca 'H' en 71.376 de 143.555
pozos, incluidos pozos de 1951, y no distingue un pozo horizontal. Se usa el criterio de Colorado con las columnas del encabezado:
  * horizontal si TD > 1.000 ft y MD - TD > 1.500 ft. Falta cualquiera de los dos: no es horizontal. TD se toma como profundidad
    vertical total y MD como profundidad medida; la pagina de datos dice que TD no se pudo confirmar como vertical.

Hijo (el pozo que se completa):
  * Fecha del hijo = FIRSTCOMP, la fecha de primera terminacion del regulador. NO es la fecha de fractura: es la unica fecha por pozo
    que WOGCC publica, y el mes 0 de cada hijo es el mes de esa terminacion. Un refrac no se distingue de un hijo nuevo porque hay una
    sola fecha por pozo.
  * FIRSTCOMP viene como AAAAMMDD, o AAAAMDD (mes sin cero a la izquierda: 2024615 es el 2024-06-15). Una fecha que no se lee como
    una fecha valida deja al pozo afuera de los hijos y se cuenta en la pagina.
    Correccion de lectura del 2026-11-19, hecha despues de ver el primer resultado y a raiz de la revision, sin tocar la regla de
    lectura ni los filtros: un valor de siete digitos que se lee como fecha valida de las dos maneras (AAAAMDD y AAAAMMD, por ejemplo
    2024104: 4 de enero o 4 de octubre) es ambiguo y se trata como una fecha que no se lee. La pagina publica el resultado de antes
    y el de despues.
  * Ventana: primera terminacion en un mes entre 2018-07 y 2024-06 (inclusive), el pozo con LON y LAT, y horizontal. Toda
    Wyoming, sin elegir cuencas del estado ni formaciones.
  * Fecha dudosa: si la fecha de terminacion cae mas de 30 dias despues del primer petroleo del pozo (inicio del primer mes con petroleo
    mayor que cero), el pozo se marca "fecha dudosa", se excluye de los hijos y se cuenta en la pagina. Un pozo sin petroleo en el
    archivo no es hijo.

Padre, bandas y controles: identicos a Colorado y a Vaca Muerta (cercano a menos de 1 km, control de 2 a 5 km, intermedio de 1 a 2
km fuera de la brecha; primer petroleo al menos 6 meses antes del mes del hijo; mas de 1 m3/d en los meses -3 a -1; el corte
principal con SOLO padres horizontales y el corte con todos los padres al lado).

Lectura (hipotesis `replicacion_wyoming`, identica a `replicacion_colorado`): se replica si la brecha del mes 1 es negativa con un IC 95% por
bloques espaciales de 5 km (limite superior menor que 0) Y la brecha previa a la fractura con base limpia (mes -1, base de los meses -6
a -4) es menor, en valor absoluto, que la del mes 1. Valor = max(limite superior del IC, |brecha previa limpia| - |brecha del mes 1|);
se replica si es < 0. Mismo estimador, mismos filtros, mismas semillas que Colorado. Se publica la tabla
`mart_replicacion_wyoming` (una fila con k = 1). Si despues de la ingesta la cuenca no se puede medir (por ejemplo, menos de 30 hijos
o menos de 30 controles tras los filtros), queda en la lectura de la familia como "no se pudo medir" con el motivo escrito, y no se
cambia ninguna regla para salvarla.

Uso de la fuente (los terminos del menu de descargas de WOGCC dicen que no se permite raspar el sitio y no traen prohibicion de usar ni
publicar cifras derivadas de los archivos que ofrece; esta es nuestra lectura de los terminos, no una licencia):
  * la ingesta baja solo los archivos listados en el menu de descargas del regulador, por URL directa, una vez por archivo y guardado en
    raw; sin recorrer paginas, formularios de consulta ni consultas por pozo;
  * la pagina de la cuenca cita textuales las dos lineas de los terminos, nombra a WOGCC como la fuente y dice en una frase que es
    nuestra lectura y no una licencia;
  * nada de Wyoming se redistribuye crudo: raw queda afuera de git y solo se publican cifras derivadas.

Que NO es: WOGCC y Vaca Muerta difieren en convencion de reporte (una fila por pozo y anio con doce columnas por mes), en la fecha (primera
terminacion, no inicio de fractura), en el id de pozo y en la poblacion. Ninguna cifra de este tramo es una brecha, ni un rendimiento,
ni una afirmacion causal.
"""
from pipeline.colorado import (BASE_MIN_M3_D, BBL_A_M3, EDAD_MIN_MESES, FECHA_DUDOSA_DIAS, FT_A_M, HORIZONTAL_LATERAL_MIN_FT,
                               HORIZONTAL_TVD_MIN_FT, KM_CERCANO, KM_CONTROL, KM_MAX, KM_POR_GRADO, PAD_KM, VENTANA_FRAC)

__all__ = ["BASE_MIN_M3_D", "BBL_A_M3", "EDAD_MIN_MESES", "FECHA_DUDOSA_DIAS", "FT_A_M", "HORIZONTAL_LATERAL_MIN_FT",
           "HORIZONTAL_TVD_MIN_FT", "KM_CERCANO", "KM_CONTROL", "KM_MAX", "KM_POR_GRADO", "PAD_KM", "VENTANA_FRAC",
           "MIN_HIJOS_MEDIBLE", "MIN_CONTROLES_MEDIBLE"]

MIN_HIJOS_MEDIBLE = 30
MIN_CONTROLES_MEDIBLE = 30
