"""Registro de cuencas de la replicacion: una cuenca es un parametro de la ingesta, el armado y la lectura.

Cada cuenca tiene su propio warehouse (`data/<id>/warehouse.duckdb`) con las tablas del contrato que consume
`pipeline.replicacion` (dim_pozo, fct_produccion, ultimo_mes, co_pozo_pad, co_hijo) y publica sus tablas `mart_replicacion_*` ahi.
El warehouse de Vaca Muerta no se toca. Este modulo no tiene reglas numericas: la regla de lectura y los filtros estan en
`pipeline/replicacion.py` y en `pipeline/colorado/__init__.py` (la primera cuenca), y la regla de la familia se fija aparte.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pipeline.ingest import DATA, ROOT


@dataclass(frozen=True)
class Cuenca:
    id: str                            # "colorado": carpeta de datos, almacen de claims y del libro de hallazgos
    nombre: str                        # como se nombra en una frase: "Colorado"
    titulo: str                        # titulo de la pagina de replicacion
    pagina: Path                       # pagina de la replicacion
    pagina_datos: str                  # nombre del archivo de la pagina de datos y conteos (misma carpeta)
    modulo: str                        # ruta del paquete de la ingesta y el armado, para el texto de la pagina
    ordinal: str                       # "una segunda cuenca": como se nombra frente a Vaca Muerta
    regla_fijada: str                  # "en que commit se fijo la regla", para el texto de la pagina
    nota_regla: str = ""               # frase opcional sobre cambios posteriores a la regla (vacia si no hubo)
    no_puede: tuple[str, ...] = field(default_factory=tuple)   # vinetas de "Que <cuenca> no puede mostrar"
    de_el: str = ""                    # "del Colorado": para "el warehouse del Colorado"
    filtros: str = "de P5a"            # "con los filtros <filtros>" en el texto de la regla
    fecha_hijo: str = "fractura"        # lo que marca el mes 0 del hijo en el texto de la pagina (Wyoming solo tiene la primera terminacion)
    rotulo_hijos: str = ""             # rotulo de la fila de hijos de los recuentos ("" = el de la tabla comun)

    @property
    def db(self) -> Path:
        return DATA / self.id / "warehouse.duckdb"

    @property
    def tabla_veredicto(self) -> str:
        return f"mart_replicacion_{self.id}"

    @property
    def hipotesis(self) -> str:
        return f"replicacion_{self.id}"


COLORADO = Cuenca(
    id="colorado",
    nombre="Colorado",
    titulo="Replicación en Colorado (cuenca DJ)",
    pagina=ROOT / "wiki" / "hallazgos" / "replicacion.md",
    pagina_datos="colorado_datos.md",
    modulo="pipeline/colorado",
    ordinal="una segunda cuenca",
    regla_fijada="en el primer commit de este tramo",
    de_el="del Colorado",
    filtros="de P5a",
    nota_regla=(" Después del primer commit se agregó `limit 1` a la consulta SQL del libro (`replicacion_colorado` en "
                "`pipeline/hallazgos.py`) solo para que la consulta de la hipótesis devuelva una única fila: el texto, el operador y el "
                "umbral son los mismos y el valor no cambió, pero cambió la `firma` registrada en el libro. Los umbrales no se tocaron "
                "después de ver resultados."),
    no_puede=(
        "No hay etapas ni arena: el largo de rama es un proxy (profundidad medida menos vertical) y no se corre ningún resultado que "
        "dependa de ellas.",
        "La rama lateral es un proxy y la ubicación es la de superficie, igual que en Vaca Muerta; no hay trayectorias.",
        "La fecha de fractura sale del formulario de divulgación de FracFocus (inicio del trabajo), no de un mes calendario de reporte; "
        "un error de unos días mueve el mes 0 de un hijo.",
        "La convención de reporte difiere: una fila por formación, sidetracks sumados al pozo y días efectivos como el máximo entre filas.",
        "Los cierres aparecen como meses con cero días producidos, no como una marca de parada; no se separa un cierre del operador de "
        "un daño.",
        "La población de padres es distinta (muchos pozos verticales); por eso el corte principal usa solo padres horizontales.",
        "El bloque de 5 km de un pad usa el centroide de todos sus pozos con ubicación (también verticales y sin producción), no solo "
        "el de los pozos filtrados; solo importa para pads cerca del borde de una celda.",
        "Es una huella medida contra un control, sin ajuste por comparaciones múltiples; no se afirma causalidad.",
    ),
)

WYOMING = Cuenca(
    id="wyoming",
    nombre="Wyoming",
    titulo="Replicación en Wyoming (WOGCC)",
    pagina=ROOT / "wiki" / "hallazgos" / "replicacion_wyoming.md",
    pagina_datos="wyoming_datos.md",
    modulo="pipeline/wyoming",
    ordinal="una tercera cuenca",
    regla_fijada="en el commit d4a7355, antes de bajar la producción de Wyoming",
    de_el="de Wyoming",
    filtros="de `pipeline/wyoming/__init__.py` (los de Colorado)",
    fecha_hijo="terminación",
    nota_regla=(" Después de ver el primer resultado, a raíz de la revisión, se corrigió la lectura de FIRSTCOMP (no la regla de lectura ni los "
                "filtros): un valor de siete dígitos que se lee como fecha válida de dos maneras (AAAAMDD y AAAAMMD) es ambiguo y el pozo "
                "queda fuera de los hijos. Antes de la corrección: 1.177 hijos, 356 eventos cercanos y 2.291 controles, brecha del mes 1 "
                "de -2,5 puntos (IC por bloques de 5 km: -5,3 a 3,0), brecha previa de -12,1 y valor 0,096; tampoco se replicaba."),
    rotulo_hijos="Hijos (regla fijada de Wyoming)",
    no_puede=(
        "No hay fecha de fractura: el mes 0 de cada hijo es el mes de FIRSTCOMP, la fecha de primera terminación del regulador. Un "
        "error de semanas o meses entre la terminación y la fractura mueve el mes 0, y un refrac no se distingue de un hijo nuevo "
        "porque hay una sola fecha por pozo. Si la terminación cae después de la fractura, el mes 0 queda corrido hacia adelante y "
        "la base de los meses -3 a -1 incluye meses posteriores a ella: la lectura no separa \"no hay huella\" de \"el mes 0 está "
        "corrido\", y los conteos de la página de datos muestran cuánto se parece el mes de FIRSTCOMP al del primer petróleo.",
        "No hay etapas ni arena: el largo de rama es un proxy (profundidad medida menos vertical) y no se corre ningún resultado que "
        "dependa de ellas. TD se toma como profundidad vertical sin que se haya podido confirmar.",
        "La columna de dirección del encabezado no se usa: no distingue un pozo horizontal (marca 'H' en la mitad de los pozos). Un "
        "pozo es horizontal por TD y MD, sin trayectorias.",
        "La convención de reporte difiere: una fila por pozo y año con doce columnas por mes, que se abre en pozo-mes; los días son el "
        "máximo entre filas y un código de días fuera de 0 a 31 (casi siempre 99) se toma como desconocido.",
        "Los pozos con producción que no están en los encabezados no tienen coordenadas ni FIRSTCOMP y no entran como hijos, padres ni "
        "controles; no se midió cuánto cambiaría una cifra si entraran.",
        "La unidad (barriles de petróleo) es la convención del regulador y no está escrita en el archivo.",
        "Es una huella medida contra un control, sin ajuste por comparaciones múltiples; no se afirma causalidad.",
    ),
)

CUENCAS: dict[str, Cuenca] = {c.id: c for c in (COLORADO, WYOMING)}


def cuenca(id_: str) -> Cuenca:
    try:
        return CUENCAS[id_]
    except KeyError:
        raise SystemExit(f"cuenca desconocida: {id_} (hay: {', '.join(CUENCAS)})") from None
