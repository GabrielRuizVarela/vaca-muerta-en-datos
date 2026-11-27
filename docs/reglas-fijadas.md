# Reglas fijadas y los commits que las citan

Este repositorio es una copia de un solo commit: el historial de trabajo no se publica. Las cifras y los textos citan, sin embargo, el commit en que se fijó cada regla. Este archivo conserva, para cada commit citado, su fecha en UTC, su asunto, los archivos que tocó y el texto que agregó, de modo que se pueda leer la regla tal como se escribió y comprobar el orden de las fechas sin el historial. El historial completo se comparte a pedido.

Cómo se armó: `git log` y `git show` de cada commit citado en el README, los docs, la wiki y el código del repositorio de trabajo (42 commits; 32 se citan en esta copia fuera de este archivo y 10 solo en documentos de trabajo que no se publican), ordenados por fecha. Es una lectura mecánica: para los commits que fijan una regla (asunto con «regla», «fijada», «antes de calcular» o «aclaración») se copia el texto que agregaron, hasta 60 líneas por archivo y 3 archivos, sin los archivos generados (datos, wiki, sitio, PDF) ni el plan de trabajo, que no se publica; el commit de las reglas de D a J muestra completos sus cinco archivos de `pipeline/`, uno por regla, y no sus tests. Los demás commits citados solo listan fecha, asunto y archivos. La línea «primer commit posterior que toca los mismos archivos» da el primer commit, sin contar merges, que desciende del citado y cambia alguno de sus archivos (`git log --ancestry-path --no-merges`): dice cuánto tiempo pasó entre la regla y el código que vino después, a veces minutos, y no prueba cuándo se calculó cada cifra. Los merges sin cambios propios no tienen esa línea.

## `94580fd` · 2026-11-15 07:30 UTC

**Asunto:** T1: event register, interference classes, 50 m pad clustering

**Archivos:** `pipeline/checks.py`, `pipeline/sql/01_staging.sql`, `pipeline/sql/02_core.sql`, `pipeline/sql/04_interferencia.sql`, `pipeline/sql/05_eventos.sql`, `pipeline/wiki.py`, `tests/test_pipeline.py`, `tests/test_wiki.py`

**Primer commit posterior que toca los mismos archivos:** `04625c6` · 2026-11-15 07:47 UTC · Fase 2: atiende la revision (historial del grafo, clave del libro, avisos, TEF meses 0-1, enlaces de pad, escape)

(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)

## `39c7dfe` · 2026-11-15 21:19 UTC

**Asunto:** P2 hijo: regla fijada antes de correr

**Archivos:** `README.md`, `docs/caso-interferencia.md`, `docs/verificacion.md`, `pipeline/hijo.py`, `wiki/hallazgos/ledger.csv`

**Primer commit posterior que toca los mismos archivos:** `3c81d21` · 2026-11-15 21:33 UTC · P2 hijo: modulo, marts, pagina, hipotesis, claims y pruebas

Texto agregado en `README.md`:

~~~
Más: `wiki/` (hallazgos, operadoras, áreas, pads y grafo, con el libro de siete hipótesis con umbral fijo), `docs/proceso/` (arquitectura, decisiones y planes) y `agente/` (operaciones, evaluación y servidor MCP).
~~~

Texto agregado en `docs/caso-interferencia.md`:

~~~
6. Pruebas corridas: siete hipótesis con umbral fijo, escrito de antemano en un libro versionado y no ajustado después de ver resultados, y 13 subconjuntos de robustez que se publican aunque debiliten el resultado; la descomposición agrega 141 intervalos sin ajuste por comparaciones múltiples, así que alguno puede quedar fuera de cero por azar.
~~~

Texto agregado en `docs/verificacion.md`:

~~~
- **Registro de eventos** por pozo (fractura, primera producción, cambios de estado y de extracción, cierres, saltos de agua, quiebres de caudal) y **libro de hallazgos**: siete hipótesis con umbral fijo, reevaluadas con cada dato nuevo y registradas en un CSV versionado.
~~~

## `d4a7355` · 2026-11-19 09:10 UTC

**Asunto:** Familia de replicaciones: la regla de Wyoming y la lectura 'se replica en k de n' quedan fijadas antes de bajar o medir nada de Wyoming

**Archivos:** `README.md`, `pipeline/familia.py`, `pipeline/wyoming/__init__.py`, `tests/test_familia.py`

**Primer commit posterior que toca los mismos archivos:** `d6a6ae8` · 2026-11-19 12:29 UTC · Replicacion: main de otra cuenca escribe la pagina de esa cuenca y no la de Colorado

Texto agregado en `README.md`:

~~~
Hecho con asistencia de IA; cada cifra de esta página se verifica contra el warehouse con `uv run python -m pipeline.claims` y hay 551 tests.
~~~

Texto agregado en `pipeline/familia.py`:

~~~
"""La familia de replicaciones: la lectura conjunta de las cuencas, con la regla fijada antes de calcular ninguna cifra de una cuenca nueva.

REGLA FIJADA (2026-11-19, antes de bajar la produccion de Wyoming; no se cambia despues de ver resultados).

Las cuencas de la familia, con su nombre, son las que replican la huella de interferencia de Vaca Muerta:
  * Colorado (cuenca DJ), la primera replicacion, ya publicada en `wiki/hallazgos/replicacion.md`;
  * Wyoming (WOGCC), la unica jurisdiccion que la auditoria de `wiki/hallazgos/fuentes_mundo.md` deja entrar ademas de Argentina
    (que es la cuenca original, no una replicacion), por la regla de elegibilidad y nada mas.
Una cuenca se agrega a la familia solo con una auditoria que la deje entrar por esa regla, y se agrega antes de ver su resultado.

Cada cuenca se lee con la misma regla de `replicacion_colorado` (pipeline/replicacion.py: brecha del mes 1 negativa con el limite
superior del IC por bloques de 5 km menor que 0, y brecha previa limpia menor en valor absoluto), con los mismos filtros y las mismas
semillas. La lectura de la familia es una frase, "se replica en k de n", con TODAS las cuencas listadas, cada una con su lectura:
  * "se replica", "no se replica" o "no se pudo medir" con el motivo escrito;
  * k cuenta las cuencas que se replican y n todas las de la familia, las que no se pudieron medir incluidas;
  * no hay estimacion conjunta, ni promedio, ni peso por cuenca: es la validez externa de la huella, no un efecto comun;
  * ninguna cuenca se quita de la lista despues de ver su resultado: si falta el resultado de una, la lectura no se arma.
"""
from __future__ import annotations

# (id de la cuenca, nombre en una frase); el orden es el de la lista de la pagina.
FAMILIA: tuple[tuple[str, str], ...] = (("colorado", "Colorado"), ("wyoming", "Wyoming"))

LECTURAS = ("se replica", "no se replica", "no se pudo medir")


def lectura_cuenca(se_replica: bool | None, motivo: str = "") -> str:
    """`se_replica` es el resultado de la regla; None es una cuenca que no se pudo medir (el motivo es obligatorio)."""
    if se_replica is None:
        if not motivo.strip():
            raise ValueError("una cuenca que no se pudo medir lleva el motivo escrito")
        return f"no se pudo medir: {motivo.strip()}"
    return "se replica" if se_replica else "no se replica"


def lectura_familia(resultados: dict[str, tuple[bool | None, str]]) -> dict:
    """`resultados`: id de cuenca -> (se_replica o None, motivo). Devuelve k, n, la frase y la lista completa, en el orden de FAMILIA."""
    ids = [i for i, _ in FAMILIA]
    faltan = [i for i in ids if i not in resultados]
    sobran = [i for i in resultados if i not in ids]
    if faltan or sobran:
        raise ValueError(f"la lectura de la familia pide exactamente {ids}: faltan {faltan}, sobran {sobran}")
    filas = [(i, nombre, lectura_cuenca(*resultados[i])) for i, nombre in FAMILIA]
    k = sum(1 for i, _, _ in filas if resultados[i][0] is True)
    n = len(filas)
    frase = f"Se replica en {k} de {n} cuencas: " + "; ".join(f"{nombre} ({lec})" for _, nombre, lec in filas) + "."
    return {"k": k, "n": n, "frase": frase, "cuencas": filas}
~~~

Texto agregado en `pipeline/wyoming/__init__.py` (primeras 60 de 68 líneas):

~~~
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
~~~

## `bddf1e0` · 2026-11-20 18:20 UTC

**Asunto:** Mecanismo por geometría: la regla y las constantes, antes de calcular ninguna cifra

**Archivos:** `pipeline/mecanismo.py`

**Primer commit posterior que toca los mismos archivos:** `8452211` · 2026-11-20 18:41 UTC · Mecanismo por geometría: cálculo, marts y tests de la regla fijada en bddf1e0

Texto agregado en `pipeline/mecanismo.py` (primeras 60 de 135 líneas):

~~~
"""El mecanismo medido con la geometria de las ramas: padres al costado de la rama del hijo contra padres en su punta.

Se corre despues de pipeline.trayectorias:  uv run python -m pipeline.mecanismo

REGLA FIJADA ANTES DE CORRER (2026-11-20). Este archivo es el primer commit de la unidad: la regla, las constantes y los umbrales
del veredicto. Antes de fijarla no se calculo ninguna cifra de resultado con este diseno (ni brechas, ni diferencias entre
posiciones, ni conteos de eventos por posicion o por banda). Todo lo que falta decidir esta decidido aca; si algo resulta
ambiguo al calcular, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra de resultado.

Pregunta: la pagina de la regla de parada (`wiki/hallazgos/eje_parada.md`) cerro el eje de la brujula y dijo que "la geometria de
las ramas no se pudo probar". Con las ramas publicadas (`mart_trayectoria_par`, `mart_par_rama`) si se puede. Esta es una prueba
NUEVA, no una repeticion del eje: la posicion del padre se mide respecto de la rama de cada hijo (su costado o su punta), que no
es la disposicion de pads de la cuenca. El mecanismo que se pone a prueba: el padre que queda al costado de la rama del hijo, en
paralelo, rinde menos que el que queda en su punta, a igual distancia entre ramas.

Eventos y muestra (como el estudio principal, con la distancia entre ramas en lugar de la distancia de superficie):
  * Pares: las filas de `mart_trayectoria_par` (hijo, padre, mes de fractura, distancia minima entre ramas `m_min` en metros)
    unidas a `mart_par_rama` por (hijo, padre). El padre cumple la regla de edad del estudio principal (al menos 6 meses de
    produccion en el mes de la fractura del hijo), que ya trae `int_par_padre_hijo`.
  * Un evento es un (padre, mes de fractura del hijo). El hijo que fija el evento es el de menor `m_min` entre los pares
    del evento (empate: el de menor id). La banda, la posicion, el paralelismo y el angulo al SHmax son los de ese par.
  * El padre entra con la base de los meses -3 a -1 mayor que 1 m3/d de petroleo, y el indice es su caudal del mes sobre esa
    base, como en `pipeline.placebo.marco`.
  * Muestra del contraste: eventos con `m_min` menor que LATERAL_CERCANO_M = 1.000 m, `paralelas` verdadera (diferencia de
    azimut de 20 grados o menos) y `posicion` en {costado, punta}. Los "mixto" y los no paralelos no entran.
  * Bandas de distancia lateral: 0 a 300, 300 a 600 y 600 a 1.000 m (el limite inferior incluido, el superior no).
  * Control lateral: los eventos cuyo hijo mas cercano por ramas queda a LATERAL_CONTROL_M = 2.000 m o mas de la rama del padre
    (mismas reglas de padre y de base). Cada evento se mide contra el control de su misma edad: el grupo de edad del padre en
    el mes del evento (6 a 11, 12 a 23, 24 a 47, 48 o mas meses) y el mismo k. Un grupo de edad con menos de
    MIN_CONTROL_EDAD = 5 controles con dato en ese k no da control y sus eventos quedan afuera de ese k.

Estimador (el del estudio principal: cada padre indexado contra su propia base, brecha entre medianas):
  * brecha de un conjunto de eventos G en el mes k = mediana del indice de G en k menos la mediana, sobre los eventos de G, del
    indice mediano del control de su grupo de edad en k. Con esa resta el control tiene la misma mezcla de edades que G.
  * contraste de una banda b = brecha de los costados de b menos brecha de las puntas de b. Es la cantidad central de la prueba
    (H-G1): negativa si el costado rinde menos que la punta.
  * contraste principal = promedio de los contrastes de las tres bandas pesado por los eventos de cada banda (costados mas
    puntas de la banda con dato en k). Una banda con menos de MIN_GRUPO_BANDA = 5 eventos en el costado o en la punta no tiene
    contraste y no entra al promedio (su peso es cero).
  * IC 95%: bootstrap de percentiles (2,5 y 97,5) con REPS_BOOT repeticiones que remuestrean bloques de 5 km (el bloque del pad
    del hijo que fija el evento, la misma grilla que `pipeline.bloques`), con semilla fija SEMILLA_MECANISMO. En cada
    remuestra se recalculan controles, brechas, pesos y contraste. Las remuestras sin ninguna banda con contraste se descartan.

Modelo principal, el unico que da el veredicto:
  * contraste principal en k = 1, base de los meses -3 a -1, eventos del estudio principal (base mayor que 1 m3/d) y el IC por
    bloques de 5 km.
  * Contraste placebo en k = -1 (antes de que el hijo fracture): misma muestra y mismo estimador, pero con la base limpia de los
    meses -6 a -4, la que usa `pipeline.placebo` para su pretendencia (con la base principal el mes -1 es parte de la base y no
    puede mostrar nada), con los eventos que pasan las dos bases y con el IC por bloques de 5 km.

Veredicto (se aplica en este orden):
  * "sin muestra": menos de MIN_EVENTOS_POSICION = 80 eventos en los costados o menos de 80 en las puntas en el modelo
    principal (eventos con indice en k = 1 y control de su edad, sumados las tres bandas), o ninguna banda con contraste.
    No hay veredicto.
  * "sostiene": el contraste principal en k = 1 tiene el limite superior de su IC menor que cero (negativo, con IC que excluye
    cero) Y el contraste placebo en k = -1 tiene un IC que incluye cero.
  * "ubicación": el contraste principal en k = 1 tiene el limite superior de su IC menor que cero Y el contraste placebo en
    k = -1 tambien tiene un IC que excluye cero (con cualquier signo): la diferencia viene de donde estan los pozos, no
    del mecanismo.
  * "no firme": cualquier otro caso (entre ellos, un IC del contraste en k = 1 que incluye cero o un contraste positivo con IC
~~~

## `76d9831` · 2026-11-20 18:21 UTC

**Asunto:** Alcance y dilución entre ramas: la regla y las constantes, antes de calcular ninguna cifra

**Archivos:** `pipeline/alcance_rama.py`

**Primer commit posterior que toca los mismos archivos:** `b582559` · 2026-11-20 18:54 UTC · Alcance y dilución entre ramas: la corrida, los marts y las pruebas

Texto agregado en `pipeline/alcance_rama.py` (primeras 60 de 140 líneas):

~~~
"""Alcance y dilución de la huella medidos entre ramas: la brecha del mes 1 con la distancia entre la rama del hijo y la del padre.

Se corre despues de pipeline.trayectorias:  uv run python -m pipeline.alcance_rama

Para que sirve. El estudio mide la distancia entre un hijo y un padre en superficie (boca contra boca). La pagina de trayectorias
(wiki/hallazgos/trayectorias.md) mostro que esa distancia clasifica mal: el 23% de los pares cercanos en superficie (menos de
1 km) tiene las ramas a 1 km o mas, y el 8% de los pares de control (2 a 5 km) tiene las ramas a menos de 1 km. Esta pagina
repite la medicion del alcance de la huella y de la dilucion del control con la distancia entre ramas en lugar de la de superficie.

REGLA FIJADA ANTES DE CORRER (2026-11-20, en un commit que solo trae este encabezado y las constantes, sin ninguna funcion de
calculo; no se cambia despues de ver resultados). Se publican todos los resultados, favorables o no. Un veredicto "no firme" o
"sin muestra" es un resultado terminado: no se rediseña la regla para evitarlo. Fuente del plan: fase 4 del proyecto, unidad U1b.

Que se habia mirado antes de fijarla
- Publicado en el repo: la pagina de trayectorias (cobertura, la distancia entre ramas por banda de superficie, el 23% y el 8% de
  arriba) y mart_par_rama (eje, solape y posicion del padre). Ninguna brecha de caudal se calculo con la distancia entre ramas
  antes de fijar esta regla; tampoco se conto ninguna banda de esta pagina.
- Los umbrales salen del plan de la fase 4, escrito el mismo dia antes de calcular. El umbral de -10 puntos es el de la regla R1
  de pipeline.bloques (CRUCE_R1) aplicado a la banda mas cercana.

Datos y eventos (el modelo principal; solo de el sale el veredicto)
- Eventos: los del estudio principal, placebo.marco(D, D["hijo_mes"], ks=(1,), base=BASE_ORIGINAL), con D = placebo.cargar(con):
  cada evento es un padre y el mes de fractura de su hijo mas cercano en superficie (desempate por el menor id), el padre con al
  menos 6 meses de produccion y una base de los meses -3 a -1 mayor que 1 m3/d. Indice = caudal por dia del mes k sobre esa
  base. Los eventos son los mismos del estudio; lo unico que cambia es la distancia que los clasifica.
- Muestra de esta pagina: los eventos cuyo par (hijo, padre) esta en mart_trayectoria_par, es decir, con la rama del hijo y la del
  padre medidas. Un padre o un control sin rama medida no entra. El hijo de cada evento es el de placebo.marco (el mas cercano en
  superficie) y la distancia entre ramas del evento es la menor distancia entre las dos ramas en planta (`m_min` de
  mart_trayectoria_par), en metros.
- Alcance de la muestra: mart_trayectoria_par solo tiene pares con las bocas a menos de 5 km, asi que un padre con la rama a menos
  de 2 km de la del hijo pero la boca a mas de 5 km no esta. Esta pagina lo dice y no lo corrige.
- Cobertura de la muestra: las ramas medidas cubren entre 80 y 94% de los hijos fracturados de 2016 a 2023 pero solo el 39% de
  2024 y el 25% de 2025 (la fuente todavia no publica la mayoria de los pozos recientes), asi que la muestra es sobre todo de 2016
  a 2023. La pagina y el README lo dicen junto al veredicto, con los eventos por ano del hijo.
- Control lateral: eventos de la muestra con m_min de 2.000 m o mas. Para un cercano en una banda, el control es siempre este y
  nunca los de la banda vecina. Un evento que sea a la vez cercano y control no existe: las bandas no se solapan.
- Brecha: mediana del indice de los eventos del grupo menos mediana del indice del control, sin contar los datos faltantes
  (placebo.brecha). Se publica en puntos de indice (100 por la brecha).
- Intervalos: bootstrap de percentiles 95% (2,5 y 97,5) por bloques espaciales de 5 km (pipeline.bloques: el bloque del pad del
  hijo del evento, `bloques.cargar(con)` y la grilla `bloque_5km`), REPS_BOOT repeticiones y semilla SEMILLA_ALCANCE. Cada
  repeticion remuestrea bloques completos de la muestra y calcula con ellos TODAS las cantidades de la pagina; asi la brecha de
  cada banda, la diferencia de H-R2 y la de H-R3 salen de las mismas remuestras. Una remuestra en que un grupo queda vacio se
  descarta y se cuenta.

H-R1, alcance. Brecha del mes 1 (k = 1) por banda de la distancia entre ramas, cada una contra el control lateral:
BANDAS_RAMA_M = 0 a 300, 300 a 600, 600 a 1.000 y 1.000 a 2.000 m (cada banda incluye el extremo de abajo y deja afuera el de
arriba). Se publica tambien la cantidad de eventos de cada banda y del control.
  1. "sin muestra": alguna de las cuatro bandas o el control lateral tiene menos de N_MIN (100) eventos con el indice del mes 1
     medido, o la muestra tiene menos de MIN_BLOQUES (30) bloques de 5 km.
  2. "alcance medido": el IC de la banda de 0 a 300 m queda entero por debajo de -10 puntos (limite alto menor que -0,10) Y la
     brecha de la banda de 1.000 a 2.000 m tiene valor absoluto menor que 5 puntos (UMBRAL_PLANO) con un IC que incluye cero. El
     alcance que se informa es el borde superior de la ultima banda (la mas lejana) cuyo IC excluye cero.
  3. "gradiente": el IC de la banda de 1.000 a 2.000 m excluye cero. No se informa un alcance: la huella sigue por lo menos hasta
     esa banda (cota inferior del alcance), y la pagina dice que no se midio el borde.
  4. "no firme": en cualquier otro caso.
  El orden es ese; las condiciones de 2 y 3 no pueden darse juntas.

H-R2, dilucion de la huella por la distancia de superficie. Sobre los mismos eventos de la muestra, en las mismas remuestras:
  * A = brecha del mes 1 de los padres cercanos por distancia entre ramas (m_min menor que 600 m, CERCA_RAMA_M) contra el control
    lateral (m_min de 2.000 m o mas).
~~~

## `c71f3a5` · 2026-11-20 19:34 UTC

**Asunto:** Regla del calendario de golpes: matrices de costo, optimizador y backtest ajustado en 2023 (solo encabezado y constantes, sin ningun calculo)

**Archivos:** `pipeline/calendario_golpes.py`

**Primer commit posterior que toca los mismos archivos:** `a663620` · 2026-11-20 19:48 UTC · Calendario de golpes: calculo del backtest, el optimizador y las matrices de costo, con pruebas sobre funciones puras y un panel sintetico

Texto agregado en `pipeline/calendario_golpes.py` (primeras 60 de 179 líneas):

~~~
"""Calendario de golpes: matrices de costo, optimizador de calendario y backtest (ajustado en 2023, predice 2024 a 2026).

Se corre despues de pipeline.golpes_mismo_padre:  uv run python -m pipeline.calendario_golpes

Para que sirve. Es la tercera y ultima pieza del optimizador de calendario (U6b de la fase 4). pipeline.golpes_mismo_mes (PR #83)
midio cuanto pierde un padre en un mes de golpe, P = a + b k, y no pudo decidir si agrupar hijos ahorra; pipeline.golpes_mismo_padre
(PR #86, U6a) comparo cada padre consigo mismo y termino en "sin muestra" en las dos cuencas (87 padres y 197 meses de golpe en
Vaca Muerta, 19 y 38 en Colorado). Como U6a no decidio un caso de costo, queda lo ultimo publicado, el modelo agrupado de #83
(a = 13,9 y b = -1,7 dias de base en Vaca Muerta, con b negativo y un IC que incluye el cero), y esta unidad corre los DOS casos
de costo, los valua con la grilla de pipeline.decision (PRECIOS, TASAS, REZAGOS) y mide si el modelo, ajustado en 2023, predice la
perdida de 2024 a 2026. Antes de usar b lo acota a 0 o mas.

REGLA FIJADA ANTES DE CORRER (2026-11-20, en un commit que solo trae este encabezado y las constantes, sin ninguna funcion de
calculo; no se cambia despues de ver resultados). Se publican todos los resultados, favorables o no. Un "no firme" o un "sin
muestra" es un resultado terminado: no se rediseña la regla para evitarlo.

Huecos del plan que esta regla cierra antes de calcular (el plan dice solo "matrices de costo valuadas en PRECIOS/TASAS/REZAGOS,
bajo los dos casos, y un backtest ajustado en 2023 que predice 2024 a 2026, con b acotado a 0 o mas"; no dice que elige el
optimizador, contra que se compara el arrepentimiento ni como se puntua el backtest ni con que umbrales). Se fijan aqui:
  1. Que elige el optimizador: para cada padre, en que meses de calendario caen los hijos que se fracturan a menos de 1 km de el.
  2. Contra que se compara el arrepentimiento: contra el calendario realmente observado de ese padre.
  3. Como se puntua el backtest, y con que umbrales sale el veredicto.
  4. Como se acota b, y que se hace con a.
  5. Que no se corre Colorado (ver abajo).

Que se habia mirado antes de fijarla
- Todo lo publicado de #83 y #86 en las dos cuencas: los coeficientes agrupados, sus IC, el veredicto "sin perdida medible" de #83, el
  "sin muestra" de #86 y sus conteos de padres y meses de golpe.
- NO se habia calculado ninguna cantidad de esta prueba: ni cuantos meses de golpe aislados hay en 2023 ni en 2024 a 2026, ni
  ningun calendario, ni ningun arrepentimiento, ni ningun puntaje fuera de muestra. El tamaño de las muestras de entrenamiento y
  de prueba se ve por primera vez cuando corre el modulo, y puede ser "sin muestra". Por eso es una prueba de regla informada en
  el sentido de #81 y #83 solo en lo que ya estaba publicado (el a y el b agrupados); el backtest es nuevo.

Que se reutiliza (de pipeline.golpes_mismo_mes y pipeline.golpes_mismo_padre, sin copiar)
- Los eventos, la perdida P (dias de produccion de base, meses -1 a 6 contra el indice mediano de los controles), el volumen
  V = P por el caudal de base (m3), k (hijos a menos de KM_CERCA fracturados ese mes), el aislamiento y la ventana completa: las
  definiciones de golpes_mismo_mes.eventos y golpes_mismo_mes.muestras, tal cual. El pad del padre es el de
  golpes_mismo_padre.cargar_pad_padre. La grilla de valor es la de pipeline.decision (PRECIOS, TASAS, REZAGOS) con
  decision.valor_indicativo, sin tocarla.
- Muestra de ajuste y de prueba del backtest: la muestra PRINCIPAL de #83 (cercanos aislados con la ventana completa). Entrenamiento:
  eventos cuyo mes de fractura cae en ANIO_ENTRENA (2023). Prueba: eventos cuyo mes de fractura cae en ANIOS_PRUEBA (2024 a 2026;
  con el dato a 2026-10 y la ventana completa, los ultimos hijos son de 2026-04). Es una partida por fecha, no al azar.

Los dos casos de costo (modelos de la perdida P de un mes de golpe con k hijos cercanos; los dos se ajustan en la muestra de
entrenamiento y los dos se acotan antes de usarlos)
- Caso ADITIVO, P = c k: el costo es por hijo y no depende de como se reparten los hijos en meses. c es de minimos cuadrados por el
  origen (c = suma(k P) / suma(k^2)); si sale menor que cero se acota en 0. Bajo este caso el calendario no cambia el costo
  total: el arrepentimiento es cero por construccion y la pagina lo dice, no lo presenta como un resultado.
- Caso FIJO MAS HIJO, P = a + b k: un costo fijo a por mes de golpe y b por hijo. Se acota asi, en este orden: (i) minimos
  cuadrados (a, b) sin controles; (ii) si b < 0, b = 0 y a se vuelve a ajustar sin k (a = media de P en la muestra de
  entrenamiento); (iii) si a < 0, a = 0. El b sin acotar y si el acotado se uso se publican. Un a o un b acotado es una
  decision de la regla, no una estimacion; la pagina lo rotula. Con b = 0 todos los hijos de un mes de golpe cuestan lo mismo que
  uno solo (phi = 1), el extremo de mas ahorro por agrupar.
- Referencia del backtest, que no es un caso de costo: M0, la media de P en la muestra de entrenamiento.
- Sin controles en el modelo principal (la decision solo mueve k). Sensibilidad S1, "con controles": los dos casos con k12 y el
  logaritmo del caudal de base de #83 como controles, centrados en la media de entrenamiento y sin efectos fijos (el año es uno solo
  en el entrenamiento, y las categorias de edad y operador de la prueba pueden no estar en el). Se publica; no cambia el veredicto.
- Descriptivo con la muestra completa: el modelo agrupado de #83 tal cual (golpes_mismo_mes.ajuste: con S, controles y efectos fijos
  de edad, año y operador, sobre toda la muestra principal 2016 a 2026), acotado con el mismo orden de pasos, y su caso aditivo
  (la misma especificacion con k sin constante). Valua el calendario observado de toda la muestra. Es dentro de muestra: no
~~~

## `59b3a26` · 2026-11-20 20:33 UTC

**Asunto:** Dosis con geometría de ramas: la regla y las constantes, antes de calcular ninguna cifra

**Archivos:** `pipeline/dosis_geometria.py`

**Primer commit posterior que toca los mismos archivos:** `e0d4007` · 2026-11-20 20:56 UTC · Dosis con geometría de ramas: la puerta de potencia, sus marts, la página, claims y tests

Texto agregado en `pipeline/dosis_geometria.py` (primeras 60 de 114 líneas):

~~~
"""Dosis y respuesta con la geometria de las ramas, detras de una puerta de potencia: los padres cercanos medidos entre ramas.

Se corre despues de pipeline.alcance_rama y pipeline.potencia_dosis:  uv run python -m pipeline.dosis_geometria

REGLA FIJADA ANTES DE CORRER (2026-11-20, en un commit que solo trae este encabezado y las constantes, sin ninguna funcion de
calculo; no se cambia despues de ver resultados). Se publican todos los modelos que se calculen, favorables o no. Un veredicto
"sin muestra" o "la geometria no da mas potencia" es un resultado terminado: no se rediseña la regla para evitarlo. Fuente del plan:
fase 4 del proyecto, unidad U4. Sigue a pipeline.dosis (seccion 3.8), pipeline.potencia_dosis (el MDE de hoy) y pipeline.alcance_rama
(la definicion de padre cercano entre ramas).

Que se habia mirado antes de fijarla
- Publicado en el repo: wiki/hallazgos/dosis.md, potencia_dosis.md, trayectorias.md y alcance_rama.md. De la potencia de hoy se leyo el
  MDE80 de Holm de las cuatro variables del modelo conjunto A (de 0,221 a 0,313 desvios de la caida; el mejor, el de la presion
  maxima, 0,221).
- De la muestra de esta pagina solo se vio que mart_trayectoria_par existe con las columnas hijo, padre, mes_frac, km, m_min,
  m_mediana, dtvd_m y misma_unidad, y que int_interferencia_evento tiene las bandas cercano, intermedio y control. No se conto el
  tamaño del subconjunto de esta pagina, no se calculo ningun error estandar ni ningun coeficiente con el.

Pregunta. El mejor efecto minimo detectable de la dosis hasta hoy es de 0,22 desvios de la caida. Medir el padre cercano por la
distancia entre ramas (en vez de la de superficie) podria afinar la exposicion y dar mas potencia. Esta pagina lo prueba en dos
pasos: primero la puerta de potencia (el MDE80 de la muestra de padres cercanos entre ramas, sin estimar ningun efecto), y solo si
la puerta pasa, el modelo conjunto de pipeline.dosis sobre esa muestra.

Muestra (la misma para los dos pasos)
- Eventos: los de pipeline.dosis._dataset_a (los eventos 'cercano' de int_interferencia_evento, padre a menos de 1 km en superficie del
  hijo_cercano; el hijo, el mes, la caida A y la caida B no cambian), SOLO los que cumplen: el par (hijo_cercano, padre) del evento esta
  en mart_trayectoria_par (la rama del hijo y la del padre medidas) y su `m_min` (menor distancia entre ramas en planta) es menor que
  CERCA_RAMA_M = 600 m, la misma definicion de padre cercano entre ramas de pipeline.alcance_rama (H-R2, medida A).
- Caso completo: el de pipeline.dosis y pipeline.potencia_dosis._caso_completo (caida A finita, controles completos, las cuatro
  variables finitas). Los controles, las dummies de terminacion, las celdas de efectos fijos y la estandarizacion se rehacen DENTRO del
  subconjunto con las mismas funciones (dosis._controles, dosis._std). km_min sigue siendo la distancia de superficie y `m_min` no
  entra como control: la regla del modelo no cambia, solo la muestra.
- Un subconjunto no puede traer eventos que el modelo de dosis no tenga: los padres con la rama a menos de 600 m del hijo pero con la
  boca a 1 km o mas del hijo no estan en la muestra de dosis. La pagina lo dice y no lo corrige.
- Resultados: A (caida del indice al mes 1) decide; B (caudal por dia) se calcula igual, solo para el MDE analitico y, si la puerta
  pasa, para el modelo conjunto, y no cambia ningun veredicto.
- Los conglomerados son los pads hijo de pipeline.dosis (pad_id del hijo; sin pad, el hijo es su propio conglomerado).
- "sin muestra": el caso completo de A tiene menos de N_MIN_CASOS (100) eventos o menos de PADS_MIN (30) pads hijo. No se calcula
  nada mas y no hay puerta.

Paso 1, la puerta de potencia (no se lee ni se publica ningun coeficiente; solo el ancho de los intervalos)
  * Cuenta analitica, la de pipeline.potencia_dosis: el modelo conjunto de las cuatro variables de pipeline.dosis sobre la muestra, con
    dosis._ajuste y bootstrap de pads hijo con B_GATE = dosis.B_MAIN (2.000) y semilla propia; SE = (ic_alto menos ic_bajo) sobre
    (2 por 1,96) y despues sobre el desvio (ddof = 0) de la caida de la muestra; MDE80 de Holm = (z(1 menos 0,05 sobre 2 por 4) mas
    0,8416) por SE, con m = M_HOLM = 4 (las mismas cuatro variables). Se publica tambien el MDE80 sin ajustar. Del bootstrap solo se usa
    el ancho del IC de percentiles.
  * Estadistico de la puerta: el menor de los cuatro MDE80 de Holm (el de la mejor variable). Es lo que se compara con "el mejor de
    hoy", 0,221 (presion maxima, modelo conjunto A de pipeline.potencia_dosis), que se fija en MDE_REF = 0,22. Se publica tambien el
    mayor de los cuatro (el estadistico del veredicto de pipeline.potencia_dosis, 0,31 hoy) y su codigo de potencia_dosis.veredicto,
    como informacion; no deciden la puerta.
  * Puerta: pasa si el menor MDE80 de Holm de A es MENOR que MDE_REF (0,22). Si es igual o mayor, el veredicto es "la geometria no da
    mas potencia", se publica el MDE y se termina (unidad terminada: no se corre el paso 2).
  * Simulacion de planta y recupera, la de pipeline.potencia_dosis.simular sobre la misma muestra y el mismo modelo conjunto A (ajusta
    el modelo, le quita a la caida el efecto estimado de las cuatro variables, planta un efecto delta por variable y reajusta con
    B_SIM = 300 sobre N_CORRIDAS = 200 remuestras de pads). Niveles: delta 0 (tamaño), 0,1, 0,2, MDE_REF (0,22), el MDE80 sin ajustar de
    cada variable (con la regla sin ajustar) y el MDE80 de Holm de cada variable (con la regla de Holm). Se publica la potencia
    empirica con su error de Monte Carlo. La simulacion valida la cuenta analitica si la potencia empirica en el MDE80 (con su regla)
    esta entre 0,70 y 0,90 en las cuatro variables; si no, la pagina lo dice y la puerta SIGUE siendo la analitica. La simulacion usa
    los coeficientes ajustados solo para armar la caida limpia; no se publican como resultado.
  * Tambien se publica, como en pipeline.potencia_dosis, cuantos pads y eventos harian falta para ver 0,1 y 0,2 desvios.
~~~

## `4b19b90` · 2026-11-20 20:33 UTC

**Asunto:** Riesgo de golpe fuerte: la regla y las constantes, antes de calcular ninguna cifra

**Archivos:** `pipeline/riesgo.py`

**Primer commit posterior que toca los mismos archivos:** `b8f718f` · 2026-11-20 20:53 UTC · Riesgo de golpe fuerte: la corrida, los marts y las pruebas (la regla sigue en 4b19b90)

Texto agregado en `pipeline/riesgo.py` (primeras 60 de 151 líneas):

~~~
"""Riesgo de golpe fuerte: cuan probable es que un padre cercano pierda mas de 30 puntos de indice al mes 1 de la fractura de un hijo.

Se corre despues de pipeline.trayectorias:  uv run python -m pipeline.riesgo

Para que sirve. El modelo de costo puntual (wiki/hallazgos/anisotropia.md) predice barriles y falla: su R2 fuera de muestra es de
-0,15. Esta pagina hace la pregunta que un operador puede usar: dado un padre y un hijo que se va a fracturar cerca, cuan probable
es un golpe fuerte. Es un modelo de clasificacion probado hacia adelante en el tiempo (entrena con los hijos fracturados hasta
2022 y se prueba con los de 2023 y 2024), con la distancia entre ramas y la geometria de las ramas entre sus variables.

REGLA FIJADA ANTES DE CORRER (2026-11-20, en un commit que solo trae este encabezado y las constantes, sin ninguna funcion de
calculo; no se cambia despues de ver resultados). Se publican todos los modelos que se calculen, favorables o no. Un veredicto
"no predice el riesgo" o "sin muestra" es un resultado terminado: no se rediseña la regla para evitarlo. Fuente del plan: fase 4
del proyecto, unidad U5.

Que se habia mirado antes de fijarla
- Publicado en el repo: la pagina de anisotropia (el modelo puntual, su R2 de -0,15 fuera de muestra), la de trayectorias y la de
  alcance entre ramas (la brecha del mes 1 por banda de distancia entre ramas). Ninguna probabilidad de golpe fuerte se calculo, y
  ningun ajuste de clasificacion se corrio, antes de fijar esta regla.
- Solo se conto cuantos eventos cercanos hay en cada ventana del corte (sin mirar ningun resultado): 673 de entrenamiento y 492 de
  prueba con el indice del mes 1 medido, de los cuales 515 y 302 tienen la rama del par medida. Con eso la regla de "sin muestra"
  (menos de 300 eventos de prueba) no es imposible de antemano.

Datos y eventos (el modelo principal; solo de el sale el veredicto)
- Eventos: las filas de int_interferencia_evento con banda = 'cercano' (el hijo mas cercano en superficie a menos de 1 km del padre;
  desempate por el menor id) que tienen el indice del mes 1 medido en int_interferencia_mes (k = 1, indice no nulo). Son los
  mismos eventos cercanos del estudio principal (placebo.marco, banda 0): un padre con al menos 6 meses de produccion y una base de
  los meses -3 a -1 mayor que 1 m3/d. Su hijo es `hijo_cercano` y su mes es `mes_frac`, el mes de fractura de ese hijo.
- Resultado ("golpe fuerte"): 1 si el indice del mes 1 del padre menos la mediana del indice del mes 1 de los controles de su mismo
  grupo de edad (`grupo_edad`; mart_interferencia_brecha con k = 1, columna `indice_control`, la mediana de los controles de 2 a
  5 km de ese grupo en todo el estudio, la misma que usa la brecha principal) es MENOR que UMBRAL_GOLPE (-0,30, es decir -30 puntos
  de indice). 0 en otro caso. La mediana de control sale de todo el periodo y no solo del entrenamiento: es la definicion del
  resultado, la del estudio principal, y no una variable del modelo; esta pagina lo dice en "Que NO prueba".
- Corte por fecha de fractura del hijo (`mes_frac`): entrenamiento de 2016-01 a 2022-12 (INICIO_ENTRENAMIENTO, FIN_ENTRENAMIENTO);
  prueba de 2023-01 a 2024-12 (INICIO_PRUEBA, FIN_PRUEBA). Los eventos de otras fechas no entran y se cuentan en la pagina. Los
  eventos de la prueba no se usan para elegir nada: no hay ningun ajuste.
- Cobertura de las ramas: las trayectorias laterales cubren alrededor del 76 al 98% de los hijos horizontales fracturados de 2016 a
  2023 (86% en conjunto) pero solo el 39% de los de 2024 y el 25% de los de 2025. La muestra es entonces sobre todo de 2016 a 2023
  y la ventana de prueba de 2023 a 2024 tiene pocos eventos de 2024 con la rama medida. Los eventos sin rama medida NO se
  descartan: entran con la distancia entre ramas faltante y su indicador (ver abajo). La pagina y el README lo dicen junto al
  veredicto.

Variables (columnas fijas; para el modelo principal son todas estas)
  km                    km_min de int_interferencia_evento: la distancia de superficie al hijo cercano.
  m_min                 la menor distancia entre las ramas en planta del par (hijo_cercano, padre), en metros, de mart_trayectoria_par.
  falta_rama            1 si el par (hijo_cercano, padre) no esta en mart_trayectoria_par (rama del hijo o del padre sin medir), 0 si esta.
  dif_azimut            dif_azimut de mart_par_rama para ese par, en grados (0 a 90).
  posicion_costado, posicion_mixto, posicion_punta   indicadoras de `posicion` de mart_par_rama para ese par.
  edad_meses            edad_meses del padre en el mes del evento (int_interferencia_evento).
  acum_m3_por_m         el petroleo acumulado del padre (m3, suma de fct_produccion.petroleo_m3 de los meses ANTERIORES a mes_frac) sobre
                        el largo de su rama horizontal en metros (dim_fractura_pozo.rama_horizontal_m del padre). Metros cubicos por metro.
  falta_largo_padre     1 si el padre no tiene rama_horizontal_m (nula o 0), 0 si la tiene.
  base_m3_d             base_m3_d de int_interferencia_evento: el caudal base del padre, de los meses -3 a -1.
  arena_por_m           toneladas de arena del hijo cercano (dim_fractura_pozo.arena_tn) sobre el largo de su rama horizontal en metros.
  etapas                dim_fractura_pozo.etapas del hijo cercano.
  falta_largo_hijo      1 si el hijo cercano no tiene rama_horizontal_m (nula o 0), 0 si la tiene.
  mismo_pad             1 si el padre y el hijo cercano tienen el mismo pad_id (int_pozo_ubicacion), 0 si no.
  hijos_1km             hijos_1km de int_interferencia_evento: los hijos fracturados ese mes a menos de 1 km del padre.
  operador_*, area_*    indicadoras del operador y del area (int_interferencia_evento, trim) del PADRE. Un nivel con menos de MIN_NIVEL (30)
                        eventos de entrenamiento se junta en `otro` (en operador y en area por separado), y un nivel que no aparece en
                        el entrenamiento va a `otro`.
~~~

## `6a4e194` · 2026-11-20 22:18 UTC

**Asunto:** Merge pull request #92 from GabrielRuizVarela/t3/fase4-riesgo

**Archivos:** `README.md`, `pipeline/claims.py`, `pipeline/riesgo.py`, `pipeline/run_all.py`, `pipeline/wiki.py`, `tests/test_riesgo.py`, `tests/test_run_all.py`, `wiki/hallazgos/linaje.md`, `wiki/hallazgos/riesgo.md`, `wiki/index.md`

**Primer commit posterior que toca los mismos archivos:** `6f2ff73` · 2026-11-21 19:06 UTC · Deslop de la prosa: quita repeticiones y relleno, congela las cifras con un test

(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)

## `05de1ca` · 2026-11-21 19:53 UTC

**Asunto:** Merge pull request #94 from GabrielRuizVarela/docs/deslop-pendientes

**Archivos:** (merge, sin cambios propios)

(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)

## `8f52ff1` · 2026-11-22 01:58 UTC

**Asunto:** Regla fijada del diseno causal (D1, D1b, D2): cabecera, constantes y umbrales, sin cifras calculadas

**Archivos:** `docs/plan-causal.md`, `pipeline/causal.py`

**Primer commit posterior que toca los mismos archivos:** `e19a93f` · 2026-11-22 02:09 UTC · Calcula D1, D1b y D2 segun la regla fijada en 8f52ff1

Texto agregado en `docs/plan-causal.md` (primeras 60 de 162 líneas):

~~~
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
~~~

Texto agregado en `pipeline/causal.py` (primeras 60 de 199 líneas):

~~~
"""Diseno causal: diferencias en diferencias escalonadas con controles aun no tratados, y el corte de agua como canal fisico.

Se corre despues de pipeline.build (y de pipeline.trayectorias para la lectura por posicion):  uv run python -m pipeline.causal

REGLA FIJADA ANTES DE CORRER (2026-11-21). Este archivo es el primer commit de la unidad: la regla, las constantes y los umbrales
del veredicto. Antes de fijarla no se calculo ninguna cifra con estos disenos (ni ATT, ni placebos, ni conteos de tratados o de
controles). Si algo resulta ambiguo al calcular, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: al fijarla se conocian las cifras publicadas del estudio (brecha del mes 1 de -19 a -23 puntos,
pretendencia de -2,5, -3,6 y -6,3 en los meses -3 a -1, salto de corte de agua de 0,187 mas de proporcion en los cercanos, dias
perdidos, alcance y contraste costado menos punta). El plan completo: docs/plan-causal.md, y la pagina
wiki/hallazgos/causal.md.

Por que: todo lo publicado compara padres cercanos con controles a 2 a 5 km de la misma edad, y los cercanos ya rendian menos antes
de la fractura (seleccion de zona de relleno). Aca el control es un padre que TAMBIEN recibira un hijo a menos de 1 km, pero mas
tarde (aun no tratado), y la tendencia previa se acota con una cota de sensibilidad. El corte de agua separa una comunicacion
fisica de un cierre preventivo: cerrar baja los dias, no mete agua.

Definiciones comunes:
  * Universo: pozos de `int_pozo_ubicacion`. Hijos y mes de fractura: `int_frac_hijo`. Distancia de superficie en km con la
    formula de `int_par_padre_hijo` (KM_POR_GRADO por grado, longitud por el coseno de la latitud del hijo).
  * Golpe a d km de un pozo i en el mes m: un hijo (distinto de i) fracturado en m a menos de d km de i, con m posterior al
    primer mes de petroleo de i. Sin la restriccion de 6 meses de edad, para ver tambien golpes a pozos jovenes.
  * Cohorte g_i: el primer mes con golpe a KM_TRATADO km. Tratado: edad (meses desde el primer mes de petroleo) en g de
    EDAD_MIN o mas, ningun golpe a KM_LIMPIO km en los VENTANA_PREVIA meses anteriores a g, y base valida.
  * Base: los meses BASE (de g - 6 a g - 4), los tres con fila en `fct_produccion`, con media de petroleo por dia calendario
    (petroleo_m3 / dias_mes) mayor que BASE_MIN m3/d.
  * Indice I_i(e) = petroleo_m3 / dias_mes del mes g + e sobre la base, recortado arriba en INDICE_TOPE. Mes sin fila: falta.
  * Control de la celda (g, grupo de edad, horizonte H): un pozo j con edad en g de EDAD_MIN o mas en el mismo grupo de edad
    (CORTES_EDAD: 6 a 11, 12 a 23, 24 a 47, 48 o mas meses), con base valida en g, sin golpe a KM_LIMPIO km en
    [g - VENTANA_PREVIA, g + H], y con su propio primer golpe a KM_TRATADO km despues de g + H y dentro de los datos (aun no
    tratado y alguna vez tratado). Un pozo puede ser control de muchas cohortes. S1 suma los nunca tratados (sin golpe a
    KM_TRATADO km en todo el dato) con las mismas condiciones.
  * ATT(g, a, e) = media de I de los tratados de la celda menos media de I de sus controles; la celda entra en e si tiene al menos
    1 tratado y MIN_CONTROLES_CELDA controles con dato en e. ATT(e) es el promedio de las celdas pesado por tratados con dato. En
    puntos de indice (x 100).
  * IC 95%: bootstrap de percentiles que remuestrea bloques de TAM_BLOQUE_KM km de la ubicacion de superficie de cada pozo
    (`pipeline.bloques.clave_bloque`), REPS repeticiones, semilla SEMILLA_CAUSAL. Los mismos sorteos para todas las cantidades
    de una misma muestra; un bloque sorteado entra con todos sus pozos, como tratados y como controles.

D1. Primera fractura a menos de 1 km y caudal del padre (principal).
  * Estimando ATT(1) con H = H_CORTO. Serie de e = -3 a 6 (E_SERIE). Pretendencia: beta(-3), beta(-2), beta(-1) contra la base.
  * Cota de sensibilidad (inspirada en Rambachan y Roth 2023, magnitudes relativas; version simplificada y conservadora, no su
    implementacion exacta): m = max(|b(-3)|, |b(-2) - b(-3)|, |b(-1) - b(-2)|); B(M) = |b(-1)| + 2 M m; intervalo robusto
    [IC bajo - B(M), IC alto + B(M)]; M* = (-IC alto - |b(-1)|) / (2 m), y 0 si eso es negativo (infinito si m es 0).
  * Potencia de la pretendencia (Roth 2022, informada, no decide): la pendiente lineal previa minima detectable con 80% de
    potencia, 2,8 veces el desvio bootstrap de la pendiente de b(-3), b(-2), b(-1).
  * Placebos. Rompe el diseno si su IC excluye cero y su valor absoluto es UMBRAL_ROTURA_PUNTOS o mas:
      - fecha falsa: g' = g - DESFASE_FECHA_FALSA para cada tratado, con las mismas condiciones de tratado y de control en g'.
      - distancia falsa: pseudo tratados con el primer golpe en [KM_FALSO_MIN, KM_FALSO_MAX) km y ninguno a KM_LIMPIO km en
        [g - VENTANA_PREVIA, g + H]; mismos controles.
      - nunca tratados: pozos sin golpe a KM_TRATADO km en todo el dato, con una fecha sorteada (semilla fija) de la
        distribucion de cohortes de los tratados entre las fechas en que cumplen las condiciones de tratado; mismos controles.
  * Dejar un operador afuera: ATT(1) sin los tratados y controles de cada operador del padre con MIN_TRATADOS_OPERADOR o mas
    tratados.
  * Veredicto, en este orden:
      - "sin muestra": menos de MIN_TRATADOS tratados con dato en e = 1 en celdas con control, o menos de MIN_BLOQUES bloques.
      - "no sobrevive a su placebo": rompe la fecha falsa, la distancia falsa o los nunca tratados.
      - "sostiene como causal bajo tendencias paralelas condicionales": IC alto de ATT(1) menor que UMBRAL_EFECTO_PUNTOS, M*
        de M_MIN o mas, y el IC alto de cada ATT(1) sin un operador menor que cero.
      - "no firme": cualquier otro caso.
~~~

## `7f2e499` · 2026-11-22 03:21 UTC

**Asunto:** D2 mide el corte de agua, no su volumen: lo dicen el resumen, la lectura y la fila del README

**Archivos:** `README.md`, `pipeline/causal.py`, `pipeline/claims.py`, `tests/fixtures/deslop_numeros_antes.json`, `wiki/hallazgos/causal.md`

**Primer commit posterior que toca los mismos archivos:** `3447714` · 2026-11-22 03:52 UTC · Claims de causal profundo: 74 cifras de la pagina D3 contra sus marts; el veredicto impreso va pegado a la primera cifra

(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)

## `74e3975` · 2026-11-22 03:25 UTC

**Asunto:** Regla de causal profundo: agua que entra o petroleo que sale, dosis, forma, donde se sostiene y Colorado, sin ninguna cifra calculada

**Archivos:** `docs/plan-causal-profundo.md`, `pipeline/causal_profundo.py`, `tests/test_causal_profundo.py`

**Primer commit posterior que toca los mismos archivos:** `b95331d` · 2026-11-22 03:35 UTC · D3: volumen de agua y de petroleo por dia, con sus placebos y marts

Texto agregado en `docs/plan-causal-profundo.md` (primeras 60 de 115 líneas):

~~~
# Plan causal profundo: qué hay debajo de la suba del corte de agua

Fecha: 2026-11-22. Rama `t3/causal-profundo`, que sale de la cabeza 7f2e499 de `t3/causal-diseno` (PR #98) para reusar
`pipeline/causal.py` sin tocarlo. La regla es el primer commit de la rama: `pipeline/causal_profundo.py` (cabecera,
constantes, funciones de veredicto) y sus pruebas, sin ninguna cifra calculada. El commit de regla 8f52ff1 de D1, D1b y D2
no se toca.

## De dónde sale

`pipeline.causal` dio una sola afirmación causal: la primera fractura de un hijo a menos de 1 km sube el corte de agua del
padre 13,8 puntos porcentuales (IC 9,5 a 19,9; 447 tratados) y la regla fijada le puso el nombre "comunicación física". Pero
el corte de agua es una proporción, W = agua / (agua + petróleo): sube si entra agua o si el petróleo cae con el agua quieta.
D1 ya mostró que el petróleo del padre cae en el mes de la fractura (aunque esa caída no sobrevive como causa). Si el corte
sube solo porque cae el petróleo, el nombre "comunicación física" no está ganado. Además la regla de D2 no tenía el placebo de
nunca tratados, el que rompió D1.

Qué se sabía al fijar esta regla (regla informada): todas las cifras de `wiki/hallazgos/causal.md` en 7f2e499 (D1, D1b, D2,
placebos, cierre, posición costado 16,2 y punta 7,8 puntos porcentuales) y lo ya publicado del estudio. Nadie calculó volumen de
agua o de petróleo por día con este diseño, ni nada de D3 a D7.

## Preguntas, en orden de prioridad

1. **D3. ¿Entra agua o sale petróleo?** Mismo diseño que D2 sobre el volumen de agua y el de petróleo por día, en la misma
   unidad (puntos del líquido de la base). Decide si D2 conserva el nombre. Prioridad uno.
2. **D4. Dosis.** ¿El efecto crece cuanto más cerca (0 a 0,5 km, 0,5 a 1, 1 a 2) y cuanto más fluido inyecta el hijo?
3. **D5. Forma en el tiempo.** Serie de -6 a 12 meses del corte, del agua y del petróleo: cuándo empieza, si persiste o se cura.
4. **D6. Dónde se sostiene.** Por operador, edad del padre, período y área: todos los cortes publicados, un solo veredicto
   (sin cada operador).
5. **D7. Colorado.** El mismo diseño y las mismas constantes sobre la segunda cuenca, con una compuerta de dato de agua.
6. **D8. Lectura operativa.** Solo si D3 da agua que entra y D4 da gradiente de distancia; sin dinero, sin veredicto.

Un "sin muestra", "sin dato", "no firme" o un negativo con cota es un resultado terminado.

## D3. Agua que entra o petróleo que sale

- Por pozo y mes: A = agua_m3 / días del mes y O = petróleo_m3 / días del mes (primario, por día calendario); A_pd y O_pd por
  día producido (meses con 5 días producidos o más; secundario).
- Base de líquido L: media de (agua + petróleo) por día calendario en los meses -6 a -4, mayor que 1 m3/d. dA = media de A en
  los meses 0 y 1 menos la base de A, sobre L, por 100. Igual dO. Los dos en la misma unidad, y dA + dO es el cambio del
  líquido: sale un control de cuentas.
- Por qué el día calendario decide: un cierre baja los días producidos, así que no puede subir el agua por día calendario. Si
  ese volumen sube a pesar de los días perdidos, llegó agua. Por día producido puede inflarse por el flujo de una reapertura;
  por eso es secundario.
- Placebos sobre dA (rompen con IC que excluye cero y 5 puntos o más): previo (meses -2 y -1), fecha falsa, distancia falsa y
  nunca tratados.
- Veredicto, en este orden: **sin muestra** (menos de 300 tratados o 30 bloques); **no sobrevive a su placebo**; **entra
  agua** (IC bajo de ATT_A sobre cero); **entra agua en los días producidos** (ATT_A incluye cero, IC bajo de ATT_A_pd sobre
  cero y sus placebos previo y de nunca tratados no rompen); **el corte sube porque cae el petróleo** (IC alto de ATT_A y de
  ATT_A_pd bajo 5 puntos e IC alto de ATT_O bajo cero: cota, el agua no sube 5 puntos del líquido base); **no firme**.
- Sin veredicto: el puente dW con la media de los meses 0 y 1 (no el máximo) y el placebo de nunca tratados sobre el dW de D2.

### Qué le pasa a D2 en README y en la entrada, según D3

El veredicto impreso de D2 lo fija 8f52ff1 y no cambia. Cambia lo que se lee en la entrada: la fila y el límite del README
(líneas de "Diseño causal" y "No se afirma causalidad"), la línea de `wiki/index.md`, el resumen y la lectura de
`wiki/hallazgos/causal.md`, y sus claims.

| D3 da | README y entrada dicen |
| --- | --- |
| entra agua | "comunicación física" se conserva y suma la cifra del agua: el volumen de agua del padre sube tanto (IC); el corte sube porque entra agua, no solo porque cae el petróleo. |
~~~

Texto agregado en `pipeline/causal_profundo.py` (primeras 60 de 208 líneas):

~~~
"""Causal profundo: si el corte de agua sube porque entra agua o porque sale petroleo, con que dosis, con que forma en el
tiempo, donde se sostiene y si se repite en Colorado.

Se corre despues de pipeline.build y de pipeline.causal:  uv run python -m pipeline.causal_profundo

REGLA FIJADA ANTES DE CORRER (2026-11-22). Este archivo es el primer commit de la unidad: la regla, las constantes y las
funciones de veredicto. Antes de fijarla no se calculo ninguna cifra de estos disenos: ni volumen de agua o de petroleo por
dia de tratados o controles, ni ATT por distancia, por tamano del hijo, por mes, por operador o por zona, ni nada de Colorado
con este diseno. Si algo resulta ambiguo al calcular, se corrige en un commit nuevo que lo diga, nunca despues de ver una
cifra. El plan completo: docs/plan-causal-profundo.md.

Regla informada en esto: al fijarla se conocian las cifras de pipeline.causal (rama t3/causal-diseno, commit de regla 8f52ff1,
cabeza 7f2e499): D2 ATT_W = 13,8 puntos porcentuales (IC 9,5 a 19,9, 447 tratados), placebo de cierre 3,6, placebos previo,
fecha falsa y distancia falsa sin romper; por posicion costado 16,2 y punta 7,8; D1 ATT(1) = -25,8 con nunca tratados -8,0
(rompe); D1b sin muestra (43). Tambien la brecha descriptiva del corte de agua de descomposicion.md (panel 4) y el gradiente
por distancia del petroleo publicado. La caida del petroleo al mes 1 es conocida: por eso D3 no decide con el petroleo solo,
decide con el agua.

Todo reutiliza pipeline.causal sin tocarlo: universo, golpes, cohortes, tratados, controles aun no tratados, celdas de mes
y grupo de edad (H = H_CORTO salvo D5), agregacion pesada por tratados, bootstrap por bloques de 5 km con la misma semilla
(SEMILLA_CAUSAL) y las mismas repeticiones, y la regla de rotura de un placebo (`causal.rompe`).

D3. Agua que entra o petroleo que sale (prioridad uno; decide si D2 se gana el nombre "comunicacion fisica").
  * Por pozo y mes: A = agua_m3 / dias_mes y O = petroleo_m3 / dias_mes (por dia calendario, primario), y A_pd, O_pd con
    dias_efectivos en el denominador (meses con dias_efectivos de DIAS_MIN_PD o mas; secundario).
  * Base de liquido L = media de (agua_m3 + petroleo_m3) / dias_mes en los meses -6 a -4 (los tres con fila), mayor que
    BASE_MIN_LIQUIDO m3/d. Base de A y de O: media de esos mismos meses.
  * dA = (media de A en VENTANA_D3, con al menos un mes) - base de A, sobre L, x 100: puntos del liquido base. Igual dO.
    Recortados en +-TOPE_D3 (fraccion). La identidad dA + dO = cambio del liquido se publica como control de cuentas.
  * Puente con D2: dW con la media (no el maximo) de W en VENTANA_D3, publicado sin veredicto.
  * Placebos de dA (rompe con UMBRAL_ROTURA_VOLUMEN puntos): previo (ventana -2 y -1), fecha falsa, distancia falsa y nunca
    tratados, definidos como en pipeline.causal.
  * Veredicto (`veredicto_d3`), en este orden:
      - "sin muestra": menos de MIN_TRATADOS tratados con dA y dO, o menos de MIN_BLOQUES bloques.
      - "no sobrevive a su placebo": rompe cualquiera de los cuatro placebos de dA.
      - "entra agua": IC bajo de ATT_A (dia calendario) mayor que cero. Cerrar baja los dias, asi que un cierre no sube el
        agua por dia calendario: una suba es agua que llega.
      - "entra agua en los dias producidos": IC de ATT_A incluye cero, IC bajo de ATT_A_pd mayor que cero y su placebo previo
        y de nunca tratados no rompen.
      - "el corte sube porque cae el petroleo": IC alto de ATT_A menor que UMBRAL_VOLUMEN, IC alto de ATT_A_pd menor que
        UMBRAL_VOLUMEN e IC alto de ATT_O menor que cero (cota: el agua no sube UMBRAL_VOLUMEN puntos del liquido base).
      - "no firme": cualquier otro caso.
  * Que le pasa al texto de D2 (README fila y limite, wiki/index.md, resumen y lectura de causal.md): solo con "entra agua"
    o "entra agua en los dias producidos" se sigue leyendo "comunicacion fisica". Con cualquier otro veredicto el veredicto
    impreso de D2 no cambia (lo fija 8f52ff1) pero cada frase de entrada dice que D3, fijado despues, no le da ese nombre.
  * Sin veredicto: placebo de nunca tratados sobre dW de D2 (la regla de D2 no lo tenia), con UMBRAL_ROTURA_AGUA.

D4. Dosis: distancia y tamano del hijo.
  * Bandas de la distancia del primer golpe: BANDAS_KM. Las dos primeras parten los tratados de D2. La tercera es una
    cohorte nueva: primer golpe a menos de KM_LIMPIO en [1, 2) km, sin golpe a menos de 1 km en [g - VENTANA_PREVIA, g + H],
    mismas condiciones de tratado y los mismos controles. La banda de 3 a 5 km es el placebo de distancia falsa, se reimprime.
  * Resultado que decide: dW de D2. Se publica tambien dA de D3.
  * Veredicto de distancia (`veredicto_gradiente`): "sin muestra" si una banda tiene menos de MIN_TRATADOS_BANDA; "gradiente"
    si las tres estimaciones son monotonas (la mas cercana mayor o igual) y el IC de la diferencia cercana menos lejana
    (mismos sorteos) queda entero sobre cero; "sin gradiente" si ese IC incluye cero; "no firme" en otro caso.
  * Tamano: agua de fractura del hijo de la cohorte (dim_fractura_pozo.agua_m3), en terciles entre los tratados de D2 con el
    dato. Mismo veredicto con el tercil alto menos el bajo, "sin dato" si menos de COBERTURA_MIN de los tratados lo tienen.
    La longitud de rama se publica igual, sin veredicto.

D5. Forma en el tiempo.
~~~

Texto agregado en `tests/test_causal_profundo.py`:

~~~
"""Pruebas de la regla de pipeline.causal_profundo: solo las funciones de veredicto, sin datos."""
from __future__ import annotations

from pipeline import causal_profundo as cp
from pipeline.causal import V_D2_CIERRE, V_D2_SOSTIENE, V_NO_FIRME, V_PLACEBO, V_SIN_MUESTRA

OK = (1000, 100)


def test_d3_orden():
    assert cp.veredicto_d3(299, 100, False, (1, 2), (1, 2), (-2, -1), False) == V_SIN_MUESTRA
    assert cp.veredicto_d3(*OK, True, (1, 2), (1, 2), (-2, -1), False) == V_PLACEBO
    assert cp.veredicto_d3(*OK, False, (0.1, 9), (-1, 1), (-2, -1), False) == cp.V_D3_ENTRA
    assert cp.veredicto_d3(*OK, False, (-1, 9), (0.5, 9), (-2, -1), False) == cp.V_D3_ENTRA_PD
    assert cp.veredicto_d3(*OK, False, (-1, 9), (0.5, 9), (-2, -1), True) == V_NO_FIRME
    assert cp.veredicto_d3(*OK, False, (-3, 4), (-2, 4.9), (-20, -1), False) == cp.V_D3_PETROLEO
    assert cp.veredicto_d3(*OK, False, (-3, 6), (-2, 4), (-20, -1), False) == V_NO_FIRME
    assert cp.veredicto_d3(*OK, False, (-3, 4), (-2, 4), (-20, 0.5), False) == V_NO_FIRME


def test_d2_nombre():
    assert cp.d2_gana_nombre(cp.V_D3_ENTRA) and cp.d2_gana_nombre(cp.V_D3_ENTRA_PD)
    for v in (cp.V_D3_PETROLEO, V_NO_FIRME, V_PLACEBO, V_SIN_MUESTRA):
        assert not cp.d2_gana_nombre(v)


def test_gradiente():
    assert cp.veredicto_gradiente([200, 200, 200], [10, 8, 3], 1.0, 12.0) == cp.V_GRADIENTE
    assert cp.veredicto_gradiente([200, 200, 99], [10, 8, 3], 1.0, 12.0) == V_SIN_MUESTRA
    assert cp.veredicto_gradiente([200, 200, 200], [10, 11, 3], 1.0, 12.0) == V_NO_FIRME
    assert cp.veredicto_gradiente([200, 200, 200], [10, 8, 3], -1.0, 12.0) == cp.V_SIN_GRADIENTE
    assert cp.veredicto_gradiente([200, 200, 200], [10, 8, 3], 1.0, 12.0, cobertura=0.5) == cp.V_SIN_DATO


def test_forma():
    assert cp.veredicto_forma(199, 1, 2, 10) == V_SIN_MUESTRA
    assert cp.veredicto_forma(500, 0.5, 9, 10) == cp.V_PERSISTE
    assert cp.veredicto_forma(500, -2, 4.9, 10) == cp.V_CURA
    assert cp.veredicto_forma(500, -2, 5.1, 10) == V_NO_FIRME


def test_general():
    assert cp.veredicto_general({"A": 1.0, "B": 0.2}) == (cp.V_GENERAL, [])
    assert cp.veredicto_general({"A": 1.0, "B": -0.2}) == (cp.V_DEPENDE, ["B"])


def test_colorado():
    vm = cp.V_D3_ENTRA
    assert cp.veredicto_colorado(0.5, V_D2_SOSTIENE, vm, vm) == cp.V_SIN_DATO_AGUA
    assert cp.veredicto_colorado(0.9, V_SIN_MUESTRA, vm, vm) == V_SIN_MUESTRA
    assert cp.veredicto_colorado(0.9, V_D2_CIERRE, vm, vm) == cp.V_NO_REPITE
    assert cp.veredicto_colorado(0.9, V_NO_FIRME, vm, vm) == cp.V_NO_REPITE
    assert cp.veredicto_colorado(0.9, V_D2_SOSTIENE, vm, vm) == cp.V_REPITE
    assert cp.veredicto_colorado(0.9, V_D2_SOSTIENE, cp.V_D3_PETROLEO, vm) == cp.V_REPITE_PARTE
~~~

## `df3a7d6` · 2026-11-22 03:53 UTC

**Asunto:** Regla de D4: precisiones fijadas antes de calcular (sorteos por bloque, cohorte de 1 a 2 km, terciles del hijo), sin ninguna cifra de D4

**Archivos:** `pipeline/causal_profundo.py`

**Primer commit posterior que toca los mismos archivos:** `313c34f` · 2026-11-22 04:13 UTC · D2 segun D3: la fila y el limite del README y el resumen de causal.md dicen que entra agua en los dias producidos; claims de esas frases

Texto agregado en `pipeline/causal_profundo.py`:

~~~
  * Precisiones fijadas antes de calcular D4 (commit propio, ninguna cifra de D4 vista):
      - Sorteos: los mismos W de D3, con el mismo universo de pozos (asi el control de D2 sigue coincidiendo). Un pozo
        fuera de ese universo toma en cada sorteo el peso de su bloque de 5 km (el de cualquier pozo del universo en ese
        bloque); si su bloque no tiene ningun pozo del universo queda fuera, y se publica cuantos quedan fuera.
      - Distancia del primer golpe de un tratado de D2: km_min del padre en el mes g (el golpe mas cercano de ese mes).
        Banda 0 a 0,5 km: km_min < 0,5; banda 0,5 a 1 km: el resto de los tratados de D2.
      - Cohorte de 1 a 2 km: g = primer mes con un golpe a menos de KM_LIMPIO; el golpe mas cercano de ese mes esta en
        [1, 2) km; edad, base de petroleo valida y ventana previa limpia como en causal._condiciones; ningun golpe a
        menos de 1 km en [g - VENTANA_PREVIA, g + H_CORTO] (g1 del pozo antes de g - VENTANA_PREVIA no puede pasar
        porque g es el primer golpe a 2 km; se exige g1 < 0 o g1 > g + H_CORTO). Celdas y controles con causal.celdas.
      - "Tratados de D2" para el tamano: los tratados de las celdas de D2 con dW. El hijo es hijo_min del padre en g. Tiene
        el dato si agua_m3 de dim_fractura_pozo es mayor que cero. Cortes de terciles con np.quantile en 1/3 y 2/3 sobre
        esos tratados con dato; tercil bajo: <= corte 1/3; alto: > corte 2/3; medio: el resto. La cobertura es la parte de
        los tratados de D2 con dato. La longitud de rama (rama_horizontal_m > 0) se parte igual y publica alto menos bajo
        con su IC, sin veredicto.
      - Diferencias (cercana menos lejana, alto menos bajo): resta sorteo por sorteo de los dos bootstrap con los mismos W;
        IC con los percentiles de causal._ic.
~~~

## `cfd9039` · 2026-11-22 05:23 UTC

**Asunto:** Regla de D5 y D6: precisiones fijadas antes de calcular (serie mes a mes, media tarde sorteo por sorteo, subgrupos con sus controles), sin ninguna cifra de D5 ni D6

**Archivos:** `pipeline/causal_profundo.py`

**Primer commit posterior que toca los mismos archivos:** `e5e01c9` · 2026-11-22 05:29 UTC · D5 y D6: forma en el tiempo y donde se sostiene, con sus marts

Texto agregado en `pipeline/causal_profundo.py`:

~~~
  * Precisiones fijadas antes de calcular D5 y D6 (commit propio, ninguna cifra de D5 ni de D6 vista):
      - Tratados: los de la cohorte de D2 (cohortes). Celdas: causal.celdas con H = H_D5 (controles sin golpe a KM_LIMPIO
        en [g - VENTANA_PREVIA, g + H_D5] y con su primer golpe a KM_TRATADO despues de g + H_D5).
      - Sorteos: los mismos W de D3 y el mismo universo, extendidos con extender_pesos como en D4; se publica cuantos
        pozos quedan fuera.
      - dW(e) = W(g + e) menos la base de W de D2 (media de los meses -6 a -4 con al menos MIN_MESES_W_BASE), un mes solo.
        dA(e) y dO(e): d3_pozos con la ventana (e, e), la base y el tope de D3.
      - Media tarde: la media de las estimaciones de dW de los meses de TRAMO_TARDE, sorteo por sorteo con los mismos W; IC
        con causal._ic. Su n es el menor n de tratados con dW entre esos meses. Media temprana: la media de las
        estimaciones de dW de los meses 0 y 1 de la misma serie (no el puente de D3, que usa otras celdas).
      - Primer mes con IC sobre cero: el menor e >= 0 de E_D5 con IC bajo de dW(e) mayor que cero; ninguno si no hay.
      - Otro golpe: tratados con al menos un golpe a menos de KM_LIMPIO en los meses g + 2 a g + 12 (causal._ventana).
  * Precisiones fijadas antes de calcular D6 (mismo commit que las de D5):
      - Resultado: dW de D2 (causal._valores_agua con k = 0) sobre las celdas de D2, los mismos W de D3.
      - Un subgrupo filtra los tratados de cada celda y deja sus controles (celdas_por_mascara); "sin el operador" saca
        tratados y controles de ese operador (causal._celdas_sin_operador), como el dejar un operador afuera de D1.
      - Operadores y areas con MIN_TRATADOS_OPERADOR o mas tratados en las celdas de D2 (la cuenta de pipeline.causal, con
        o sin dW). Area: dim_pozo.area del padre por pozo_id, "Sin dato" si falta (es un corte mas si llega al minimo).
      - Edad: el grupo de edad de la celda (los cuatro de causal). Periodo: el anio del mes g del tratado (PERIODOS).
      - Veredicto: veredicto_general con el IC bajo de dW sin cada operador con el minimo. Valor del veredicto: el sin
        operador de IC bajo mas chico, con su IC.
~~~

## `8f5c778` · 2026-11-22 08:30 UTC

**Asunto:** D7, Colorado: el mismo diseno de D2 y D3 sobre la segunda cuenca; se repite

**Archivos:** `README.md`, `pipeline/causal.py`, `pipeline/causal_profundo.py`, `pipeline/claims.py`, `pipeline/linaje.py`, `tests/fixtures/deslop_numeros_antes.json`, `tests/test_calidad.py`, `tests/test_causal_profundo.py`, `wiki/hallazgos/causal.md`, `wiki/hallazgos/causal_profundo.md`, `wiki/hallazgos/linaje.md`

**Primer commit posterior que toca los mismos archivos:** `9559f7a` · 2026-11-22 08:31 UTC · D7: la pagina no cae sin meses base, --cuenca solo acepta colorado y la cobertura nombra su denominador (tratados de las celdas de D2)

(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)

## `8a38c29` · 2026-11-23 04:00 UTC

**Asunto:** copy: índice: la tarjeta del eje retirado sale (sus cifras están en 'Ver los números'), y el estado de la prueba prospectiva sale de su página (ya está puntuada: sin muestra)

**Archivos:** `README.md`, `pipeline/claims.py`, `pipeline/report.py`, `pipeline/report_template.html`, `site/index.html`, `tests/test_report.py`

**Primer commit posterior que toca los mismos archivos:** `5626aa2` · 2026-11-23 04:05 UTC · revisión del lote: prueba sin muestra dicho por los mínimos, test del README ata el veredicto, sale el test del bloque de costo y el CSS muerto

(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)

## `f7a3746` · 2026-11-23 13:24 UTC

**Asunto:** Merge pull request #153 from GabrielRuizVarela/data/refresh-2026-11-23

**Archivos:** `README.md`, `data/dq_report.json`, `data/manifest.json`, `docs/caso-interferencia.md`, `docs/verificacion.md`, `site/index.html`, `site/informe.html`, `site/mundo.html`, `site/replay.html`, `tests/fixtures/deslop_numeros_antes.json`, `wiki/area/agua-del-cajon.md`, `wiki/area/aguada-canepa.md`, `wiki/area/aguada-de-castro.md`, `wiki/area/aguada-de-la-arena.md` y 530 más

**Primer commit posterior que toca los mismos archivos:** `e9d01d4` · 2026-11-23 16:48 UTC · copy: README verdict words match the closed list (sin muestra, se replica en 1 de 2 cuencas)

(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)

## `d370e0b` · 2026-11-23 16:50 UTC

**Asunto:** Regla fijada del dia de inicio como dosis: plan, constantes y veredicto, sin ninguna cifra del estudio nuevo

**Archivos:** `docs/plan-dia-inicio.md`, `pipeline/dia_inicio.py`, `tests/test_dia_inicio.py`

**Primer commit posterior que toca los mismos archivos:** `6629dc3` · 2026-11-23 17:33 UTC · Dia de inicio como dosis: implementacion corrida contra la regla fijada en d370e0b

Texto agregado en `docs/plan-dia-inicio.md` (primeras 60 de 185 líneas):

~~~
# Plan: el día del mes en que empieza la fractura como dosis

Fecha: 2026-11-23. Rama `t3/study-a-daily-dose`, que sale de `origin/main` en f7a3746. La regla es el primer commit de la rama:
esta página y `pipeline/dia_inicio.py` (cabecera, constantes y funciones de veredicto sin datos) con sus pruebas sobre números
inventados, sin ninguna cifra calculada del estudio nuevo. Después de ese commit no se cambia: toda desviación va en su propia
sección fechada al final de esta página y en la del hallazgo.

## De dónde sale

El resultado principal del estudio dice que un mes después de la fractura de un hijo, los padres a menos de 1 km rinden 19 a 23
puntos menos de su caudal previo que los controles a 2 a 5 km. Toda la lectura depende de que los controles lejanos sean el
contrafactual de los cercanos, y esa duda aparece de cuatro formas distintas (brecha previa, medianas sin emparejar, fechas
permutadas, nunca tratados). Esta prueba usa una sola cosa que el diseño no necesita lejos: **cuánto del mes del padre expone la
fractura**. Una fractura que empieza el día 3 expone casi todo el mes 0 del padre; una que empieza el día 27 casi nada; y nadie
elige el día pensando en la cifra mensual del padre. Se compara entonces cada padre cercano con padres cercanos, por esa fracción
del mes. Una caída causada por la fractura crece con la fracción; una brecha que ya estaba (selección, pozos distintos) no.

Qué se sabía al fijar esta regla (regla informada): `pipeline/sincronia.py` ya corrió, con regla fijada el 2026-11-15, la pendiente
de la brecha cercano menos control sobre la misma fracción del mes: -2,1 puntos por cada 0,1 (IC por pads -3,3 a -0,8), -0,7
(IC -1,9 a 0,6) el mes anterior y terciles de brecha -14,5, -22,1 y -32,4 puntos. Lo que esta regla agrega, y no estaba:
(a) el estimador usa solo padres cercanos, sin ningún control lejano en la pendiente; (b) el IC es por bloques de 5 km como el
titular; (c) el equilibrio del día de inicio frente a operador, edad del padre y caudal base; (d) tres pruebas negativas
(pozos de control, fechas falsas, días sorteados); (e) el tercio monótono; (f) la lectura del intercepto; (g) un umbral de
magnitud que el de `sincronia` (2 puntos entre el primer y el último día) no tiene; (h) Colorado. La corrida del estudio nuevo
no se vio antes de fijar esta regla: nadie calculó la pendiente solo de cercanos ni ninguna de las pruebas (b) a (h).

## Variable de exposición

- Cada hijo tiene su primera fecha de inicio de fractura en el mes 0 (`stg_fractura.fecha_inicio`, la misma que fija
  `int_frac_hijo.mes_frac`) y su fecha de fin (`fecha_fin`).
- **f0 = (días del mes - día de inicio + 1) / días del mes**, con los días reales del mes (28, 29, 30 o 31). Cuenta el día de
  inicio como expuesto. Un inicio el día 1 da f0 = 1; el último día da 1 / días del mes. Es la misma definición que
  `pipeline.sincronia.fraccion_mes0`, y se reusa esa función.
- Sensibilidad sin veredicto: **fd** = días del mes entre el día de inicio y el menor entre el día de fin y el último día del mes,
  contados los dos extremos, sobre los días del mes (la exposición mientras dura la fractura). Solo con hijos cuya fecha de fin
  es posterior o igual a la de inicio. Se publica su pendiente y su IC; no entra en el veredicto.
- Cada evento (padre, mes 0) hereda la f0 del hijo más cercano, el mismo que fija su banda.

## Muestra

- Eventos de `pipeline.placebo.marco` con la base limpia (meses -6 a -4, la de `sincronia`), con los mismos filtros del titular:
  padre con al menos 6 meses de producción al mes de la fractura, base original (meses -3 a -1) y base limpia mayores que 1 m3/d.
- **Cercanos: menos de 1 km del hijo más cercano.** Esos son la muestra de la prueba. Los controles (2 a 5 km) no entran en la
  pendiente; solo en la prueba negativa de pozos de control y en la lectura del intercepto.
- Resultado de un evento: índice de petróleo del mes 0 (caudal por día sobre la media de su base), acotado a [0, 2].

## Estimador

- Regresión de mínimos cuadrados del índice del mes 0 sobre f0, con efectos fijos de área y de año de fractura (los mismos de
  `sincronia`), solo con eventos cercanos. El coeficiente de f0 es la pendiente, en índice por unidad de f0 (de 0 a 1). Se
  publica en puntos por cada 0,1 de f0 (diez veces la pendiente por unidad, en puntos) y el cambio entre un inicio el último
  día y uno el primer día (cien veces la pendiente por unidad, en puntos).
- IC 95%: bootstrap de percentiles (2,5 y 97,5) de 400 repeticiones (`REPS_BOOT`), remuestreando **bloques de 5 km** completos con
  reemplazo (`pipeline.bloques.clave_bloque` sobre el promedio de lat y lon del pad hijo). Semilla del titular para k = 0:
  SEMILLA_PLACEBO + 100 + posición de 0 en KS_PRE. Una remuestra con menos de 5 eventos cercanos se descarta.
- Una dosis en el tiempo es una pendiente **negativa**: más caída cuanto mayor es f0.

## Chequeos de equilibrio (sobre los eventos cercanos de la muestra)

El supuesto que la prueba necesita es que el día del mes en que empieza la fractura no está relacionado con la tendencia del padre.
~~~

Texto agregado en `pipeline/dia_inicio.py` (primeras 60 de 176 líneas):

~~~
"""El dia del mes en que empieza la fractura como dosis: la caida de los padres cercanos en el mes 0, segun la fraccion del mes
del padre que la fractura expone.

Se corre despues de pipeline.build:  uv run python -m pipeline.dia_inicio

REGLA FIJADA ANTES DE CORRER (2026-11-23, antes de calcular ninguna cifra de este estudio; no se cambia despues de ver
resultados). La regla completa, con sus razones, es docs/plan-dia-inicio.md; este modulo guarda sus constantes y sus funciones de
veredicto, sin tocar ningun dato. Todo lo que falta (cargar datos, estimar, escribir la pagina) se agrega en un commit posterior y no
cambia nada de lo de abajo.

Resumen:
  * Exposicion f0 = (dias del mes - dia de inicio + 1) / dias del mes (pipeline.sincronia.fraccion_mes0), de la primera fecha de
    inicio de fractura del hijo en el mes 0. Sensibilidad sin veredicto: fd, la fraccion mientras dura la fractura.
  * Muestra: padres a menos de 1 km (eventos de pipeline.placebo.marco, base de los meses -6 a -4, mismos filtros del titular).
  * Estimador: pendiente de f0 en una regresion del indice del mes 0 (acotado a [0, 2]) con efectos fijos de area y de ano de
    fractura, solo cercanos; IC 95% por bootstrap de bloques de 5 km, REPS_BOOT repeticiones.
  * Equilibrio: eta cuadrado de f0 contra operador del hijo, Spearman con edad y con caudal base; pendiente ajustada; pendiente sin
    cada operador grande.
  * Negativos: la misma pendiente en controles, con fecha falsa (-12 y -6 meses) y con la f0 sorteada entre hijos del mismo mes.
  * Tercio monotono; intercepto a exposicion cero leido contra la brecha previa (sin veredicto); Colorado con el mismo diseno.
  * Veredicto en orden: sin muestra, opuesta o plana, no equilibrado, no sobrevive a su placebo, no firme, con dosis.

Signo: el indice es el caudal del mes sobre su base; una dosis en el tiempo es una pendiente NEGATIVA (mas caida cuanto mayor es f0).

Que NO prueba:
  * Es un caudal mensual contra un dia: el mes 0 mezcla dias antes y despues del inicio; la dosis esta atenuada y la prueba lee signo y
    orden, no magnitud por dia.
  * No separa un cierre preventivo del operador de un dano del pozo: los dos empiezan con la fractura.
  * "El dia de inicio no se relaciona con la tendencia del padre" no se puede comprobar; el equilibrio y los placebos la hacen creible.
  * Es una huella medida, sin ajuste por comparaciones multiples, no una prueba de causa.
"""
from __future__ import annotations

import math

# ------------------------------------------------------------------ constantes fijadas (docs/plan-dia-inicio.md)

K_PRINCIPAL = 0
CLIP_INDICE = (0.0, 2.0)
KM_BLOQUE = 5.0                 # lado de la celda del IC por bloques
DESPLAZAMIENTOS_FALSOS = (-12, -6)   # los corrimientos hacia adelante no se usan: su base cae en los meses 0 a 2 reales
N_PERM = 200                    # sorteos de f0 entre hijos del mismo mes de fractura
OFFSET_SEMILLA_PERM = 900       # semilla del sorteo: SEMILLA_PLACEBO + 900
OFFSET_SEMILLA_TERCIOS = 800    # semilla del bootstrap de la diferencia de terciles: SEMILLA_PLACEBO + 800
OFFSET_SEMILLA_INTERCEPTO = 810  # semilla del bootstrap del intercepto: SEMILLA_PLACEBO + 810

UMBRAL_DOSIS = -0.05            # limite superior del IC de la pendiente (por unidad de f0): 5 puntos entre el primer y el ultimo dia
RUPTURA_PLACEBO = 0.025         # un placebo rompe si su IC excluye cero y |pendiente| >= esto (la mitad del umbral de dosis)
SESGO_PERM = 0.0125             # el estimador de dias sorteados esta sesgado si |media de las pendientes sorteadas| >= esto
P_PERM = 0.05                   # el p bilateral de dias sorteados debe ser menor que esto

MAX_ETA2 = 0.10                 # equilibrio con el operador del hijo: eta cuadrado de f0 menor que esto
MAX_RHO = 0.10                  # equilibrio con edad y con caudal base: |Spearman| menor que esto
MIN_EVENTOS_OPERADOR = 50       # los operadores con menos eventos cercanos se juntan en "otros"
EDAD_GRUPOS = (12, 24, 48)      # cortes de edad del padre en meses (menos de 12, 12 a 24, 24 a 48, 48 o mas)
PARTE_OPERADOR_GRANDE = 0.10    # un operador es grande si tiene esta parte de los eventos cercanos o mas

MIN_CERCANOS = 1000
MIN_BLOQUES = 30
MIN_TERCIO = 300
~~~

Texto agregado en `tests/test_dia_inicio.py` (primeras 60 de 84 líneas):

~~~
"""Pruebas de las funciones de veredicto de pipeline.dia_inicio, con numeros inventados (la regla se fijo antes de correr)."""
from pipeline import dia_inicio as di


def _r(**kw) -> dict:
    r = {"n_cercanos": 2000, "n_controles": 17000, "bloques": 120, "n_tercios": (650, 700, 650),
         "pend": (-0.20, -0.30, -0.10), "eta2_operador": 0.02, "rho_edad": 0.03, "rho_base": -0.02,
         "control": (0.001, -0.01, 0.01), "falsas": {-12: (800, 0.0, -0.02, 0.02), -6: (900, 0.01, -0.01, 0.03)},
         "perm_media": 0.001, "perm_p": 0.005, "medianas_tercios": (0.9, 0.8, 0.7), "dif_tercios": (-0.2, -0.3, -0.1),
         "ajustada": (-0.15, -0.25, -0.05), "sin_operador": [("A", -0.04), ("B", -0.08)]}
    r.update(kw)
    return r


def test_caso_limpio_es_con_dosis():
    assert di.veredicto(_r()) == ("con dosis", [])


def test_sin_muestra_por_cada_minimo():
    assert di.veredicto(_r(n_cercanos=999))[0] == "sin muestra"
    assert di.veredicto(_r(bloques=29))[0] == "sin muestra"
    assert di.veredicto(_r(n_tercios=(650, 299, 650)))[0] == "sin muestra"
    assert di.veredicto(_r(n_controles=2999))[0] == "sin muestra"
    assert di.veredicto(_r(pend=(float("nan"), float("nan"), float("nan"))))[0] == "sin muestra"


def test_plana_y_opuesta():
    assert di.veredicto(_r(pend=(-0.05, -0.20, 0.10)))[0] == "plana"
    assert di.veredicto(_r(pend=(0.0, -0.01, 0.0)))[0] == "plana"      # el limite superior en cero incluye cero
    assert di.veredicto(_r(pend=(0.10, 0.02, 0.20)))[0] == "opuesta"


def test_no_equilibrado_nombra_lo_que_falla():
    v, m = di.veredicto(_r(eta2_operador=0.10))
    assert v == "no equilibrado" and m == ["operador del hijo"]
    v, m = di.veredicto(_r(rho_edad=-0.10, rho_base=0.11))
    assert v == "no equilibrado" and m == ["edad del padre", "caudal base"]
    assert di.veredicto(_r(rho_edad=0.099))[0] == "con dosis"


def test_placebos_rompen_solo_con_ic_fuera_de_cero_y_tamano():
    assert di.rompe(0.03, 0.01, 0.05) and di.rompe(-0.03, -0.05, -0.01)
    assert not di.rompe(0.02, 0.01, 0.03)              # excluye cero pero es chico (menos de 0,025)
    assert not di.rompe(0.04, -0.01, 0.09)             # grande pero el IC incluye cero
    assert not di.rompe(float("nan"), float("nan"), float("nan"))
    v, m = di.veredicto(_r(control=(0.04, 0.02, 0.06)))
    assert v == "no sobrevive a su placebo" and m == ["pozos de control"]
    v, m = di.veredicto(_r(falsas={-12: (800, -0.04, -0.07, -0.01), -6: (900, 0.0, -0.02, 0.02)}))
    assert v == "no sobrevive a su placebo" and m == ["fecha falsa -12"]
    # una fecha falsa con menos de MIN_FALSA eventos no rompe
    assert di.veredicto(_r(falsas={-12: (299, -0.04, -0.07, -0.01), -6: (900, 0.0, -0.02, 0.02)}))[0] == "con dosis"
    assert di.veredicto(_r(perm_media=-0.0125))[0] == "no sobrevive a su placebo"


def test_no_firme_dice_cual_condicion_falla():
    v, m = di.veredicto(_r(pend=(-0.04, -0.07, -0.03)))
    assert v == "no firme" and m == ["el limite superior no baja del umbral de dosis"]
    assert di.veredicto(_r(perm_p=0.05))[1] == ["p de dias sorteados"]
    assert di.veredicto(_r(medianas_tercios=(0.9, 0.7, 0.8)))[1] == ["tercio no monotono"]
    assert di.veredicto(_r(dif_tercios=(-0.2, -0.1, 0.01)))[1] == ["tercio no monotono"]
~~~

## `6629dc3` · 2026-11-23 17:33 UTC

**Asunto:** Dia de inicio como dosis: implementacion corrida contra la regla fijada en d370e0b

**Archivos:** `pipeline/claims.py`, `pipeline/dia_inicio.py`, `pipeline/linaje.py`, `pipeline/run_all.py`, `pipeline/wiki.py`, `tests/fixtures/deslop_numeros_antes.json`, `tests/test_calidad.py`, `tests/test_deslop_numeros.py`, `tests/test_dia_inicio.py`, `tests/test_run_all.py`, `wiki/hallazgos/dia_inicio.md`, `wiki/hallazgos/linaje.md`, `wiki/index.md`

**Primer commit posterior que toca los mismos archivos:** `30bae37` · 2026-11-23 17:49 UTC · Diagnostico del sorteo: la rotacion entre pads ahora es un ciclo sin puntos fijos (hallazgo del finder)

Texto agregado en `pipeline/claims.py`:

~~~
W_DIA = "wiki/hallazgos/dia_inicio.md"


def _claims_dia_inicio() -> list[Claim]:
    """Cada cifra de la pagina del dia de inicio como dosis contra pipeline.dia_inicio. Las lineas se arman de
    `dia_inicio.especificacion`, la misma que escribe la pagina, asi que lo impreso y lo verificado no se separan. Los marts de
    Colorado viven en el warehouse de Vaca Muerta y se saltan (tabla) si Colorado no corrio. El veredicto impreso va como su posicion
    en el orden de la regla: una pagina vieja cuyo veredicto ya no es el del mart da otra posicion (FAIL)."""
    from pipeline import dia_inicio as di

    cl = []
    for cuenca in ("", "colorado"):
        pref = "Colorado: " if cuenca else ""
        tabla = di.nombre_tabla("_veredicto", cuenca) if cuenca else ""
        sufijo = cuenca or "vm"
        for clave, (lits, cifras) in di.especificacion(cuenca).items():
            if cuenca and clave in di.CLAVES_SOLO_VM:
                continue
            lits = di._sustituir(lits, pref)
            opc = clave.startswith("pend_op") or clave == "pend_fd"
            for k, (sql, factor, dec) in enumerate(cifras):
                tol = 0 if dec == 0 else 0.5 * 10 ** -dec * 1.001
                cl.append(_c(f"dia_{sufijo}_{clave}_{k}@wiki", W_DIA, _fr(k, *lits),
                             (lambda q, f: lambda con: f * con.execute(q).fetchone()[0])(sql, factor), tol,
                             "{:,.0f}" if dec == 0 else "{:." + str(dec) + "f}", opcional=opc, tabla=tabla))
        # tabla del dia de inicio por operador del hijo: la fila i, sin el nombre (que sale de los datos)
        anc = "\n" + ("###" if cuenca else "##") + " Día de inicio por operador del hijo\n\n"
        cab = ("| Operador del hijo | Eventos cercanos | f0 media | Parte con inicio en los tres primeros días |\n"
               "| --- | ---: | ---: | ---: |\n")
        for i in range(10):
            fila = r"(?:\|[^\n]*\n){" + str(i) + r"}\| [^|\n]+ \| "
            tn = di.nombre_tabla("_operador", cuenca)
            for col, factor, dec in (("eventos", 1.0, 0), ("f0_media", 1.0, 3), ("parte_f0_mayor_09", 100.0, 1)):
                pat = re.escape(anc) + re.escape(cab) + fila + ("" if col == "eventos" else r"[\d.]+ \| ") \
                    + ("" if col != "parte_f0_mayor_09" else r"\d+,\d+ \| ") + f"({NG})" + (" %" if col == "parte_f0_mayor_09" else "")
                q = f"select {col} from {tn} order by eventos desc, operador limit 1 offset {i}"
                cl.append(_c(f"dia_{sufijo}_oper{i}_{col}@wiki", W_DIA, pat,
                             (lambda q, f: lambda con: f * con.execute(q).fetchone()[0])(q, factor),
                             0 if dec == 0 else 0.5 * 10 ** -dec * 1.001, "{:,.0f}" if dec == 0 else "{:." + str(dec) + "f}",
                             opcional=True, tabla=tn))
    orden_vm = {v: i + 1 for i, v in enumerate(di.VEREDICTOS_VM)}
    orden_co = {v: i + 1 for i, v in enumerate(di.ESTADOS_COLORADO)}
    cl.append(_c("dia_vm_veredicto@wiki", W_DIA, r"Veredicto contra la regla fijada \(posición (\d) de " + str(len(di.VEREDICTOS_VM)) + " en el orden",
                 lambda con: orden_vm[con.execute("select veredicto from mart_dia_inicio_veredicto").fetchone()[0]], 0, "{:.0f}"))
    cl.append(_c("dia_colorado_veredicto@wiki", W_DIA, r"Veredicto de Colorado \(posición (\d) de " + str(len(di.ESTADOS_COLORADO)) + r"\)",
                 lambda con: orden_co[con.execute("select veredicto from mart_dia_inicio_colorado_veredicto").fetchone()[0]], 0, "{:.0f}",
                 tabla="mart_dia_inicio_colorado_veredicto"))
    return cl


    *_claims_dia_inicio(),
~~~

Texto agregado en `pipeline/dia_inicio.py` (primeras 60 de 736 líneas):

~~~
import calendar
import duckdb
import numpy as np

from pipeline import bloques, placebo, replicacion, sincronia
from pipeline.costo import _clusters, _escribir, _remuestra
from pipeline.cuencas import COLORADO
from pipeline.ingest import DATA
from pipeline.placebo import BASE_LIMPIA, KS_PRE, M0, REPS_BOOT, SEMILLA_PLACEBO, _g

OFFSET_SEMILLA_DIAGNOSTICO = 910  # semilla de la lectura posterior del sorteo (fuera del veredicto)


# ------------------------------------------------------------------ datos
# Desde aqui es la implementacion de la regla (commit posterior al de la regla): no cambia ninguna constante ni funcion de arriba.

SEMILLA_K0 = SEMILLA_PLACEBO + 100 + KS_PRE.index(K_PRINCIPAL)      # la del titular para k = 0
SEMILLA_K_PREVIO = SEMILLA_PLACEBO + 100 + KS_PRE.index(-1)         # la del titular para k = -1 (brecha previa)


def _fechas_vm(con) -> tuple[dict, dict]:
    """Primera fecha de inicio de fractura de cada hijo en su mes 0 (la que fija int_frac_hijo) y la ultima fecha de fin de las
    filas de fractura que empiezan en ese mes (precision de implementacion de la sensibilidad fd; no entra en el veredicto)."""
    q = ("select h.hijo, min(f.fecha_inicio), max(f.fecha_fin) from int_frac_hijo h join stg_fractura f on f.pozo_id = h.hijo "
         "where f.fecha_inicio is not null and date_trunc('month', f.fecha_inicio) = h.mes_frac group by h.hijo")
    filas = con.execute(q).fetchall()
    return {int(r[0]): r[1] for r in filas}, {int(r[0]): r[2] for r in filas}


def fd_de(ini, fin) -> float:
    """Fraccion del mes entre el dia de inicio y el menor entre el dia de fin y el ultimo dia del mes (extremos incluidos);
    nan si no hay fecha de fin o es anterior al inicio."""
    if fin is None or fin < ini:
        return float("nan")
    n = calendar.monthrange(ini.year, ini.month)[1]
    ultimo = fin.day if (fin.year, fin.month) == (ini.year, ini.month) else n
    return (ultimo - ini.day + 1) / n


def cargar(con, colorado: bool = False) -> dict:
    """Datos del placebo mas, por hijo: dia de inicio, f0, fd, operador y bloque de 5 km de su pad.

    `con` de Colorado puede estar abierto solo para leer (replicacion.preparar arma sus entradas como tablas temporales).
    """
    if colorado:
        replicacion.preparar(con)
        D = placebo.cargar(con)
        D["bloque_pad"] = replicacion.bloque_por_pad(con, D)
        ini = {int(r[0]): r[1] for r in con.execute("select pozo_id, fecha_frac from co_hijo where hijo").fetchall()}
        fin: dict = {}
    else:
        D = bloques.cargar(con)
        D["bloque_pad"] = D[bloques._nombre(KM_BLOQUE)]
        ini, fin = _fechas_vm(con)
    oper = {int(r[0]): r[1] for r in con.execute("select pozo_id, operador from int_pozo_ubicacion").fetchall()}
    fechas = [ini[int(h)] for h in D["hijo_id"]]
    D["hijo_f0"] = sincronia.fraccion_mes0(fechas)
    D["hijo_dia"] = np.array([f.day for f in fechas], dtype=np.int64)
    D["hijo_fd"] = np.array([fd_de(f, fin.get(int(h))) for f, h in zip(fechas, D["hijo_id"])], dtype=float)
    D["hijo_oper"] = np.array([oper.get(int(h)) or "sin dato" for h in D["hijo_id"]])
~~~

Texto agregado en `pipeline/linaje.py`:

~~~
         "tomados de un diccionario y no con una llamada por mart. Los marts `mart_dias_perdidos_colorado*`, `mart_golpes_mismo_mes_colorado*`, `mart_golpes_mismo_padre_colorado*`, `mart_dia_inicio_colorado*` y `mart_causal_profundo_d7` sí están: "
~~~

## `30bae37` · 2026-11-23 17:49 UTC

**Asunto:** Diagnostico del sorteo: la rotacion entre pads ahora es un ciclo sin puntos fijos (hallazgo del finder)

**Archivos:** `docs/plan-dia-inicio.md`, `pipeline/dia_inicio.py`, `tests/fixtures/deslop_numeros_antes.json`, `wiki/hallazgos/dia_inicio.md`

**Primer commit posterior que toca los mismos archivos:** `fe46183` · 2026-11-23 18:45 UTC · Plan y pagina: registrar la correccion del sorteo sin pad propio y su alcance (revision del finder de fidelidad)

(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)

## `562d175` · 2026-11-25 04:53 UTC

**Asunto:** Merge pull request #167 from GabrielRuizVarela/deploy/publicar-sitio

**Archivos:** `docs/paper/seccion-analisis.md`, `scripts/publicar_sitio.sh`, `tests/test_publicar_sitio.py`

**Primer commit posterior que toca los mismos archivos:** `d96c255` · 2026-11-26 06:59 UTC · Sitio: no publica los planes de trabajo ni la linea base de Fable

(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)

## `4297f3f` · 2026-11-26 05:42 UTC

**Asunto:** Merge pull request #175 from GabrielRuizVarela/copy/runner-mensual

**Archivos:** `README.md`, `docs/operador-datos-propios.md`, `docs/paper/paper.md`, `docs/paper/vaca-muerta-paper.pdf`, `docs/resumen-operador.md`, `pipeline/report_template.html`, `site/index.html`

**Primer commit posterior que toca los mismos archivos:** `b80eaf8` · 2026-11-26 06:56 UTC · D9: el agua en Wyoming con la regla de f29014a

(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)

## `15e194e` · 2026-11-26 06:00 UTC

**Asunto:** Merge pull request #176 from GabrielRuizVarela/docs/plan-nota-175

**Archivos:** (merge, sin cambios propios)

(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)

## `f29014a` · 2026-11-26 06:29 UTC

**Asunto:** Regla D9: el agua en Wyoming con el diseno de D7, fijada antes de calcular

**Archivos:** `pipeline/causal_profundo.py`

**Primer commit posterior que toca los mismos archivos:** `b80eaf8` · 2026-11-26 06:56 UTC · D9: el agua en Wyoming con la regla de f29014a

Texto agregado en `pipeline/causal_profundo.py`:

~~~

D9. Wyoming (tercera cuenca). Fijada antes de calcular ningun numero de agua de Wyoming: la replicacion del petroleo de
Wyoming ya corrio (regla d4a7355, no se replico) y el corte de agua de Wyoming no se calculo nunca.
  * El mismo diseno de D7, sin cambiar ninguna constante ni ningun umbral: D2 y D3 con sus placebos, la compuerta de
    cobertura de agua (COBERTURA_MIN sobre los meses base de los tratados), la semilla SEMILLA_CAUSAL, las mismas REPS, y
    `veredicto_colorado` como regla de veredicto ("se repite", "se repite en parte", "no se repite", "sin dato de agua",
    "sin muestra"), comparando con el D3 de Vaca Muerta.
  * Dato: el warehouse opcional de Wyoming (data/wyoming/warehouse.duckdb) con las tablas que arma pipeline/wyoming y que
    lee pipeline.replicacion.preparar, las mismas de la replicacion del petroleo de Wyoming.
  * Mes 0 del hijo: el mes de FIRSTCOMP (primera terminacion), como en la replicacion del petroleo de Wyoming. Es la
    diferencia con Colorado y va escrita como limite: un mes 0 corrido hacia adelante mete meses posteriores a la fractura
    en la base y achica D2; "no se repite" no separa "no hay suba" de "el mes 0 esta corrido".
  * Mart: mart_causal_profundo_d9, con las columnas de mart_causal_profundo_d7.
  * Se publica cualquiera sea el veredicto: la seccion de D9 en la pagina de causal_profundo y, en el README, el renglon que
    hoy dice "Se repite en Colorado" suma Wyoming con su veredicto y su cifra. "se repite": la suba del agua aparece en dos
    cuencas fuera de Vaca Muerta. "se repite en parte" o "no se repite": se dice asi, con la reserva del mes 0. "sin dato
    de agua" o "sin muestra": se dice que Wyoming no permite probarla.

~~~

## `d347bfd` · 2026-11-26 06:48 UTC

**Asunto:** Merge pull request #177 from GabrielRuizVarela/t3/siguiente-nivel

**Archivos:** `pipeline/causal_profundo.py`

**Primer commit posterior que toca los mismos archivos:** `5ebed5a` · 2026-11-26 10:59 UTC · P: auditoría frase por frase aplicada (rótulos de las reglas, D9 en los resúmenes y el paper, 114 y 38, Holm en el conteo de pruebas)

(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)

## `b80eaf8` · 2026-11-26 06:56 UTC

**Asunto:** D9: el agua en Wyoming con la regla de f29014a

**Archivos:** `README.md`, `pipeline/causal_profundo.py`, `pipeline/claims.py`, `pipeline/linaje.py`, `tests/test_calidad.py`, `tests/test_causal_profundo.py`, `wiki/hallazgos/causal_profundo.md`, `wiki/hallazgos/linaje.md`

**Primer commit posterior que toca los mismos archivos:** `e5aa13d` · 2026-11-26 07:04 UTC · D9: la foto de cifras de las dos páginas que cambian y la etiqueta D9 del README como definicional

Texto agregado en `README.md`:

~~~
● **¿Se pierde o se atrasa?** *Sostiene.* A los 6 meses la brecha es de menos de 5 puntos: sería petróleo que llega tarde. No está probado que vuelva todo. El agua no se atrasa: el corte de agua del padre sube 13,8 puntos porcentuales y en los meses 6 a 12 sigue 10,9 puntos arriba. Es la única afirmación causal, con supuestos nombrados. Se repite en Colorado (9,0, regla fijada después), Wyoming no permite probarla (D9, regla fijada después: 38 tratados, sin muestra) y en Vaca Muerta depende de YPF: sin sus pozos da 7,1, con un intervalo que incluye cero. Contra un control de la misma edad el diferido de los meses 0 a 6 va de 6,4 a 11,4 millones de barriles (sin duplicar y descontando la brecha previa hasta el total original).
~~~

Texto agregado en `pipeline/causal_profundo.py` (primeras 60 de 114 líneas):

~~~
def _d7(con_vm, con_co, cuenca: str = "colorado") -> None:
    D9 (cuenca="wyoming") es el mismo codigo sobre el warehouse de Wyoming, con otro mart y otra etiqueta; el mes 0 del hijo
    lo fija pipeline.replicacion.preparar (en Wyoming es FIRSTCOMP).

    El warehouse de la cuenca se abre solo lectura (las entradas que arma pipeline.replicacion son tablas
    wy = cuenca == "wyoming"
    etq, nombre_cuenca = ("D9", "Wyoming") if wy else ("D7", "Colorado")
        filas.append((etq, 0, nan, nan, nan, False, v_d7))
        print(f"{etq}: cobertura de agua de los meses base: {cobertura:.4f} ({_num(100 * cobertura)}%); "
        print(f"{etq}: veredicto {v_d7}")
        filas.append((etq, int(d3["n_tratados"]), nan, nan, nan, False, v_d7))
        print(f"{etq}: cobertura de agua de los meses base: {cobertura:.4f} ({_num(100 * cobertura)}%); "
        print(f"{etq}: D2 en {nombre_cuenca}: dW = {d2['r']['est']:+.2f} puntos porcentuales (IC 95%: {d2['r']['ic_bajo']:+.2f} a "
        print(f"{etq}: D3 en {nombre_cuenca}: dA = {d3['res_a']['est']:+.2f} puntos del liquido base (IC 95%: "
        print(f"{etq}: veredicto {v_d7}")
    if wy:
        _escribir(con, "mart_causal_profundo_d9", COLS_D7, filas)
    else:
        _escribir(con, "mart_causal_profundo_d7", COLS_D7, filas)
MES0_D9 = ("En Wyoming el mes 0 del hijo es el de la primera terminación (FIRSTCOMP), no el de la fractura: un mes 0 "
           "corrido hacia adelante mete meses posteriores a la fractura en la base y achica D2, así que este resultado "
           "no separa «no hay suba» de «el mes 0 está corrido».")

TEXTO_D9 = {
    V_REPITE: "El corte de agua de D2 sostiene también en Wyoming, y D3 da allí el mismo veredicto que en Vaca Muerta: "
              "la suba del agua aparece en dos cuencas fuera de Vaca Muerta.",
    V_NO_REPITE: "En Wyoming el corte de agua de D2 no sostiene, así que D3 no se compara: la suba del agua no se repite "
                 "en Wyoming. " + MES0_D9,
    V_REPITE_PARTE: "En Wyoming el corte de agua de D2 sostiene, pero D3 da un veredicto distinto al de Vaca Muerta: la "
                    "suba del agua se repite en parte. " + MES0_D9,
    V_SIN_MUESTRA: "La muestra de Wyoming no llega al mínimo de la regla: las cifras se publican pero no deciden, y "
                   "Wyoming no permite probarla.",
    V_SIN_DATO_AGUA: "El dato de agua de los meses base no llega a la cobertura que pide la regla: en Wyoming no se "
                     "calculan D2 ni D3, y Wyoming no permite probarla.",
}

def _filas_d9(con) -> dict | None:
    """{resultado: (n_tratados, valor, ic_bajo, ic_alto, roto, veredicto)}; None si D9 no se corrio."""
    try:
        filas = con.execute("select resultado, n_tratados, valor, ic_bajo, ic_alto, roto, veredicto "
                            "from mart_causal_profundo_d9").fetchall()
    except duckdb.Error:
        return None
    return {f[0]: f[1:] for f in filas}


def _seccion_d9(con, d9: dict | None) -> list[str]:
    """La seccion de D9 (Wyoming): cobertura, D2 y D3 de la segunda cuenca y el veredicto."""
    from pipeline.causal import _ic_txt, _num
    L = ["", "## D9: Wyoming", ""]
    if d9 is None:
        L.append("D9 no se corrió: Wyoming es opcional y su warehouse puede no estar. No hay cifras de Wyoming en "
                 "esta página.")
        return L
    cob = d9["cobertura_agua"]
    ver = d9["D9"][5]
    L.append("El mismo diseño de D7 (D2 y D3 con las mismas constantes, los mismos sorteos y la regla de veredicto de "
             "Colorado), con una regla fijada antes de calcular ninguna cifra de agua de Wyoming, sobre el warehouse "
             "opcional de Wyoming: los pozos horizontales con coordenadas y la producción mensual. El mes 0 del hijo es "
             "el de la primera terminación (FIRSTCOMP), como en la replicación del petróleo de Wyoming, no el de la "
~~~

Texto agregado en `pipeline/claims.py`:

~~~
    T9 = "mart_causal_profundo_d9"
    def d9_n(con) -> float:  # nan si D9 ya no dice "sin muestra"
        v = con.execute(f"select veredicto from {T9} where resultado = 'D9'").fetchone()[0]
        return con.execute(f"select n_tratados from {T9} where resultado = 'dW'").fetchone()[0] if v == "sin muestra" else float("nan")

    cl.append(_c("entrada_agua_d9_readme_q3", R, r"Wyoming no permite probarla \(D9, regla fijada después: " + N + r" tratados, sin muestra\)", d9_n, 0, "{:.0f}", tabla=T9))
    def frase(clave, lits, fns, tols, fmts, tabla="mart_causal_profundo_d3", fichero=W_CAUP, ancla=""):
        sufijo = "readme" if fichero == R else "wiki"   # ancla: regex que lleva la busqueda a una seccion (D9 repite las frases de D7)
            cl.append(_c(f"caup_{clave}_{k}@{sufijo}", fichero, ancla + _fr(k, *lits), fn, tol, fmt, tabla=tabla))
    # D9: Wyoming (el mart lo escribe solo `--cuenca wyoming`; sin el, SKIP). Frases del veredicto "sin muestra"
    T9 = "mart_causal_profundo_d9"
    A9 = r"## D9: Wyoming.*?"

    def d9(res: str, col: str, factor: float = 1.0) -> Callable:
        return lambda con: factor * con.execute(f"select {col} from {T9} where resultado = '{res}'").fetchone()[0]

    frase("d9_cob", ["- Cobertura del dato de agua: ", "% de los meses base (meses -6 a -4) de los ",
                     " tratados de las celdas de D2 tienen agua y días efectivos"],
          [d9("cobertura_agua", "valor", 100), d9("cobertura_agua", "n_tratados")], [0.5, 0], [n0, n0], tabla=T9, ancla=A9)
    frase("d9_d2", ["- D2, corte de agua: ", " puntos porcentuales (IC 95%: ", " a ", "), con ", " tratados; en Vaca Muerta, "],
          [d9("dW", "valor"), d9("dW", "ic_bajo"), d9("dW", "ic_alto"), d9("dW", "n_tratados")],
          [0.05] * 3 + [0], [d1] * 3 + [n0], tabla=T9, ancla=A9)
    frase("d9_cierre", ["El placebo de cierre da ", " (IC 95%: ", " a ", ")"],
          [d9("placebo_cierre", "valor"), d9("placebo_cierre", "ic_bajo"), d9("placebo_cierre", "ic_alto")],
          [0.05] * 3, [d1] * 3, tabla=T9, ancla=A9)
    frase("d9_d3", ["- D3, en puntos del líquido base: agua por día calendario ", " (IC 95%: ", " a ",
                    "), agua por día producido ", " (IC 95%: ", " a ", "), petróleo por día calendario ", " (IC 95%: ",
                    " a ", "), con ", " tratados."],
          [d9("dA", "valor"), d9("dA", "ic_bajo"), d9("dA", "ic_alto"), d9("dA_pd", "valor"),
           d9("dA_pd", "ic_bajo"), d9("dA_pd", "ic_alto"), d9("dO", "valor"), d9("dO", "ic_bajo"), d9("dO", "ic_alto"),
           d9("dA", "n_tratados")], [0.05] * 9 + [0], [d1] * 9 + [n0], tabla=T9, ancla=A9)
~~~

## `857d434` · 2026-11-26 06:56 UTC

**Asunto:** Reglas de D, E, F, G, H, I y J fijadas antes de calcular

**Archivos:** `pipeline/causal_exposicion.py`, `pipeline/cota_rr.py`, `pipeline/inferencia.py`, `pipeline/stacked.py`, `pipeline/tarjeta.py`, `tests/test_cota_rr.py`, `tests/test_inferencia_regla.py`

**Primer commit posterior que toca los mismos archivos:** `c682a63` · 2026-11-26 07:09 UTC · D12: corte de agua dentro de operador por área

Texto agregado en `pipeline/causal_exposicion.py`:

~~~
"""Exposicion: golpes repetidos (D10), exposicion por rama y anillos de derrame (D11), operador por area (D12).

Se corre despues de pipeline.causal_profundo:  uv run python -m pipeline.causal_exposicion

REGLA FIJADA ANTES DE CALCULAR (2026-11-26, porciones G, H y J de docs/plan-siguiente-nivel.md). Este commit trae solo la
regla, las constantes y los veredictos; no se calculo ninguna cifra de D10, D11 ni D12. Si algo resulta ambiguo al
construirlo, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: se conocian D2 (13,8 con 447 tratados), D4 (la banda de 1 a 2 km sube 7,2), D5 (142 de 341
tratados reciben otro golpe a menos de 2 km en los meses 2 a 12; no se conocia la cuenta a 1 km) y D6 (sin YPF da 7,1).

Todo reutiliza pipeline.causal y pipeline.causal_profundo sin tocarlos: universo, golpes, cohortes, celdas, W, dW, bloques,
sorteos (los W de D3 extendidos con extender_pesos, como D4 y D5), causal.rompe y causal._ic.

D10. Golpes repetidos (porcion G): D5 censurado en el segundo golpe.
  * Serie de D5 (E_D5, H = H_D5, sus celdas y su dW por mes; tambien dO(e)), con una sola diferencia: un tratado con un golpe
    a menos de KM_TRATADO (la distancia que define el primero) en un mes g + s, s >= S_CENSURA, sale de la serie desde
    e = s (sus meses e >= s quedan como faltantes). Los controles ya no tienen golpe a KM_LIMPIO hasta g + H_D5.
    El mes g + 1 no censura: un pad que se fractura entre dos meses es el mismo evento (como en "otro golpe" de D5).
  * Publicado sin veredicto: la misma serie censurada a KM_LIMPIO (2 km, la cuenta de D5) y cuantos tratados quedan en cada e.
  * Veredicto: veredicto_forma de D5 sobre la serie censurada a 1 km (media de dW en TRAMO_TARDE, n = el menor n de
    tratados con dW en esos meses, MIN_TRATADOS_D5, FRACCION_CURA, media temprana de los meses 0 y 1 de la misma serie).
  * Lo que no dice: la censura no es al azar (los padres de zonas de relleno reciben mas hijos); la serie censurada mide la
    primera fractura sola en los padres que no recibieron otra, no en todos.

D11. Exposicion por rama y anillos de derrame (porcion H).
  * Distancia entre ramas: `m_min` de mart_trayectoria_par (la distancia minima entre las dos ramas medidas, en m) para el
    par (hijo, padre). Bandas: las de RAMA en pipeline.trayectorias (menos de 250 m, 250 m a 1 km, 1 km o mas).
  * Submuestra: tratados de D2 con g en ANIOS_RAMA y con al menos un hijo de su mes g a menos de KM_TRATADO cuyo par con el
    padre tiene `m_min`; la distancia del tratado es la menor `m_min` de esos pares. Se publica la cobertura: tratados de D2
    en ANIOS_RAMA y cuantos tienen distancia.
  * D11a, dosis por rama: dW de D2 (k = 0) en cada banda de rama, con las celdas de D2 filtradas a los tratados de la banda
    (celdas_por_mascara, controles iguales). Diferencia "menos de 250 m" menos "250 m o mas" (las dos ultimas bandas
    juntas), sorteo por sorteo. Veredicto (`veredicto_rama`): "sin muestra" si alguna de las dos tiene menos de
    MIN_TRATADOS_BANDA; "gradiente por rama" si el IC bajo de la diferencia es mayor que cero; "sin gradiente por rama" si
    el IC de la diferencia incluye cero, el dW de la banda cercana es positivo y el IC alto de la diferencia es menor que
    FRACCION_RAMA de ese dW; "no firme" en otro caso.
  * D11b, controles limpios por rama: D2 en la submuestra, sacando de cada celda los controles con un par medido de
    `m_min` menor que RAMA_LIMPIA_M con un hijo fracturado en [g - VENTANA_PREVIA, g + H_CORTO] y los controles sin rama
    medida. Se publica junto al D2 de la misma submuestra con todos sus controles, y la diferencia con IC. Sin veredicto.
  * D11c, anillos (Butts, 2021): cohortes por anillo de la distancia de boca del golpe mas cercano del mes g, ANILLOS_KM
    (el de 1 a 2 km es la cohorte de D4, causal_profundo._cohorte_1_2_km); para los anillos de 2 km o mas: primer mes con
    km_min en el anillo, ningun golpe mas cerca que el borde interno en [g - VENTANA_PREVIA, g + H_CORTO], edad, base y
    ventana previa como causal._condiciones. Controles de todos los anillos: los de causal.celdas con H_CORTO y ademas sin
    golpe a menos de KM_ANILLO_LIMPIO (km_min) en [g - VENTANA_PREVIA, g + H_CORTO]. Resultados: dW de D2 e I(1) de D1.
    Tambien D2 (anillo de 0 a 1 km, los tratados de D2) con estos controles limpios a 5 km.
    Veredicto (`veredicto_anillos`) sobre dW: "sin muestra" si el anillo de 2 a 3 km tiene menos de MIN_TRATADOS_BANDA;
    "derrame hasta R km" con R el borde externo del anillo mas lejano con IC bajo de dW mayor que cero, si ese anillo
    empieza en KM_LIMPIO o mas (los controles de D1 y D2, limpios solo a 2 km, pueden estar contaminados); "controles
    limpios" si ningun anillo de 2 km o mas tiene IC bajo mayor que cero; mismo criterio sobre I(1) con IC alto menor que
    cero, publicado sin veredicto.
  * Lo que no dice: `m_min` es la geometria declarada de la rama, no la red de fracturas; la submuestra con rama es sobre
    todo de 2016 a 2023.

D12. Operador por area (porcion J): ¿YPF o composicion?
  * Celdas (g, grupo de edad, operador del padre, area del padre): las celdas de D2 partidas, con los controles de cada una
    restringidos al mismo operador y la misma area (dim_pozo.area por pozo_id; "Sin dato" es un area mas, como en D6). La
    celda entra con MIN_CONTROLES_CELDA controles con dato. dW de D2 (k = 0), mismos sorteos.
  * D12a: todos los tratados. D12b: sin los tratados ni controles de YPF (operador del padre igual a OPERADOR_YPF).
    D12c: solo YPF. Se publica tambien cuantos tratados de D2 conserva cada una.
  * Veredicto (`veredicto_operador_area`) sobre D12a: "sin muestra" con menos de MIN_TRATADOS tratados con dW en celdas con
    control; "sostiene dentro de operador y area" si el IC bajo es mayor que UMBRAL_AGUA_PP; "puede ser composicion" si el
    IC incluye cero; "no firme" en otro caso. Sobre D12b (S5 entre operadores): "se repite fuera de YPF" si tiene
    MIN_TRATADOS_OPERADOR o mas tratados y su IC bajo es mayor que cero; "no se repite fuera de YPF" si su IC incluye cero;
    "sin muestra" con menos tratados; "no firme" en otro caso.

Marts (escritos con `_escribir(con, "mart_causal_exposicion_d10", ...)`, `..._d11` y `..._d12` literales para el linaje) y
una seccion por diseno en wiki/hallazgos/causal_profundo.md o una pagina propia, con su regla citada por el SHA de este commit.
"""
from __future__ import annotations

from pipeline.causal import (H_CORTO, KM_LIMPIO, KM_TRATADO, MIN_CONTROLES_CELDA, MIN_TRATADOS, MIN_TRATADOS_OPERADOR,
                             UMBRAL_AGUA_PP, V_NO_FIRME, V_SIN_MUESTRA, VENTANA_PREVIA)
from pipeline.causal_profundo import E_D5, FRACCION_CURA, H_D5, MIN_TRATADOS_BANDA, MIN_TRATADOS_D5, TRAMO_TARDE

# heredado sin cambio
REGLA_HEREDADA = {"KM_TRATADO": KM_TRATADO, "KM_LIMPIO": KM_LIMPIO, "VENTANA_PREVIA": VENTANA_PREVIA,
                  "H_CORTO": H_CORTO, "MIN_CONTROLES_CELDA": MIN_CONTROLES_CELDA, "MIN_TRATADOS": MIN_TRATADOS,
                  "MIN_TRATADOS_OPERADOR": MIN_TRATADOS_OPERADOR, "UMBRAL_AGUA_PP": UMBRAL_AGUA_PP, "E_D5": E_D5,
                  "H_D5": H_D5, "TRAMO_TARDE": TRAMO_TARDE, "MIN_TRATADOS_D5": MIN_TRATADOS_D5,
                  "FRACCION_CURA": FRACCION_CURA, "MIN_TRATADOS_BANDA": MIN_TRATADOS_BANDA}

# ---- regla fijada (no cambiar despues de ver cifras) ----
# D10
KM_CENSURA = KM_TRATADO               # el segundo golpe a la distancia que define el primero
KM_CENSURA_SECUNDARIA = KM_LIMPIO     # publicado sin veredicto
S_CENSURA = 2                         # el mes g + 1 no censura

# D11
ANIOS_RAMA = (2016, 2023)             # inclusive; las ramas cubren de 76 a 97% de los hijos de esos anios
BANDAS_RAMA_M = ((0.0, 250.0), (250.0, 1000.0), (1000.0, None))   # las de RAMA en pipeline.trayectorias, en m
RAMA_LIMPIA_M = 250.0
FRACCION_RAMA = 0.5
ANILLOS_KM = ((1.0, 2.0), (2.0, 3.0), (3.0, 5.0))
KM_ANILLO_LIMPIO = 5.0

# D12
OPERADOR_YPF = "YPF"                  # se compara con el operador del padre en mayusculas y sin espacios al borde; si el
                                      # dato lo escribe distinto (p. ej. "YPF S.A."), el commit de construccion fija el
                                      # texto exacto y lo dice, sin mirar ninguna cifra de D12

V_D10_PERSISTE = "persiste"           # los de veredicto_forma de D5, sobre la serie censurada
V_RAMA_GRADIENTE = "gradiente por rama"
V_RAMA_SIN_GRADIENTE = "sin gradiente por rama"
V_ANILLOS_LIMPIOS = "controles limpios"
V_ANILLOS_DERRAME = "derrame hasta {r:g} km"
V_D12_SOSTIENE = "sostiene dentro de operador y área"
V_D12_COMPOSICION = "puede ser composición"
V_D12_FUERA_REPITE = "se repite fuera de YPF"
V_D12_FUERA_NO = "no se repite fuera de YPF"


def veredicto_rama(n_cerca: int, n_lejos: int, dif_bajo: float, dif_alto: float, dw_cerca: float) -> str:
    if min(n_cerca, n_lejos) < MIN_TRATADOS_BANDA:
        return V_SIN_MUESTRA
    if dif_bajo > 0:
        return V_RAMA_GRADIENTE
    if dif_bajo <= 0 <= dif_alto and dw_cerca > 0 and dif_alto < FRACCION_RAMA * dw_cerca:
        return V_RAMA_SIN_GRADIENTE
    return V_NO_FIRME


def veredicto_anillos(n_por_anillo: dict[tuple[float, float], int], bajos: dict[tuple[float, float], float]) -> str:
    """bajos: IC bajo de dW por anillo (los de ANILLOS_KM)."""
    if n_por_anillo.get((2.0, 3.0), 0) < MIN_TRATADOS_BANDA:
        return V_SIN_MUESTRA
    lejos = [a for a in ANILLOS_KM if a[0] >= KM_LIMPIO and n_por_anillo.get(a, 0) >= MIN_TRATADOS_BANDA
             and bajos.get(a, float("-inf")) > 0]
    if lejos:
        return V_ANILLOS_DERRAME.format(r=max(a[1] for a in lejos))
    return V_ANILLOS_LIMPIOS


def veredicto_operador_area(n_tratados: int, bajo: float, alto: float) -> str:
    if n_tratados < MIN_TRATADOS:
        return V_SIN_MUESTRA
    if bajo > UMBRAL_AGUA_PP:
        return V_D12_SOSTIENE
    if bajo <= 0 <= alto:
        return V_D12_COMPOSICION
    return V_NO_FIRME


def veredicto_fuera_de_ypf(n_tratados: int, bajo: float, alto: float) -> str:
    if n_tratados < MIN_TRATADOS_OPERADOR:
        return V_SIN_MUESTRA
    if bajo > 0:
        return V_D12_FUERA_REPITE
    if bajo <= 0 <= alto:
        return V_D12_FUERA_NO
    return V_NO_FIRME
~~~

Texto agregado en `pipeline/cota_rr.py`:

~~~
"""Cota de Rambachan y Roth (2023), magnitudes relativas, sobre una serie de eventos (porcion F).

REGLA FIJADA ANTES DE CALCULAR (2026-11-26, porcion F de docs/plan-siguiente-nivel.md). Este commit trae la regla, las
constantes, el conjunto identificado, el intervalo y el veredicto. No se calculo ninguna cifra con esta cota antes de
fijarla. Si algo resulta ambiguo al calcular, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: se conocian las cifras publicadas de D1 (pretendencia de -2,5, -3,6 y -6,3 en los meses -3 a -1,
M* simplificado de 0,62) y de D2 (13,8 con 447 tratados, promedio de los meses 0 y 1 de 9,5 en D3).

Reemplaza, en el texto, al M* simplificado de pipeline.causal (m_estrella, que suma |b(-1)| a los dos lados y compara con
el IC alto). El veredicto de D1 ya fijado no cambia: sigue usando m_estrella y queda como registro.

Marco. Una serie de eventos estima beta(e) contra la base (meses -6 a -4 de g, que vale cero). Sin anticipacion,
beta(e) = tau(e) + delta(e), con delta el sesgo por tendencias no paralelas; en los meses previos tau = 0 y
delta(-k) = beta(-k). Los previos son PREVIOS (e = -3, -2, -1).

Magnitudes relativas, Delta^RM(Mbar). Saltos previos: s(-3) = b(-3) - 0 (contra la base, como en m_estrella),
s(-2) = b(-2) - b(-3), s(-1) = b(-1) - b(-2); m = max |s|. Cada salto posterior, delta(0) - delta(-1), delta(1) - delta(0),
..., vale en valor absoluto a lo sumo Mbar m.

Conjunto identificado (exacto, cerrado): para theta = media de tau(e) sobre un conjunto de meses E (e >= 0; un mes solo es
E = {e}), delta(e) = b(-1) + la suma de e + 1 saltos, asi que
    theta en [l(beta) - b(-1) - c(E) Mbar m, l(beta) - b(-1) + c(E) Mbar m],   c(E) = media de (e + 1) sobre E,
con l(beta) la media de beta(e) sobre E. Para ATT(1): c = 2. Para la media de los meses 0 y 1: c = 1,5.

Inferencia (fijada; no es la prueba condicional e hibrida de Andrews, Roth y Pakes que usa el paquete de Rambachan y Roth):
intervalo de union por bootstrap. Con los sorteos de bloques del diseno (los mismos para beta y para los previos), cada
sorteo r da lo_r y hi_r del conjunto identificado; el intervalo es [percentil 2,5 de lo_r, percentil 97,5 de hi_r]. Cubre el
conjunto identificado, y por eso el parametro, con al menos 95% de probabilidad asintotica (cada extremo falla a lo sumo
2,5%): es conservador. El max de m no es suave cuando dos saltos previos empatan; se declara como limite. No se agrega
ninguna dependencia nueva.

Que se publica, para cada diseno y estimando (D1 ATT(1); D2 tau_W(1) y la media de tau_W(0) y tau_W(1) con las celdas de D2,
H = H_CORTO, dW por mes como en D5 pero con la base y las celdas de D2; E ATT(1) cuando exista su mart):
  * la grilla GRILLA_MBAR con el conjunto identificado y el intervalo de cada Mbar;
  * el Mbar de quiebre: el menor Mbar en [0, MBAR_MAX] con intervalo que contiene cero, por biseccion (el intervalo crece
    con Mbar); 0 si ya lo contiene con Mbar = 0; "mayor que MBAR_MAX" si no lo contiene en MBAR_MAX. Con dos decimales.
  * El estimando de maximo de D2 (dW = max(W(g), W(g+1)) - base) no es lineal en tau y no lleva esta cota; el texto lo dice.

Veredicto (`veredicto_rr`), en este orden:
  * "sin dato": falta algun previo.
  * "resiste Mbar = 1": quiebre de M_MIN o mas (saltos posteriores tan grandes como el mayor previo no alcanzan para cero).
  * "resiste solo con Mbar menor que 1": quiebre mayor que cero y menor que M_MIN.
  * "no resiste ni con Mbar = 0": quiebre cero (el efecto menos la pretendencia del mes -1 no se distingue de cero).

Lo que no dice: supone que los meses previos no tienen efecto (sin anticipacion); con anticipacion, restar b(-1) achica un
efecto del mismo signo que la pretendencia y la cota es conservadora en ese caso, no en el contrario.
"""
from __future__ import annotations

import numpy as np

from pipeline.causal import M_MIN, PERCENTILES_IC

# ---- regla fijada (no cambiar despues de ver cifras) ----
PREVIOS = (-3, -2, -1)
GRILLA_MBAR = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0)
MBAR_MAX = 2.0
TOL_BISECCION = 1e-4

V_RR_SIN_DATO = "sin dato"
V_RR_RESISTE = "resiste Mbar = 1"
V_RR_PARCIAL = "resiste solo con Mbar menor que 1"
V_RR_NO = "no resiste ni con Mbar = 0"


def m_previo(b3: np.ndarray | float, b2: np.ndarray | float, b1: np.ndarray | float) -> np.ndarray:
    """Mayor salto previo en valor absoluto, contra la base y entre meses previos consecutivos."""
    b3, b2, b1 = (np.asarray(x, float) for x in (b3, b2, b1))
    return np.maximum.reduce([np.abs(b3), np.abs(b2 - b3), np.abs(b1 - b2)])


def c_meses(meses: tuple[int, ...]) -> float:
    """c(E) = media de (e + 1) sobre los meses posteriores E."""
    if not meses or min(meses) < 0:
        raise ValueError("los meses del estimando son posteriores (e >= 0)")
    return float(np.mean([e + 1 for e in meses]))


def conjunto(l_beta, b3, b2, b1, mbar: float, meses: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray]:
    """Extremos del conjunto identificado de theta (por sorteo si los argumentos son vectores)."""
    centro = np.asarray(l_beta, float) - np.asarray(b1, float)
    media = c_meses(meses) * mbar * m_previo(b3, b2, b1)
    return centro - media, centro + media


def intervalo(l_beta_r, b3_r, b2_r, b1_r, mbar: float, meses: tuple[int, ...]) -> tuple[float, float]:
    """Intervalo de union: percentil bajo de lo_r y percentil alto de hi_r sobre los sorteos."""
    lo, hi = conjunto(l_beta_r, b3_r, b2_r, b1_r, mbar, meses)
    return float(np.percentile(lo, PERCENTILES_IC[0])), float(np.percentile(hi, PERCENTILES_IC[1]))


def _contiene_cero(iv: tuple[float, float]) -> bool:
    return iv[0] <= 0 <= iv[1]


def quiebre(l_beta_r, b3_r, b2_r, b1_r, meses: tuple[int, ...]) -> float:
    """Menor Mbar en [0, MBAR_MAX] con intervalo que contiene cero; inf si no lo contiene en MBAR_MAX."""
    def iv(mbar: float) -> tuple[float, float]:
        return intervalo(l_beta_r, b3_r, b2_r, b1_r, mbar, meses)
    if _contiene_cero(iv(0.0)):
        return 0.0
    if not _contiene_cero(iv(MBAR_MAX)):
        return float("inf")
    a, b = 0.0, MBAR_MAX
    while b - a > TOL_BISECCION:
        c = (a + b) / 2
        if _contiene_cero(iv(c)):
            b = c
        else:
            a = c
    return b


def veredicto_rr(hay_previos: bool, mbar_quiebre: float) -> str:
    if not hay_previos:
        return V_RR_SIN_DATO
    if mbar_quiebre >= M_MIN:
        return V_RR_RESISTE
    if mbar_quiebre > 0:
        return V_RR_PARCIAL
    return V_RR_NO
~~~

Texto agregado en `pipeline/inferencia.py`:

~~~
"""Inferencia (porcion I): escala de los bloques, permutacion de D2 y Holm sobre la familia confirmatoria.

Se corre al final de los pasos causales:  uv run python -m pipeline.inferencia

REGLA FIJADA ANTES DE CALCULAR (2026-11-26, porcion I de docs/plan-siguiente-nivel.md). Este commit trae la regla, las
constantes, la familia, Holm y los veredictos; no se calculo ninguna cifra con otra escala de bloque, ninguna permutacion y
ningun p. Si algo resulta ambiguo al construirlo, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: se conocian los IC publicados con bloques de 5 km de D1 a D7.

I1. Escala de los bloques.
  * D1 (ATT(1) y sus tres placebos) y D2 (ATT_W y sus placebos previo, fecha falsa y distancia falsa) con bloques de cada
    tamano de TAMANOS_BLOQUE_KM: pipeline.bloques.clave_bloque con ese tamano en lugar de TAM_BLOQUE_KM, los mismos REPS y
    SEMILLA_CAUSAL, el resto de pipeline.causal sin cambio. Se publica el IC y la cantidad de bloques de cada tamano.
  * Veredicto (`veredicto_escala`): "sin muestra a N km" si con N km hay menos de MIN_BLOQUES bloques (ese tamano no
    decide); "no depende de la escala" si para cada cantidad el IC excluye cero en todos los tamanos con muestra o en
    ninguno; "depende de la escala: ..." con las cantidades que cambian.

I2. Permutacion de D2.
  * Observaciones: los pares (pozo, celda) de D2 con dW (tratados y controles de cada celda, k = 0). Estratos: bloque de
    TAM_BLOQUE_KM km del pozo, anio del mes g de la celda y grupo de edad. En cada permutacion, dentro de cada estrato se
    reparten al azar las etiquetas de tratado entre sus observaciones, con la misma cantidad de tratados; cada observacion
    queda en su celda con su dW. ATT_W se recalcula con la regla de D2 (celdas con al menos 1 tratado y
    MIN_CONTROLES_CELDA controles, pesadas por tratados).
  * R_PERM permutaciones, semilla SEMILLA_PERM. p a dos colas = (1 + #{|ATT_perm| >= |ATT_obs|}) / (1 + R_PERM). Se publica
    tambien la parte de las observaciones en estratos con las dos etiquetas.
  * Veredicto: "sobrevive a la permutacion" si p < ALFA; "no sobrevive a la permutacion" si no.

I3. Holm sobre la familia confirmatoria.
  * La familia es FAMILIA_CONFIRMATORIA: el estimando principal de cada diseno con veredicto, fijada aca y contada en el
    codigo (len). Las 17 hipotesis con umbral fijo del libro (wiki/hallazgos/ledger.csv) quedan fuera: comparan un valor
    con un umbral, sin distribucion muestral.
  * p de cada una: aproximacion normal a su IC 95% publicado, ee = (IC alto - IC bajo) / (2 Z_95), p = 2 (1 - Phi(|valor| /
    ee)). Un diseno "sin muestra", sin fila o sin IC entra con p = 1 (la familia no se achica). Para D2 se publica tambien el
    p de I2, que no reemplaza al de la familia.
  * Holm (1979) a ALFA. Se publica p, p ajustado, si rechaza, y k = len(FAMILIA_CONFIRMATORIA).
  * Publicado sin veredicto: de los intervalos de la descomposicion sin ajuste (los 141 de docs/paper/paper.md), cuantos
    siguen excluyendo cero con Holm dentro de su propia familia, con la misma aproximacion normal.

Mart: mart_inferencia_escala, mart_inferencia_permutacion y mart_inferencia_holm (con `_escribir(con, "mart_...", ...)`
literal para el linaje), y una pagina wiki/hallazgos/inferencia.md con la regla citada por el SHA de este commit.
"""
from __future__ import annotations

import math

from pipeline.causal import MIN_BLOQUES, MIN_CONTROLES_CELDA, REPS, SEMILLA_CAUSAL, TAM_BLOQUE_KM

REGLA_HEREDADA = {"MIN_BLOQUES": MIN_BLOQUES, "MIN_CONTROLES_CELDA": MIN_CONTROLES_CELDA, "REPS": REPS,
                  "TAM_BLOQUE_KM": TAM_BLOQUE_KM}

# ---- regla fijada (no cambiar despues de ver cifras) ----
TAMANOS_BLOQUE_KM = (2.0, 5.0, 10.0)
R_PERM = 2000
SEMILLA_PERM = SEMILLA_CAUSAL + 70
ALFA = 0.05
Z_95 = 1.959964

# (id, mart, diseno en ese mart): el estimando principal de cada diseno con veredicto. Los de los marts nuevos los escribe
# su construccion con columnas diseno, veredicto, valor, ic_bajo, ic_alto, n_tratados.
FAMILIA_CONFIRMATORIA = (
    ("D1", "mart_causal_veredicto", "D1"),                       # ATT(1) del petroleo, aun no tratados
    ("D1b", "mart_causal_veredicto", "D1b"),                     # persistencia, meses 7 a 24
    ("D2", "mart_causal_veredicto", "D2"),                       # corte de agua
    ("D3", "mart_causal_profundo_veredicto", "D3"),              # agua que entra
    ("D4_distancia", "mart_causal_profundo_veredicto", "D4_distancia"),
    ("D4_tamano", "mart_causal_profundo_veredicto", "D4_tamano"),
    ("D5", "mart_causal_profundo_veredicto", "D5"),              # media tarde de dW
    ("D6", "mart_causal_profundo_veredicto", "D6"),              # sin el operador de IC bajo mas chico
    ("D7", "mart_causal_profundo_d7", "D2"),                     # Colorado, el D2 de su mart
    ("D9", "mart_causal_profundo_d9", "D2"),                     # Wyoming, el D2 de su mart
    ("E", "mart_apilado", "E"),                                  # ATT(1) apilado
    ("D10", "mart_causal_exposicion_veredicto", "D10"),          # D5 censurado
    ("D11a", "mart_causal_exposicion_veredicto", "D11a"),        # diferencia por rama
    ("D12a", "mart_causal_exposicion_veredicto", "D12a"),        # dentro de operador y area
    ("D12b", "mart_causal_exposicion_veredicto", "D12b"),        # fuera de YPF
)

V_ESCALA_NO = "no depende de la escala"
V_ESCALA_SI = "depende de la escala: {}"
V_ESCALA_SIN = "sin muestra a {:g} km"
V_PERM_SI = "sobrevive a la permutación"
V_PERM_NO = "no sobrevive a la permutación"


def p_normal(valor: float | None, bajo: float | None, alto: float | None) -> float:
    """p a dos colas de la aproximacion normal a un IC 95%; 1 si falta algo o el IC no tiene ancho."""
    if valor is None or bajo is None or alto is None or any(map(math.isnan, (valor, bajo, alto))) or alto <= bajo:
        return 1.0
    z = abs(valor) / ((alto - bajo) / (2 * Z_95))
    return math.erfc(z / math.sqrt(2))


def holm(ps: list[float], alfa: float = ALFA) -> tuple[list[float], list[bool]]:
    """p ajustados de Holm (monotonos, recortados en 1) y si cada hipotesis se rechaza a `alfa`."""
    k = len(ps)
    orden = sorted(range(k), key=lambda i: ps[i])
    ajust = [1.0] * k
    previo = 0.0
    for r, i in enumerate(orden):
        previo = max(previo, min(1.0, (k - r) * ps[i]))
        ajust[i] = previo
    return ajust, [a < alfa for a in ajust]


def veredicto_permutacion(p: float) -> str:
    return V_PERM_SI if p < ALFA else V_PERM_NO


def veredicto_escala(excluye: dict[str, dict[float, bool]], bloques: dict[float, int]) -> str:
    """excluye: cantidad -> {tamano: el IC excluye cero}; bloques: tamano -> cantidad de bloques."""
    sin = [t for t in TAMANOS_BLOQUE_KM if bloques.get(t, 0) < MIN_BLOQUES]
    validos = [t for t in TAMANOS_BLOQUE_KM if t not in sin]
    cambian = sorted(q for q, por in excluye.items() if len({por[t] for t in validos if t in por}) > 1)
    if cambian:
        return V_ESCALA_SI.format(", ".join(cambian))
    if sin:
        return "; ".join([V_ESCALA_NO] + [V_ESCALA_SIN.format(t) for t in sin])
    return V_ESCALA_NO
~~~

Texto agregado en `pipeline/stacked.py`:

~~~
"""Estimador apilado del petroleo (porcion E): una pila por evento con controles limpios emparejados.

Se corre despues de pipeline.causal:  uv run python -m pipeline.stacked

REGLA FIJADA ANTES DE CALCULAR (2026-11-26, porcion E de docs/plan-siguiente-nivel.md). Este commit trae solo la regla, las
constantes y el veredicto; no se calculo ninguna cifra de este diseno (ni ATT, ni placebos, ni cuentas de eventos o de
controles). Si algo resulta ambiguo al construirlo, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: se conocian las cifras de D1 (ATT(1) de -25,8 con 468 tratados; el placebo de nunca tratados con
fecha sorteada da -8,0 con IC de -15,2 a -0,5 y tumba el diseno; M* simplificado de 0,62) y la brecha mediana publicada.

Por que: D1 promedia celdas (g, edad) con controles aun no tratados de toda la cuenca, y su placebo de nunca tratados da -8,0:
los pozos que reciben un hijo a menos de 1 km ya rendian distinto. Aca cada evento tiene su propia pila (Cengiz, Dube,
Lindner y Zipperer, 2019) con controles cercanos, limpios en la ventana y emparejados por el nivel y la pendiente de la base.

Definiciones (todo lo que no se nombra es lo de pipeline.causal: golpe, edad, base, indice, bloques):
  * Evento: un tratado de D1 (cohortes de causal: padre i, mes g del primer golpe a KM_TRATADO, edad de EDAD_MIN o mas,
    ventana previa limpia a KM_LIMPIO, base valida).
  * Candidatos a control del evento: pozos j distintos de i con boca a KM_CONTROL_MIN a KM_CONTROL_MAX km de la boca de i,
    edad en g de EDAD_MIN o mas y en el mismo grupo de edad (CORTES_EDAD), base valida en g, sin golpe a KM_LIMPIO en
    [g - VENTANA_PREVIA, g + H_APILADO], y nunca tratados o con su primer golpe a KM_TRATADO despues de g + H_APILADO.
  * Emparejamiento, dentro del grupo de edad: dos variables de la base,
      - nivel: log de la media de petroleo por dia calendario en los meses BASE (la de causal);
      - pendiente: pendiente de minimos cuadrados del log de petroleo por dia calendario contra el mes, en los meses
        VENTANA_PENDIENTE (relativos a g) con fila y petroleo positivo, con al menos MIN_MESES_PENDIENTE meses; sin eso,
        el pozo no es candidato (y un tratado sin eso no es evento).
    Cada variable se estandariza con el desvio de los eventos. Distancia euclidea sobre las dos estandarizadas. Se toman
    los K_MAX candidatos mas cercanos con distancia de CALIPER o menos, con reemplazo entre eventos. Un evento con menos de
    K_MIN controles queda fuera; se publica cuantos.
  * Resultado: el indice I(e) de causal (recortado en INDICE_TOPE) para e en E_SERIE. Efecto del evento en e: I_i(e) menos
    la media de I(e) de sus controles con dato en e (al menos K_MIN con dato; si no, el evento no entra en e).
  * ATT(e): media simple de los efectos de los eventos que entran en e, por 100 (puntos de indice). Estimando: ATT(1).
  * IC 95%: bootstrap de percentiles por bloques de TAM_BLOQUE_KM km de la boca del padre del evento (causal._pesos_bloques
    sobre los padres de los eventos), REPS sorteos, semilla SEMILLA_APILADO; los mismos sorteos para todo e y para la cota.
  * Balance: diferencia estandarizada de medias de nivel y pendiente entre eventos y controles, antes y despues de emparejar.
  * Cota: pipeline.cota_rr con ATT(1) y los previos e = -3, -2, -1 de esta misma serie, sorteo por sorteo.

Placebos (cada uno con la misma maquinaria: candidatos, emparejamiento, ATT(1)). Rompe si causal.rompe con
UMBRAL_ROTURA_PUNTOS:
  * fecha falsa: g' = g - DESFASE_FECHA_FALSA para cada evento, con las condiciones de evento y de control en g';
  * distancia falsa: pseudo eventos con el primer golpe en [KM_FALSO_MIN, KM_FALSO_MAX) km y ninguno a KM_LIMPIO en
    [g - VENTANA_PREVIA, g + H_APILADO];
  * nunca tratados: los pseudo eventos del placebo de D1 (causal._cohorte_nunca_tratados, la misma fecha sorteada), con sus
    propios controles emparejados. Es la prueba de que el -8,0 de D1 desaparece.
La pretendencia no es un placebo: va a la cota (D1 tolera anticipacion de hasta 3 meses).

Dejar un operador afuera: ATT(1) sin los eventos de cada operador del padre con MIN_TRATADOS_OPERADOR o mas eventos y sin
los controles de ese operador.

Veredicto (`veredicto_apilado`), en este orden:
  * "sin muestra": menos de MIN_TRATADOS eventos con efecto en e = 1, o menos de MIN_BLOQUES bloques.
  * "no sobrevive a su placebo": rompe la fecha falsa, la distancia falsa o los nunca tratados.
  * "sostiene como causal bajo tendencias paralelas condicionales al emparejamiento": IC alto de ATT(1) menor que
    UMBRAL_EFECTO_PUNTOS, la cota de Rambachan y Roth da "resiste Mbar = 1", y el IC alto de cada ATT(1) sin un operador
    es menor que cero.
  * "no firme": cualquier otro caso.

Que se publica en cada caso:
  * "sostiene": ATT(1) pasa a ser el titular del petroleo (README, portada, paper) y la brecha mediana agrupada de
    pipeline/sql/04_interferencia.sql pasa a descripcion.
  * cualquier otro: el titular sigue siendo una huella medida (la brecha mediana, rotulada descriptiva) y este resultado se
    publica como falla o como "no firme", con sus placebos.
  * Siempre: la serie ATT(e), los tres placebos, el balance, los eventos fuera por falta de controles, la cota y el dejar un
    operador afuera. Mart: mart_apilado (escrito con `_escribir(con, "mart_apilado", ...)` literal para el linaje).

Prueba: en datos sinteticos con seleccion (los tratados rinden menos y caen mas rapido antes de g) y un efecto plantado,
el ATT(1) recupera el efecto plantado y los placebos no rompen; con efecto cero, el ATT(1) incluye cero.

Lo que no dice: aun con "sostiene" es causa bajo supuestos nombrados (tendencias paralelas condicionales al emparejamiento,
anticipacion acotada por la cota, sin derrame sobre controles a 2 a 5 km: lo prueba H), no un hecho fisico medido.
"""
from __future__ import annotations

from pipeline.causal import (CORTES_EDAD, DESFASE_FECHA_FALSA, E_SERIE, EDAD_MIN, INDICE_TOPE, KM_FALSO_MAX,
                             KM_FALSO_MIN, KM_LIMPIO, KM_TRATADO, MIN_BLOQUES, MIN_TRATADOS, MIN_TRATADOS_OPERADOR, REPS,
                             SEMILLA_CAUSAL, TAM_BLOQUE_KM, UMBRAL_EFECTO_PUNTOS, UMBRAL_ROTURA_PUNTOS, V_NO_FIRME,
                             V_PLACEBO, V_SIN_MUESTRA, VENTANA_PREVIA)
from pipeline.cota_rr import V_RR_RESISTE

# heredado de pipeline.causal sin cambio
REGLA_HEREDADA = {"KM_TRATADO": KM_TRATADO, "KM_LIMPIO": KM_LIMPIO, "VENTANA_PREVIA": VENTANA_PREVIA,
                  "EDAD_MIN": EDAD_MIN, "CORTES_EDAD": CORTES_EDAD, "INDICE_TOPE": INDICE_TOPE, "E_SERIE": E_SERIE,
                  "TAM_BLOQUE_KM": TAM_BLOQUE_KM, "REPS": REPS, "DESFASE_FECHA_FALSA": DESFASE_FECHA_FALSA,
                  "KM_FALSO": (KM_FALSO_MIN, KM_FALSO_MAX), "MIN_TRATADOS": MIN_TRATADOS, "MIN_BLOQUES": MIN_BLOQUES,
                  "MIN_TRATADOS_OPERADOR": MIN_TRATADOS_OPERADOR, "UMBRAL_ROTURA_PUNTOS": UMBRAL_ROTURA_PUNTOS,
                  "UMBRAL_EFECTO_PUNTOS": UMBRAL_EFECTO_PUNTOS}

# ---- regla fijada (no cambiar despues de ver cifras) ----
SEMILLA_APILADO = SEMILLA_CAUSAL + 60
H_APILADO = 6                          # ventana limpia de los controles, como H_CORTO de D1
KM_CONTROL_MIN, KM_CONTROL_MAX = 2.0, 5.0
VENTANA_PENDIENTE = (-9, -4)           # meses relativos a g, inclusive
MIN_MESES_PENDIENTE = 3
K_MAX = 5
K_MIN = 3
CALIPER = 0.5                          # en desvios de los eventos, distancia euclidea sobre las dos variables
E_PRINCIPAL = 1

V_APILADO_SOSTIENE = "sostiene como causal bajo tendencias paralelas condicionales al emparejamiento"


def veredicto_apilado(n_eventos: int, n_bloques: int, placebos_rotos: bool, alto: float, v_rr: str,
                      altos_sin_operador: list[float]) -> str:
    if n_eventos < MIN_TRATADOS or n_bloques < MIN_BLOQUES:
        return V_SIN_MUESTRA
    if placebos_rotos:
        return V_PLACEBO
    if alto < UMBRAL_EFECTO_PUNTOS and v_rr == V_RR_RESISTE and all(a < 0 for a in altos_sin_operador):
        return V_APILADO_SOSTIENE
    return V_NO_FIRME
~~~

Texto agregado en `pipeline/tarjeta.py`:

~~~
"""Modo local con agua y tarjeta del operador (porcion D).

Se corre desde el modo local:  uv run python -m pipeline.local --dir CARPETA  (escribe tarjeta.json y tarjeta.md junto a su
salida). Este modulo arma la tarjeta y su prueba de privacidad; pipeline.local lee las tablas.

REGLA FIJADA ANTES DE CORRER (2026-11-26, porcion D de docs/plan-siguiente-nivel.md). Este commit trae la regla, la
validacion y los campos permitidos; no se corrio D2 sobre tablas locales. Si algo resulta ambiguo al construirlo, se corrige
en un commit nuevo que lo diga, nunca despues de ver una cifra de la validacion.

Entrada. `mensual.csv` acepta `agua_m3` opcional (m3 del mes, mayor o igual a cero), en la lista de opcionales de
pipeline.local junto a `dias_produccion`. Sin `agua_m3`, el modo local hace lo de hoy y la tarjeta dice "sin dato de agua".
Con `agua_m3`, corre D2 de pipeline.causal sobre las tablas locales: W, base de W, dW = max(W(g), W(g+1)) - base, celdas,
placebos previo, fecha falsa y distancia falsa, bootstrap por bloques, la misma semilla y REPS. El placebo de cierre necesita
dias producidos: sin `dias_produccion` no se corre, el veredicto se calcula sin esa prueba y la tarjeta lo dice ("sin prueba
de cierre"). Las ubicaciones y los meses de fractura salen de `pozos.csv` como hoy.

Validacion, fijada antes de correr: el warehouse publico exportado a `pozos.csv` y `mensual.csv` (con `agua_m3`, y
`dias_produccion` desde `dias_efectivos`) y corrido por el modo local da D2 con VALIDACION_D2_TRATADOS tratados y ATT_W de
VALIDACION_D2_PP (a un decimal), igual con la misma semilla y repeticiones. Si no da igual, el commit de construccion dice
por que y la diferencia tiene que ser TOLERANCIA_VALIDACION_PP o menos en el valor y en los dos extremos del IC; si no,
la porcion no esta lista. La exportacion y la comparacion son una prueba que se corre con el warehouse (lenta, opcional
sin el).

Tarjeta (`tarjeta.json` y `tarjeta.md`, en espanol con voseo en el .md). Solo cifras agrupadas, de CAMPOS_TARJETA:
eventos (tratados con dato), brecha del mes 1 con IC, dW con IC, veredictos, y la version del codigo (SHA corto). Ningun
pozo_id, pad, coordenada, nombre de pozo ni fecha (mes o dia; el anio tampoco). Una cifra que sale de menos de
MIN_POZOS_CIFRA pozos se suprime ("menos de N pozos"). La prueba de privacidad: con tablas sinteticas, ningun pozo_id ni
nombre de la entrada aparece en la tarjeta, ninguna clave fuera de CAMPOS_TARJETA, ningun numero con forma de coordenada de
la entrada y ningun texto con forma de fecha (AAAA-MM, AAAA-MM-DD, DD/MM/AAAA).

Lo que no dice: la tarjeta de un operador no es una replicacion independiente del estudio publico si el operador ya esta en
el dato publico; lo dice la tarjeta.
"""
from __future__ import annotations

# ---- regla fijada (no cambiar despues de ver cifras) ----
VALIDACION_D2_TRATADOS = 447
VALIDACION_D2_PP = 13.8
TOLERANCIA_VALIDACION_PP = 0.1
MIN_POZOS_CIFRA = 10
CAMPOS_TARJETA = ("version", "eventos", "brecha_mes1", "brecha_mes1_ic", "dw_pp", "dw_ic", "veredicto_petroleo",
                  "veredicto_agua", "notas")
SIN_AGUA = "sin dato de agua"
SIN_CIERRE = "sin prueba de cierre"
~~~

## `f72c10c` · 2026-11-26 07:18 UTC

**Asunto:** Reglas E, G a J e I: el docstring ya no trae la llamada literal a _escribir

**Archivos:** `pipeline/causal_exposicion.py`, `pipeline/inferencia.py`, `pipeline/stacked.py`

**Primer commit posterior que toca los mismos archivos:** `761e955` · 2026-11-26 07:29 UTC · Porción E: estimador apilado del petróleo, mart_apilado y página apilado.md

Texto agregado en `pipeline/causal_exposicion.py`:

~~~
Marts mart_causal_exposicion_d10, _d11, _d12 y _veredicto (cada uno con su llamada a _escribir con el nombre literal) y
~~~

Texto agregado en `pipeline/inferencia.py`:

~~~
Mart: mart_inferencia_escala, mart_inferencia_permutacion y mart_inferencia_holm (cada uno con su llamada a
_escribir escrita con el nombre literal, para el linaje), y una pagina wiki/hallazgos/inferencia.md con la regla
citada por el SHA de este commit.
~~~

Texto agregado en `pipeline/stacked.py`:

~~~
    operador afuera. Mart: mart_apilado (su llamada a _escribir lleva el nombre literal, para el linaje).
~~~

## `b33064e` · 2026-11-26 07:42 UTC

**Asunto:** Literatura: rótulos y citas según lo leído; verificación de los 15 puntos de Fable

**Archivos:** `scripts/publicar_sitio.sh`, `tests/fixtures/deslop_numeros_antes.json`, `tests/test_publicar_sitio.py`, `wiki/hallazgos/literatura.md`

**Primer commit posterior que toca los mismos archivos:** `c8fd7db` · 2026-11-26 08:38 UTC · Antecedentes leídos: página para el lector (sin bitácora de proceso); OGJ/Procyk vuelve a rotularse nota

(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)

## `88a9168` · 2026-11-26 08:08 UTC

**Asunto:** Regla I: aclaración antes de calcular

**Archivos:** `pipeline/inferencia.py`

**Primer commit posterior que toca los mismos archivos:** `fe27468` · 2026-11-26 08:20 UTC · Porción I: escala de los bloques, permutación de D2 y Holm sobre la familia confirmatoria

Texto agregado en `pipeline/inferencia.py`:

~~~

ACLARACION (2026-11-26, antes de calcular ninguna cifra de esta porcion). Puntos que la regla dejaba abiertos; se fijan aca y no
se tocan despues de ver un numero.
  * I1, veredicto por diseno: `veredicto_escala` se aplica dos veces, una con las cuatro cantidades de D1 (ATT(1) y sus tres
    placebos) y otra con las cuatro de D2 (ATT_W y sus tres placebos); cada diseno tiene su veredicto. "El IC excluye cero" es
    ic_bajo > 0 o ic_alto < 0. La cantidad de bloques de un tamano es la de los pozos tratados de las celdas primarias, la que
    cuentan D1 y D2 en su propio veredicto (D1 y D2 comparten celdas, asi que el conteo es el mismo). El bootstrap de cada
    tamano usa el mismo universo de pozos y la misma semilla que `pipeline.causal.main` (las seis familias de celdas, para que
    con 5 km salgan los mismos sorteos); solo cambia `D["bloque"]` por `clave_bloque(lat, lon, tamano)`.
  * I2, observaciones: son los pares (pozo, celda) de las celdas que D2 usa de verdad (al menos 1 tratado y MIN_CONTROLES_CELDA
    controles con dW); los pares de una celda que D2 descarta no entran, asi el ATT_W observado es el de D2. El anio de la celda
    es g // 12 (g es el indice absoluto de mes, anio * 12 + mes - 1). Un estrato sin las dos etiquetas no cambia en las
    permutaciones y cuenta en el denominador de la parte de observaciones. La comparacion es |perm| >= |obs| sin tolerancia.
  * I3, lectura de los marts: se busca la fila por la columna `diseno`; el mart de D7 (`mart_causal_profundo_d7`) no tiene esa
    columna sino `resultado`, y su estimando de corte de agua es la fila resultado = 'dW' (no hay fila 'D2'): FILA_ALIAS. Un
    veredicto que empieza con "sin muestra" entra con p = 1 aunque la fila tenga IC (el caso de D1b).
  * I3, publicado sin veredicto: los 141 son las filas de mart_descomposicion_k (95), mart_descomposicion_aditiva (38) y
    mart_descomposicion_distancia (8), una prueba por fila, como las cuenta pipeline.bloques.conteo_pruebas. La cantidad de cada
    fila es su brecha con su IC (brecha, ic_bajo, ic_alto; en la aditiva brecha_total con total_ic_bajo y total_ic_alto). Una sola
    familia de Holm con las filas de las tres tablas. Se informa cuantas excluyen cero sin ajuste y cuantas con Holm.
# mart de D7: la fila de su estimando de corte de agua (ver ACLARACION)
FILA_ALIAS = {("mart_causal_profundo_d7", "D2"): "dW"}

~~~

## `eb1c51b` · 2026-11-26 08:48 UTC

**Asunto:** I: D11c entra en la familia de Holm (k = 16), con una segunda aclaración fechada que dice que las cifras de D11 ya se conocían

**Archivos:** `pipeline/inferencia.py`, `tests/fixtures/deslop_numeros_antes.json`, `tests/test_inferencia_regla.py`, `wiki/hallazgos/inferencia.md`

**Primer commit posterior que toca los mismos archivos:** `f43f08b` · 2026-11-26 08:52 UTC · I: la página de inferencia con todos los marts de esta fase en el warehouse (D10 rechaza con Holm; E, D11 y D12 entran sin muestra)

Texto agregado en `pipeline/inferencia.py`:

~~~

ACLARACION 2 (2026-11-26, revision del PR #192, despues de la primera corrida). La regla de D11 da dos filas con veredicto,
D11a (`veredicto_rama`) y D11c (`veredicto_anillos`, sobre dW); D11b va sin veredicto. Como D4 y D12 entran con sus dos filas,
D11c entra tambien: k pasa de 15 a 16. Ya se conocian las cifras de D11 (pagina de exposicion: D11a y D11c dan "sin muestra",
con menos tratados por banda que MIN_TRATADOS_BANDA) y las de la primera corrida de esta familia; por la regla, las dos filas
de D11 entran con p = 1, asi que sumar D11c solo puede hacer a Holm mas exigente. El valor de la fila D11c es el anillo de 2 a
3 km; su veredicto puede decidirlo tambien el de 3 a 5 km.
    ("D11c", "mart_causal_exposicion_veredicto", "D11c"),        # anillos (ACLARACION 2)
          "Un diseño sin muestra, sin fila o sin IC entra con p = 1: la familia no se achica. D7 y D9 se leen de la fila `dW` de "
          "su mart, que guarda sus resultados en la columna `resultado`. D11c se sumó después de la primera corrida, con las "
          "cifras de D11 ya conocidas: la regla de D11 le da veredicto propio, como a D4 y D12 sus dos filas (segunda "
          "aclaración de la regla, en `pipeline/inferencia.py`).", "",
~~~

Texto agregado en `tests/test_inferencia_regla.py`:

~~~
    assert len(ids) == len(set(ids)) == 16   # 15 en la regla, mas D11c (ACLARACION 2)
~~~

## `a1f1fee` · 2026-11-26 11:11 UTC

**Asunto:** D13: regla fijada antes de calcular (donde se sostiene la suba de Colorado)

**Archivos:** `pipeline/causal_profundo.py`

**Primer commit posterior que toca los mismos archivos:** `f3357c0` · 2026-11-26 11:15 UTC · D13: Colorado por operador (codigo, Holm k=17, claims, pruebas)

Texto agregado en `pipeline/causal_profundo.py`:

~~~
D13. Donde se sostiene la suba de Colorado. Fijada antes de calcular ninguna cifra de D13.
  * Que se sabia al fijarla: de Colorado esta publicado el dW de D7 (9,0 puntos, con 1.247 tratados) y sus resultados de
    petroleo; no hay publicada ninguna cifra de agua de Colorado por operador (se busco en wiki/hallazgos). En Vaca Muerta la
    suba depende de YPF (D6); la pregunta de un revisor externo es si Colorado, con 1.247 tratados, se repite entre operadores.
  * Cortes: los mismos de D6 sobre las celdas de D7 (cel_pri) y los mismos sorteos W que arma _d7, con la maquinaria de _d6
    (celdas_por_mascara para "solo el operador", causal._celdas_sin_operador para "sin el operador"): cada operador con
    MIN_TRATADOS_OPERADOR o mas tratados en las celdas de D7, ambos cortes, todos publicados. No hay cortes de edad, periodo
    ni area: la pregunta de D13 es el operador.
  * Veredicto (`veredicto_general`) sobre dW: "general" si sin cada operador con el minimo el IC bajo sigue sobre cero;
    "depende de un operador", con sus nombres, en otro caso. Valor del veredicto: el "sin el operador" de IC bajo mas chico,
    con su IC, como en D6.
  * "sin muestra" si la compuerta de cobertura de agua de D7 no pasa, si ningun operador llega al minimo o si llega uno solo
    (D6 con un solo operador daria "general" o "depende" sobre un unico corte; con uno solo, "sin el operador" deja a los
    demas sin mas contraste y no alcanza para decir "general", asi que D13 pide al menos dos).
  * Se corre solo si D7 (cuenca Colorado) paso la compuerta, despues de las filas de D7. Mart: mart_causal_profundo_d13,
    con las columnas de COLS_D6 y la fila de veredicto de D6, y una columna `diseno` para la familia de Holm.
  * Holm: D13 entra en FAMILIA_CONFIRMATORIA de pipeline.inferencia con la fila de su veredicto, como D6; la familia pasa de
    16 a 17 disenos. Esto se fija antes de calcular y puede cambiar el p ajustado por Holm de los otros disenos.
  * Se publica cualquiera sea el veredicto: una seccion de D13 en la pagina de causal_profundo con la tabla de cortes, el
    veredicto y el commit de esta regla, y un renglon en el resumen de causal.md: "general": "En Colorado la suba se sostiene
    sin cada uno de sus operadores grandes (D13)"; "depende de un operador": "En Colorado tambien depende de un operador:
    <nombre>"; "sin muestra": "D13 no tiene muestra".

# ---- D13: donde se sostiene la suba de Colorado (regla en el docstring del archivo; todavia sin calculo)

MART_D13 = "mart_causal_profundo_d13"
MIN_OPERADORES_D13 = 2    # con menos de dos operadores con el minimo, D13 da "sin muestra"

~~~

## `19415b3` · 2026-11-26 11:11 UTC

**Asunto:** Regla I4: permutacion dentro de las celdas de D2 y D3 de Holm con dA_pd, antes de calcular

**Archivos:** `pipeline/inferencia.py`

**Primer commit posterior que toca los mismos archivos:** `a8bf328` · 2026-11-26 11:12 UTC · I4 (permutacion dentro de las celdas de D2) y fila dA_pd de D3 en Holm: codigo y tests

Texto agregado en `pipeline/inferencia.py`:

~~~
ACLARACION 3 (2026-11-26, revision externa; antes de calcular ninguna cifra de I4 ni de la fila nueva de D3).
I4. Permutacion dentro de las celdas de D2.
  * Observaciones: las mismas de I2 (pares pozo, celda de las celdas que usa D2).
  * Cada estrato es la celda de D2. Toda celda que D2 usa tiene al menos 1 tratado y MIN_CONTROLES_CELDA controles, asi que
    toda observacion se mezcla.
  * En cada permutacion se reparten al azar las etiquetas de tratado dentro de cada celda, con la cantidad de tratados de
    esa celda. ATT_W se recalcula con la regla de D2, asi que los pesos de las celdas no cambian.
  * R_PERM permutaciones (2000), semilla SEMILLA_PERM + 1. p a dos colas, como en I2.
  * Se publica: p, los percentiles 2,5 y 97,5 y la media de la distribucion nula, y la parte de las observaciones que se
    mezcla (debe ser 100%; si no lo es, se dice por que).
  * Veredicto, como en I2: "sobrevive a la permutacion" si p < ALFA.
  * I4 es lo que los textos citan como la prueba de permutacion. I2 sigue publicada con su debilidad dicha.
  * Se declara sin vueltas: I4 se agrego despues de ver las cifras de I2 (8,0% de observaciones que se mezclan, nula no
    centrada en cero) y antes de calcular ninguna cifra de I4. Lo que no prueba: la intercambiabilidad dentro de la celda es el
    supuesto que D2 ya hace, asi que I4 no prueba las tendencias paralelas.
Holm, fila de D3. La familia lee D3 de `mart_causal_profundo_d3` donde cantidad = 'dA_pd' (valor, ic_bajo, ic_alto,
n_tratados), el estadistico con el que decide su veredicto, en lugar de `mart_causal_profundo_veredicto:D3` (que guarda dA, el
volumen de agua del mes). Se declara sin vueltas: esto cambia despues de ver el p de Holm de D3 con dA (0,1308). La regla propia de
D3 decide con dA_pd desde su commit; la familia pasa a leer el estadistico que usa el veredicto del diseno. Su estado y su
veredicto siguen saliendo de `mart_causal_profundo_veredicto:D3`. Ninguno de los dos cambios toca el veredicto de un diseno.
Mart de I4: mart_inferencia_permutacion, segunda fila (cantidad = CANT_PERM_CELDA).
SEMILLA_PERM_CELDA = SEMILLA_PERM + 1
CANT_PERM_I2 = "ATT_W (pp)"
CANT_PERM_CELDA = "ATT_W (pp), I4 dentro de la celda"
~~~

## `dbc5c49` · 2026-11-26 11:55 UTC

**Asunto:** Ronda 1: textos, claims y PDF con D13, I4, D3 en Holm y la lista factual de Fable

**Archivos:** `README.md`, `docs/caso-interferencia.md`, `docs/paper/paper.md`, `docs/paper/vaca-muerta-paper.pdf`, `docs/proceso/antecedentes-leidos.md`, `pipeline/bloques.py`, `pipeline/claims.py`, `pipeline/report_template.html`, `scripts/publicar_sitio.sh`, `site/index.html`, `tests/fixtures/deslop_numeros_antes.json`, `tests/test_publicar_sitio.py`, `wiki/hallazgos/bloques.md`, `wiki/hallazgos/inferencia.md` y 1 más

**Primer commit posterior que toca los mismos archivos:** `3b1620a` · 2026-11-26 12:06 UTC · I5: permutacion por pad padre (codigo, pagina, claims, tests)

(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)

## `052ee98` · 2026-11-26 12:03 UTC

**Asunto:** I5: regla de la permutacion por pad padre (ACLARACION 4), antes de calcular cifras

**Archivos:** `pipeline/inferencia.py`

**Primer commit posterior que toca los mismos archivos:** `3b1620a` · 2026-11-26 12:06 UTC · I5: permutacion por pad padre (codigo, pagina, claims, tests)

Texto agregado en `pipeline/inferencia.py`:

~~~

ACLARACION 4 (2026-11-26, revision externa; despues de ver las cifras de I4 y antes de calcular ninguna cifra de I5).
I5. Permutacion por pad padre dentro de las celdas de D2.
  * Motivo: I4 reparte los pozos de a uno dentro de la celda y da p = 1/2001, el minimo, con la nula centrada en cero. La
    revision lo objeta: los padres tratados de un mismo pad hijo comparten tratamiento, y la pagina no lo dice. Los pozos de un
    pad reciben juntos la fractura del hijo y comparten shocks, asi que permutar pozos sueltos puede exagerar la precision.
  * Observaciones: los mismos pares (pozo, celda) de I2 y de I4.
  * Cluster: los pozos padres de una celda que comparten `pad_id` en `int_pozo_pad` (componentes conexas de bocas de pozo;
    `pad_id` es 'p' mas el menor pozo_id del componente, pipeline/sql/04_interferencia.sql). Un pozo sin fila en `int_pozo_pad`
    es su propio cluster de tamano 1.
  * Estratos: (celda, tamano del cluster). Los clusters del mismo tamano en la misma celda son intercambiables.
  * En cada permutacion se reparten al azar, entre los clusters de cada estrato, las cantidades de tratados por cluster. Dentro
    de un cluster que recibe k tratados de n pozos, los k tratados se sortean con probabilidad uniforme entre sus n pozos. Asi
    cada celda conserva exactamente su cantidad de tratados y los pesos de las celdas de D2 no cambian. ATT_W se recalcula con
    la regla de D2 (`att_w`).
  * R_PERM permutaciones (2000), semilla SEMILLA_PERM + 2 (SEMILLA_PERM_PAD). p a dos colas, como en I2 y en I4.
  * Se publica: p, los percentiles 2,5 y 97,5 y la media de la distribucion nula; la cantidad de clusters y la parte de las
    observaciones que esta en clusters de mas de un pozo; y la parte que se mezcla (observaciones en estratos con al menos
    dos clusters de distinta cantidad de tratados).
  * Veredicto, como en I2 y en I4 (`veredicto_permutacion`): "sobrevive a la permutacion" si p < ALFA.
  * No entra en la familia de Holm, como I4. Los textos siguen citando I4 como la prueba de permutacion y agregan I5 como su
    version por pad. Si I5 no sobrevive, los textos lo dicen.
  * Se declara sin vueltas: I5 se agrego despues de ver las cifras de I4 (p en su minimo, nula centrada en cero) y la
    observacion de la revision, y antes de calcular ninguna cifra de I5. Lo que no prueba: los pads son clusters de bocas de
    pozo, no de laterales; un pad hijo puede alcanzar varios pads padres, que siguen correlacionados entre clusters; y la
    intercambiabilidad dentro de la celda es el supuesto que D2 ya hace, asi que I5 no prueba las tendencias paralelas.
  * Se corrigen dos frases de la pagina: la linea 3 de la pagina dice que la fila de D3 en Holm se fijo "antes de calcular
    ninguna cifra de ellas", y no es asi (el valor y el IC de dA_pd ya eran cifras publicadas del veredicto de D3, y el
    cambio se fijo despues de ver el p de D3 con dA); y el "que no prueba" de I4 agrega que las etiquetas se permutan pozo por
    pozo y no por pad, y que I5 lo hace por pad.
Mart de I5: mart_inferencia_permutacion, tercera fila (cantidad = CANT_PERM_PAD).
SEMILLA_PERM_PAD = SEMILLA_PERM + 2
CANT_PERM_PAD = "ATT_W (pp), I5 por pad padre"
~~~

## `82d58c0` · 2026-11-26 12:03 UTC

**Asunto:** Regla E2 fijada antes de calcular: pila de E con donantes a 2 a 10 km

**Archivos:** `pipeline/stacked.py`

**Primer commit posterior que toca los mismos archivos:** `2d34af6` · 2026-11-26 12:06 UTC · E2: anillo de donantes parametrizado, mart_apilado_e2, entrada de Holm y pruebas

Texto agregado en `pipeline/stacked.py`:

~~~

E2. REGLA FIJADA ANTES DE CALCULAR (2026-11-26, ronda 2, porcion E2). Este commit trae solo la regla y la constante; no se
calculo ninguna cifra de E2 (ni cuentas de eventos, bloques o controles, ni ATT, ni placebos, ni balance) y no se consulto
la base para ver si hay muestra. Si algo resulta ambiguo al construirlo, se corrige en un commit nuevo que lo diga, nunca
despues de ver una cifra. La regla de E de arriba (commit 857d434) no cambia.
  * Misma pila que E con un solo cambio: los candidatos a control estan a KM_CONTROL_MIN (2) a KM_CONTROL_MAX_E2 = 10 km de la
    boca del padre del evento, en lugar de 2 a 5. Todo lo demas es el de E, tal cual: edad y grupo de edad, ventana limpia,
    nunca tratados o tratados despues, emparejamiento por nivel y pendiente, CALIPER, K_MAX, K_MIN, resultado y ATT(1), el
    bootstrap por bloques con los mismos sorteos (semilla SEMILLA_APILADO: E2 no trae semilla propia), balance, placebos
    (con el anillo de E2 para sus controles), dejar un operador afuera, la cota de Rambachan y Roth y `veredicto_apilado`
    con los umbrales de E. La distancia falsa y los eventos no cambian de anillo: solo cambia el de los controles.
  * Lo que se conocia al fijarla: de E, 81 eventos en 26 bloques con al menos K_MIN controles, veredicto "sin muestra", 576 de
    657 eventos fuera por falta de controles a 2 a 5 km y su tabla de balance; de D1, ATT(1) de -25,8 con 468 tratados y el
    placebo de nunca tratados de -8,0; del paper, la cifra de D1 con controles a 5 a 10 km, -24,6. No se conocia ninguna
    cifra de E2.
  * El costo, dicho en la regla: donantes mas lejos dan mas eventos pero geologia menos comparable. Lo que los hace comparables
    es emparejar por el nivel y la pendiente de la base, y la tabla de balance despues de emparejar es la prueba. Si el balance
    de E2 despues de emparejar es peor que el de E, la pagina lo dice, y el veredicto no se lee sin ese dato.
  * Holm: E2 entra a FAMILIA_CONFIRMATORIA de pipeline/inferencia.py con el ATT(1) de su fila de veredicto, como E. Esto queda
    fijado antes de calcular y puede cambiar el k de la familia y el p ajustado de Holm de otros disenos.
  * Se publica: una seccion "E2" en wiki/hallazgos/apilado.md con las mismas tablas que E y el SHA de esta regla; su propio mart
    mart_apilado_e2 (mismas COLUMNAS, diseno = "E2"), con su llamada a _escribir con el nombre literal, para el linaje. Se
    eligio un mart aparte y no filas de E en mart_apilado para que la salida de E quede identica byte a byte; se verifica
    volcando mart_apilado (select * order by all) antes y despues.
  * Los veredictos de E y de E2 son independientes: que E2 tenga muestra no cambia el de E.
KM_CONTROL_MAX_E2 = 10.0               # E2: el mismo piso, anillo de donantes hasta 10 km (regla E2 del docstring)
~~~

## `5002094` · 2026-11-26 12:04 UTC

**Asunto:** Regla D14 fijada antes de calcular: D2 con el golpe definido por distancia entre ramas (2016-2023)

**Archivos:** `pipeline/causal_exposicion.py`, `pipeline/inferencia.py`

**Primer commit posterior que toca los mismos archivos:** `f1b1e08` · 2026-11-26 12:05 UTC · Aclaracion D14: celdas propias, etiqueta del veredicto y ventanas del padre (antes de calcular)

Texto agregado en `pipeline/causal_exposicion.py`:

~~~
REGLA D14 FIJADA ANTES DE CALCULAR (2026-11-26, ronda 2, S2 del revisor: "la distancia entre ramas como exposicion primaria en
2016-2023"). Este commit trae solo la regla y las constantes; no se calculo ninguna cuenta ni efecto de D14. Lo que se conocia:
D2 (13,8 con 447 tratados), la cobertura de D11a (279 de 312 tratados de D2 de 2016 a 2023 con distancia de rama, y su
"sin muestra"), y las cifras publicadas de D11b en wiki/hallazgos/exposicion.md (seccion D11). Ninguna cuenta de tratados ni
de controles de D14, ningun efecto y ningun p se vieron antes de este commit.

D14. D2 con el golpe definido por la distancia entre ramas.
  * Universo, celdas (g, grupo de edad, y lo demas que usen las celdas de D2), resultado (W, dW con k = 0), bloques de
    bootstrap y sorteos: los de D2, restringidos a g en ANIOS_RAMA (2016 a 2023). Eleccion: el filtro de g se aplica DESPUES de
    construir las celdas de D2 y de sus minimos (MIN_CONTROLES_CELDA), es decir, una celda de D2 de esos anios entra o sale
    igual que en D2; solo se descartan las celdas de otros anios. Asi D14 y la fila de comparacion usan las mismas celdas.
  * Tratado: un padre con golpe de rama en el mes g: un hijo fracturado en g con un par (hijo, padre) en mart_trayectoria_par
    con `m_min` menor que RAMA_TRATADO_M (250 m, la banda mas cercana de RAMA en pipeline.trayectorias). Cuenta sin importar la
    distancia de boca (hasta los 5 km que cubre el mart). Ademas: todas las condiciones de D2 sobre el padre (edad, base valida,
    etc.) y ventana previa limpia en los dos sentidos de D2: ningun par de rama a menos de RAMA_TRATADO_M ni golpe de boca a
    menos de KM_TRATADO con un hijo fracturado en [g - VENTANA_PREVIA, g - 1]. Eleccion: un padre con golpe de rama en g y un
    golpe de boca previo en la ventana queda fuera de los tratados (la ventana previa limpia manda) y no es control; un padre
    con un golpe de rama en g y tambien un golpe de boca en g es tratado (los dos golpes ocurren en el mes de la cohorte).
  * Controles: padres de las mismas celdas sin NINGUNO de estos en [g - VENTANA_PREVIA, g + H_CORTO]: un par medido con `m_min`
    menor que RAMA_CONTROL_M (1000 m, donde empieza la banda lejana); un hijo a distancia de boca menor que KM_LIMPIO cuyo par
    con el padre no tiene `m_min` medido (exposicion desconocida). Los controles de D2 que cumplen esto son los de D14.
  * Estimador: ATT_W de D2 con la regla de celdas de D2 (MIN_CONTROLES_CELDA) y el IC de D2 (bootstrap por bloques, los mismos
    sorteos).
  * Veredicto (`veredicto_d14`): usa la logica de veredicto_d2 de pipeline.causal: "sin muestra" con menos de MIN_TRATADOS (300)
    tratados con dW en celdas con control; "sostiene: la rama como golpe" si el IC bajo de ATT_W es mayor que UMBRAL_AGUA_PP;
    "no firme" en otro caso. Eleccion: los pasos de placebo y de cierre de veredicto_d2 NO se recalculan para D14 (no se
    construyen placebos con la definicion de rama), y el veredicto lo dice en su texto; "sin muestra" aqui significa menos de
    300 tratados de rama, no falta de cobertura de rama.
  * Publicado sin veredicto, al lado: D2 restringido a g en ANIOS_RAMA (golpe de boca a KM_TRATADO), con las mismas celdas,
    los mismos controles de D2 (los suyos, no los de D14) y los mismos sorteos, para ver si la definicion por rama mueve la
    estimacion. Tambien: cuantos tratados de D14 no son tratados de D2 (rama cerca, boca de 1 a 5 km) y cuantos tratados de D2
    de esos anios no son tratados de D14.
  * Holm: D14 entra en FAMILIA_CONFIRMATORIA de pipeline.inferencia con la fila `diseno` = "D14" de su mart. Esto se fija antes
    de calcular y puede cambiar el p ajustado por Holm de los otros disenos (k sube en uno).
  * Lo que no dice: `m_min` es la distancia entre ramas medidas, no la geometria de la fractura; un hijo sin rama medida puede
    estar cerca igual (queda fuera de los controles, pero no de los otros golpes de un padre tratado); la ventana es solo 2016 a
    2023.

Mart mart_causal_d14 (nombre literal en _escribir, con columna `diseno`) y una seccion D14 en wiki/hallazgos/exposicion.md
(su generador en este modulo), con la regla citada por el SHA de este commit.
# D14
RAMA_TRATADO_M = 250.0                # tratado: par con m_min menor que esto (la banda mas cercana de RAMA)
RAMA_CONTROL_M = 1000.0               # control: ningun par medido con m_min menor que esto (empieza la banda lejana)

V_D14_SOSTIENE = "sostiene: la rama como golpe"
def veredicto_d14(n_tratados: int, bajo: float) -> str:
    """Los pasos de veredicto_d2 sin placebos ni cierre (no se recalculan para D14)."""
    if n_tratados < MIN_TRATADOS:
        return V_SIN_MUESTRA
    if bajo > UMBRAL_AGUA_PP:
        return V_D14_SOSTIENE
    return V_NO_FIRME


~~~

Texto agregado en `pipeline/inferencia.py`:

~~~
    ("D14", "mart_causal_d14", "D14"),                           # D2 con el golpe por distancia entre ramas (regla en causal_exposicion)
~~~

## `f1b1e08` · 2026-11-26 12:05 UTC

**Asunto:** Aclaracion D14: celdas propias, etiqueta del veredicto y ventanas del padre (antes de calcular)

**Archivos:** `pipeline/causal_exposicion.py`

**Primer commit posterior que toca los mismos archivos:** `0a71605` · 2026-11-26 12:08 UTC · D14: calculo, mart_causal_d14, seccion de la pagina, claims y tests

Texto agregado en `pipeline/causal_exposicion.py`:

~~~
ACLARACION D14 (2026-11-26, escrita antes de calcular cualquier cifra de D14; aprobada la regla con tres correcciones del lead).
  1. Celdas. D14 arma SUS PROPIAS celdas con la regla de D2: las mismas claves de celda (g, grupo de edad), MIN_CONTROLES_CELDA y
     los mismos minimos, aplicados a los tratados de D14 y a los controles de D14, y se quedan solo las g en ANIOS_RAMA. No
     reutiliza el conjunto de celdas de D2 (las que tienen tratados de D2). Esto es lo que ya queria decir la eleccion 2 de la
     regla; donde decia "las celdas de D2" se lee "la regla de celdas de D2". La fila de comparacion (D2 en 2016-2023) usa las
     celdas de D2 filtradas a esos anios.
  2. Etiqueta del veredicto. D14 reutiliza la identificacion de D2 y no repite los placebos de D2, asi que no dice "sostiene"
     como un diseno propio: V_D14_SOSTIENE = "la suba se ve también con el golpe por rama". Se mantienen "sin muestra" (menos
     de MIN_TRATADOS tratados con dW en celdas con control) y "no firme". La pagina dice en una frase que D14 cambia solo la
     definicion del golpe y que sus placebos son los de D2, no repetidos.
  3. Condiciones del padre. Las de D2 se aplican tal cual (causal._condiciones): edad desde EDAD_MIN, base valida y la ventana
     previa limpia propia de D2, que cuenta golpes a menos de KM_LIMPIO (2 km, no KM_TRATADO) en [g - VENTANA_PREVIA, g - 1].
     Sobre eso se agrega la ventana previa lateral: ningun par (hijo, padre) con m_min menor que RAMA_TRATADO_M con un hijo
     fracturado en [g - VENTANA_PREVIA, g - 1]. Ventanas que quedan aplicando a un tratado de D14: (a) boca a KM_LIMPIO en
     [g - VENTANA_PREVIA, g - 1] (la de D2, que ya incluye lo que decia la regla con KM_TRATADO); (b) rama a menos de
     RAMA_TRATADO_M en [g - VENTANA_PREVIA, g - 1]. Controles: las condiciones de D2 (causal.controles, incluida la ventana a
     KM_LIMPIO en [g - VENTANA_PREVIA, g + H_CORTO] y su primer golpe a KM_TRATADO despues de g + H_CORTO) mas las dos condiciones
     de rama de la regla, que son las de [g - VENTANA_PREVIA, g + H_CORTO] con m_min menor que RAMA_CONTROL_M y con hijo cercano
     sin m_min medido.
V_D14_SOSTIENE = "la suba se ve también con el golpe por rama"
~~~

## `c28f0c9` · 2026-11-26 12:48 UTC

**Asunto:** Pruebas: la familia de Holm tiene 19 diseños, el paper lleva claims de Wyoming y la foto de linaje.md se rehízo

**Archivos:** `tests/fixtures/deslop_numeros_antes.json`, `tests/test_inferencia_regla.py`, `tests/test_wyoming_pagina.py`

**Primer commit posterior que toca los mismos archivos:** `6ff9a55` · 2026-11-26 13:14 UTC · Lista factual de la ronda 2: siete correcciones de texto y tres claims del mes 6 de E2

(Commit citado que no fija una regla: se listan solo su fecha, asunto y archivos.)

## `de19052` · 2026-11-27 03:37 UTC

**Asunto:** Ronda 3: reglas fijadas antes de calcular para la replicacion por operador (S5) y la cota de Rambachan y Roth condicional (S1)

**Archivos:** `docs/plan-siguiente-nivel.md`, `pipeline/cota_rr_condicional.py`, `pipeline/replicacion_operadores.py`

**Primer commit posterior que toca los mismos archivos:** `4fed1c5` · 2026-11-27 03:56 UTC · Replicación por operador (S5): módulo, mart, página, tests sintéticos y paso en run_all, con la regla de de19052 sin cambios

Texto agregado en `pipeline/cota_rr_condicional.py` (primeras 60 de 143 líneas):

~~~
"""Cota de Rambachan y Roth (2023) con la prueba condicional e hibrida de Andrews, Roth y Pakes (ronda 3, S1).

Las reglas de este modulo se citan tal como se escribieron: "este commit" es el commit en que se fijo la regla, y el plan que
nombra (docs/plan-siguiente-nivel.md) no se publica. El SHA, la fecha y el texto de la regla estan en docs/reglas-fijadas.md.

REGLA FIJADA ANTES DE CALCULAR (2026-11-27, ronda 3 de docs/plan-siguiente-nivel.md). Este commit trae la regla, las constantes y
las firmas; no se calculo ninguna cifra con esta prueba antes de fijarla. Si algo resulta ambiguo al calcular, se corrige en un
commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: se conocen las cifras publicadas de pipeline.cota_rr (regla 857d434), que usa el mismo marco con un
intervalo de union por bootstrap: Mbar de quiebre 0,20 en D1 ATT(1), mayor que 2 en D2 tau_W(1) y 1,62 en la media de tau_W(0) y
tau_W(1); en D1, b(-3) = -6,1, b(-2) = -3,6, b(-1) = -10,0.

Que cambia respecto de pipeline.cota_rr. El marco, la restriccion y los estimandos son los mismos: magnitudes relativas,
Delta^RM(Mbar), con los saltos previos s(-3) = delta(-3) (contra la base), s(-2) = delta(-2) - delta(-3), s(-1) = delta(-1) -
delta(-2), y cada salto posterior delta(0) - delta(-1), delta(1) - delta(0) a lo sumo Mbar max|s| en valor absoluto. Cambia la
inferencia: en lugar de la union de percentiles del bootstrap, el conjunto de confianza de Rambachan y Roth (2023, seccion 4), que
invierte la prueba condicional e hibrida de Andrews, Roth y Pakes (2023) para cada valor del parametro. El max de |s| deja de ser
un limite: Delta^RM se escribe como la union de seis poliedros, uno por salto previo que es el mayor y por su signo, y el conjunto
de confianza es la union de los de cada poliedro (como computeConditionalCS_DeltaRM del paquete HonestDiD). No se agrega ninguna
dependencia nueva: numpy y statistics.NormalDist de la biblioteca estandar.

Entradas, por estimando: beta = (b(-3), b(-2), b(-1), b(0), b(1)) con el punto de la muestra completa y Sigma = la covarianza
muestral de los sorteos completos del bootstrap por bloques del diseno (los mismos sorteos para los cinco coeficientes; un sorteo
con algun valor faltante se descarta). Estimandos: D1 ATT(1) (theta = tau(1)); D2 tau_W(1); D2 media de tau_W(0) y tau_W(1)
(theta = (tau(0) + tau(1)) / 2), armados como en pipeline.cota_rr._estimandos_d1 y _estimandos_d2 pero guardando tambien b(0).
E ATT(1) no entra: su veredicto es "sin muestra".

Prueba para un poliedro (j, sg), j en {-3, -2, -1} el salto previo mayor y sg en {+1, -1} su signo, y un valor theta0:
  * A (8 x 5) sobre delta = (delta(-3), delta(-2), delta(-1), delta(0), delta(1)): para cada salto previo i distinto de j,
    s(i) - sg s(j) <= 0 y -s(i) - sg s(j) <= 0 (4 filas); para cada salto posterior p, p - Mbar sg s(j) <= 0 y
    -p - Mbar sg s(j) <= 0 (4 filas). Con d = 0.
  * delta = beta - (0, 0, 0, tau(0), tau(1)) y tau_post = theta0 a + gamma b, con a = (0, 1), b = (1, 0) para ATT(1) y
    a = (1, 1), b = (1, -1) para la media. Momentos: Y = A beta - theta0 A_post a, X = A_post b (A_post son las columnas de
    delta(0) y delta(1)); bajo la nula hay un gamma con E[Y - X gamma] <= 0. Sigma_Y = A Sigma A', sigma = raiz de su diagonal.
  * Estadistico: eta = max sobre los vertices v de {nu >= 0, nu'X = 0, nu'sigma = 1} de v'Y (el dual del programa lineal
    min eta sujeto a Y - X gamma <= eta sigma). Con un solo parametro de estorbo, cada vertice tiene a lo sumo dos componentes
    distintas de cero: las filas i con X_i = 0 (nu = e_i / sigma_i) y los pares (i, k) con X_i X_k < 0 que resuelven
    nu_i X_i + nu_k X_k = 0, nu_i sigma_i + nu_k sigma_k = 1. Se enumeran todos; nu* es el que da el maximo (empate: el primero
    en el orden de las filas).
  * Primera etapa, menos favorable (LF): c_LF = cuantil 1 - KAPPA de max_v v'xi, con xi ~ N(0, Sigma_Y) en N_LF sorteos con la
    semilla SEMILLA_LF (raiz de Sigma_Y por autovalores, los negativos llevados a cero). Si eta > c_LF, se rechaza.
  * Segunda etapa, condicional: s2 = nu*'Sigma_Y nu*, c = Sigma_Y nu* / s2, z = Y - c eta. Para cada vertice v, con
    a_v = v'c y b_v = v'z: si a_v < 1, b_v / (1 - a_v) es una cota inferior; si a_v > 1, es una cota superior (tolerancia
    TOL_VERTICE). V_lo es la mayor de las inferiores y V_up la menor de las superiores, tope c_LF. Con la media en cero (el caso
    menos favorable de la nula), p = (F(V_up) - F(eta)) / (F(V_up) - F(V_lo)), F la normal con desvio raiz de s2. Se rechaza si
    p < (ALFA - KAPPA) / (1 - KAPPA). Si el denominador no es positivo, no se rechaza.

Conjunto de confianza para un Mbar: los theta0 de una grilla de N_THETA puntos que alguno de los seis poliedros no rechaza. La
grilla va del extremo bajo del conjunto identificado de pipeline.cota_rr.conjunto (con el punto) menos THETA_SE desvios al extremo
alto mas THETA_SE desvios, con el desvio de l(beta) - b(-1) en los sorteos. Si un extremo de la grilla queda aceptado, se duplica
la cantidad de desvios que se agrega a cada lado (THETA_SE, 2 THETA_SE, 4 THETA_SE...), con N_THETA puntos cada vez, hasta
MAX_AMPLIAR veces; si sigue aceptado, el extremo se publica como abierto. Se publica [min, max] de los aceptados y
si el conjunto tiene huecos.

Mbar de quiebre: el menor Mbar en [0, MBAR_MAX] cuyo conjunto contiene cero, probando theta0 = 0 directamente (no en la grilla),
por biseccion con TOL_BISECCION; 0 si ya lo contiene con Mbar = 0; "mayor que MBAR_MAX" si no lo contiene en MBAR_MAX. Veredicto:
pipeline.cota_rr.veredicto_rr con ese quiebre, mismas palabras y mismo M_MIN.

Que se publica:
  * mart_cota_rr_condicional: por estimando, la grilla GRILLA_MBAR con el conjunto de confianza condicional, y la fila del quiebre
~~~

Texto agregado en `pipeline/replicacion_operadores.py` (primeras 60 de 105 líneas):

~~~
"""Replicacion por operador dentro de Vaca Muerta: la brecha del mes 1 medida operador por operador (ronda 3, S5).

Las reglas de este modulo se citan tal como se escribieron: "este commit" es el commit en que se fijo la regla, y el plan que
nombra (docs/plan-siguiente-nivel.md) no se publica. El SHA, la fecha y el texto de la regla estan en docs/reglas-fijadas.md.

REGLA FIJADA ANTES DE CALCULAR (2026-11-27, ronda 3 de docs/plan-siguiente-nivel.md). Este commit trae la regla, las constantes y
las firmas; no se calculo ninguna brecha de un operador medida solo con sus eventos antes de fijarla. Si algo resulta ambiguo al
calcular, se corrige en un commit nuevo que lo diga, nunca despues de ver una cifra.
Regla informada en esto: se conocen la brecha del mes 1 de la muestra completa (unos 23 puntos menos), las 7 salidas de
pipeline.robustez_operador (sacando de a un operador, la brecha puntual queda entre -24,1 y -22,2 puntos) y que esos 7 operadores
tienen al menos 50 eventos cercanos. Tambien se conoce el veredicto de la familia de cuencas (se replica en 1 de 2).

Pregunta. pipeline.robustez_operador prueba que ningun operador produce la brecha por si solo (sacar de a uno). Esta prueba es la
otra mitad: si la brecha aparece dentro de cada operador, con sus padres cercanos contra sus padres de control. Es la lectura de
pipeline.familia (cuenca por cuenca, sin efecto comun) aplicada a los operadores de una misma cuenca.

Datos y marco (los de pipeline.robustez_operador, sin cambios):
  * d = placebo.cargar(con); m = placebo.marco(d, d["hijo_mes"], ks=(1,), base=placebo.BASE_ORIGINAL). El operador de cada
    evento es el de su PADRE, como en robustez_operador.cargar_eventos (operador de int_pozo_ubicacion ordenada por pozo_id,
    indexado por m["padre"]).
  * Brecha previa limpia: mp = placebo.marco(d, d["hijo_mes"], ks=(-1,), base=placebo.BASE_LIMPIA), con el operador del padre
    por el mismo camino.
  * Placebo de fechas: mf = placebo.marco(d, d["hijo_mes"] + DESPLAZAMIENTO_PLACEBO, solo_reales=True), como lo arma
    placebo.tabla_fechas para ese desplazamiento, con el operador del padre por el mismo camino.
  * Operadores medidos: robustez_operador.grupos_a_sacar(m, operador), es decir los que tienen al menos MIN_CERCANOS = 50 eventos
    cercanos con indice del mes 1 observado. Es el mismo conjunto fijo de la prueba de sacar de a uno, elegido por conteo y no
    por resultado. Los operadores mas chicos no se leen solos.

Por operador X, con los eventos cuyo padre es de X en las dos bandas (cercanos a menos de 1 km, control a 2 a 5 km):
  * brecha del mes 1 y su IC 95%: placebo.brecha_ic(m["idx"][1][mk], m["banda"][mk], m["clave"][mk], placebo.REPS_BOOT,
    placebo.SEMILLA_PLACEBO), con mk = (operador == X);
  * brecha previa: placebo.brecha_ic(mp["idx"][-1][mkp], mp["banda"][mkp], mp["clave"][mkp], placebo.REPS_BOOT,
    placebo.SEMILLA_PLACEBO)["brecha"];
  * placebo: placebo.brecha_ic(mf["idx"][1][mkf], mf["banda"][mkf], mf["clave"][mkf], placebo.REPS_BOOT, SEMILLA_FECHAS), con
    SEMILLA_FECHAS la que usa placebo.tabla_fechas para el desplazamiento -12 (placebo.SEMILLA_PLACEBO + 201);
  * lectura: (se_replica, valor) = replicacion.lectura(brecha, ic_alto, brecha_previa), es decir que se replica si el IC 95%
    queda entero bajo cero y la brecha previa es menor, en valor absoluto, que la del mes 1. Ademas el placebo tiene que estar
    limpio: su ic_alto es mayor o igual que cero. Un placebo que tambien da una brecha entera bajo cero anula la replicacion de X
    ("no se replica: el placebo de fechas tambien da brecha").
  * No se pudo medir: menos de MIN_CONTROLES = 50 eventos de control con indice del mes 1 observado, o la brecha, su IC, la
    brecha previa o el ic_alto del placebo sin valor (placebo.brecha_ic no da IC con menos de 5 eventos en una banda). Cuenta en
    n con su motivo escrito, como una cuenca que no se pudo medir en pipeline.familia.

Lectura de la familia: "Se replica en k de n operadores: <operador> (<lectura>); ...", con n todos los operadores medidos (los que
no se pudieron medir incluidos) y k los que se replican, en el orden de grupos_a_sacar. No hay promedio, peso ni estimacion
conjunta. Se publica cualquiera sea k, tambien k = 0.

Que se publica:
  * mart_replicacion_operadores: una fila por operador (COLS_REP_OP) y una fila de familia (COLS_FAM_OP: k, n, frase);
  * la pagina wiki/hallazgos/replicacion_operadores.md, con la tabla, la frase y lo que no prueba;
  * en un PR de texto aparte, una frase en la pregunta de validez externa del README y de la portada ("Dentro de Vaca Muerta,
    con la misma regla, ..."), con sus claims.

Validacion fijada antes de leer cifras reales (tests/test_replicacion_operadores.py, con eventos sinteticos):
  * una brecha plantada de BRECHA_PLANTADA puntos en los cercanos de un operador sintetico, con la de los otros en cero, da "se
    replica" en ese y "no se replica" en los otros;
  * un operador cuyo placebo de fechas tambien da brecha queda en "no se replica" aunque su brecha del mes 1 pase;
  * k y n cuentan a los que no se pudieron medir como en pipeline.familia.

Que no prueba: dentro de un operador cambian el area y el ano, asi que la brecha por operador no separa al operador de su area.
~~~

## `55a709a` · 2026-11-27 04:16 UTC

**Asunto:** S1: enmienda de la regla antes de calcular ninguna cifra real: el ancho pasa a ser dato y no puerta

**Archivos:** `docs/plan-siguiente-nivel.md`, `pipeline/cota_rr_condicional.py`, `tests/test_cota_rr_condicional.py`

**Primer commit posterior que toca los mismos archivos:** `2ee52dd` · 2026-11-27 04:20 UTC · S1: corrida con datos reales después de la enmienda 55a709a

Texto agregado en `pipeline/cota_rr_condicional.py` (primeras 60 de 98 líneas):

~~~
Enmienda del 2026-11-27, antes de calcular ninguna cifra real. Va despues de 2ffa2ef, que implemento la regla sin cambios y solo
corrio la validacion sintetica. La cuarta validacion fallo tal como estaba escrita: en las primeras 20 simulaciones el conjunto
de ATT(1) contiene el punto en 20 de 20, pero el mas ancho mide 2,14 veces el intervalo normal al 95% (el promedio, 1,79) y el
tope era 2. Ese tope no salia de la literatura ni de una cuenta: se puso como guarda contra una implementacion rota, y el ancho
mide eficiencia, no correccion. Las tres validaciones de correccion pasan. diagnostico_ancho() (sin warehouse, los mismos datos
sinteticos) muestra de donde sale el ancho. Los dos poliedros que contienen a la delta verdadera rechazan theta verdadero en
4,3% y 2,8% de 1000 simulaciones y miden como maximo 1,70 y 1,97 veces. El 2,14 viene de un poliedro que no la contiene, y la
union tiene que incluirlo porque con datos reales no se sabe cual vale. Con Mbar = 0 la union contiene a theta en las 1000
simulaciones. Un conjunto mas ancho incluye antes el cero: solo puede bajar el Mbar de quiebre, nunca subirlo. Lo que cambia:
  * el ancho deja de ser puerta. Se sigue calculando con los mismos 20 casos, y la pagina publica el mas ancho, el promedio, el
    tope de 2 que no se cumplio, esta enmienda y el diagnostico;
  * que el conjunto contenga el punto en las 20 sigue siendo puerta;
  * no cambia ningun otro numero. El tope no se reemplaza por otro, y las constantes, la dualidad, la cobertura y la potencia
    quedan iguales.

COMMIT_ENMIENDA = ""        # el commit de la enmienda del ancho; lo fija el commit que corre la prueba con datos reales
TOPE_ANCHO = 2.0            # el tope de la regla original; desde la enmienda es dato, no puerta
def conjunto_confianza(beta, Sigma, a, b, mbar: float, centro_id: tuple[float, float], desvio: float,
                       pruebas: list[_Prueba] | None = None) -> dict:
    """Union sobre los seis poliedros (o sobre `pruebas`, si se pasan): bajo, alto, abierto y con_huecos."""
    pruebas = _pruebas(Sigma, a, b, mbar) if pruebas is None else pruebas
    # enmienda del ancho: la puerta es solo que el conjunto contenga el punto; el ancho contra TOPE_ANCHO queda como dato
    return {"ok": contiene == N_ANCHO, "contiene": contiene, "de": N_ANCHO, "razon_max": razon,
            "razon_media": float(np.mean(anchos) / ancho_normal), "tope": TOPE_ANCHO, "cumple_tope": razon <= TOPE_ANCHO}


def diagnostico_ancho() -> dict:
    """Dato de la enmienda, no puerta. Con los datos sinteticos del ancho (ATT(1), Mbar = 0, theta = -3): para cada poliedro,
    si contiene a la delta verdadera (eta por vertices <= 0 sin ruido), su rechazo de theta verdadero en las N_MC simulaciones
    y su ancho en los N_ANCHO casos del ancho, contra el intervalo normal; y la cobertura y el ancho de la union."""
    a, b, _m = _NOMBRE_SINT["ATT(1)"]
    theta = -3.0
    betas = _betas_sinteticos(0.0, theta)
    d = np.array(DELTA_PREVIA)
    media = np.concatenate([d, [d[-1], d[-1]]]) + np.array([0, 0, 0, theta, theta])
    desvio = float(np.sqrt(SIGMA_SINT[4, 4] + SIGMA_SINT[2, 2] - 2 * SIGMA_SINT[2, 4]))
    ancho_normal = 2 * NormalDist().inv_cdf(0.975) * desvio
    pruebas = _pruebas(SIGMA_SINT, a, b, 0.0)

    def _anchos(ps):
        out = []
        for beta in betas[:N_ANCHO]:
            punto = float(beta[4] - beta[2])
            cc = conjunto_confianza(beta, SIGMA_SINT, a, b, 0.0, (punto, punto), desvio, pruebas=ps)
            out.append(0.0 if cc["bajo"] is None else (cc["alto"] - cc["bajo"]) / ancho_normal)
        return out

    filas = []
    for (j, sg), P in zip(POLIEDROS, pruebas):
        w = _anchos([P])
        filas.append({"j": j, "sg": sg,
                      "contiene_delta": bool(eta_vertices(P.momentos(media, theta)[0], P.X, P.sigma) <= 1e-9),
                      "rechazo": float(P.rechaza_Y(P.momentos(betas, theta)).mean()),
                      "ancho_medio": float(np.mean(w)), "ancho_max": float(max(w))})
    u = _anchos(pruebas)
    return {"poliedros": filas, "union_cobertura": float(_aceptado(pruebas, betas, theta).mean()), "n": len(betas),
            "union_ancho_medio": float(np.mean(u)), "union_ancho_max": float(max(u))}
    """Las cuatro validaciones de la regla; main publica cifras reales solo si pasan todas (la del ancho, desde la enmienda,
    solo por contener el punto). Trae ademas diagnostico_ancho(), que no es puerta."""
         "ancho": validar_ancho(), "diagnostico": diagnostico_ancho()}
~~~

Texto agregado en `tests/test_cota_rr_condicional.py`:

~~~
def test_conjunto_con_mbar_cero_contiene_el_punto():
    # enmienda del ancho: la puerta es contener el punto; el ancho contra el tope de 2 es un dato que la pagina publica
    assert r["contiene"] == r["de"] and r["ok"], r
    assert r["tope"] == 2.0 and r["cumple_tope"] == (r["razon_max"] <= 2.0), r


def test_diagnostico_del_ancho():
    d = cc.diagnostico_ancho()
    assert len(d["poliedros"]) == 6 and d["n"] == cc.N_MC
    si = [f for f in d["poliedros"] if f["contiene_delta"]]
    assert si, d
    # los poliedros que contienen a la delta verdadera no rechazan theta verdadero mas que el 5 % nominal, con margen de simulacion
    assert all(f["rechazo"] <= 0.05 + 3 * (0.05 * 0.95 / cc.N_MC) ** 0.5 for f in si), si
    assert d["union_cobertura"] >= 0.95 and d["union_ancho_max"] >= max(f["ancho_max"] for f in d["poliedros"]) - 1e-9, d
~~~
