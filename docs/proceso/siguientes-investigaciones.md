# Siguientes investigaciones: cerrado con dato público

Esta lista se escribió el 2026-11-16, después de cerrar la 3.8, ordenada por valor por hora. Los tres puntos se corrieron, cada uno con su regla fijada en el encabezado del módulo y commiteada antes de correr. No queda ninguna investigación abierta que el dato público pueda resolver: lo que falta necesita otro dato (abajo).

El texto de cada punto queda como se escribió, porque los módulos lo citan como origen de su regla. Las cifras de este documento pueden quedar viejas: valen las de la wiki.

## Los tres puntos, con su resultado

1. **Cierre a 6 meses con otros controles (3 h).** La brecha del mes 1 ya se publica contra el anillo de 5 a 10 km (`mart_descomposicion_distancia`), pero la afirmación de que la brecha se cierra a los 6 meses (`recuperacion_mes6`) solo se mide contra el control de 2 a 5 km, que por la propia descomposición recibe algo de efecto (brecha de 2,8 puntos entre 5 a 10 y 2 a 5 km). Cuatro controles: 2 a 5 km (de referencia), 5 a 10 km, 2 a 10 km, y 2 a 5 km sin padres con otro hijo a menos de 2 km en los meses -6 a +6. Meses k = 1 y 6, IC por pads hijo. Regla: la afirmación es robusta si en los cuatro controles la brecha del mes 1 es menor que -0,10 y la del mes 6 tiene valor absoluto menor que 0,05; si en alguno el mes 6 no cumple, el README y la página de recuperación dicen con qué control se cierra y con cuál no.

   Resultado: robusto a la elección del control. La regla se cumple en los cuatro controles; el intervalo de la brecha del mes 6 todavía excluye cero en algunos, así que "se cierra" quiere decir menos de 5 puntos y no cero (`pipeline/anillo.py`, `wiki/hallazgos/anillo.md`).

2. **Dosis mes a mes (3 h).** La 3.8 mira solo k = 1. Una respuesta tardía (golpe que se nota en k = 2 a 4) no aparecería. Mismo modelo conjunto de `pipeline/dosis.py` para k = 1 a 4 en la parte de caudal por día, Holm sobre 16 pruebas (4 variables por 4 meses). Regla: si ninguna cumple, se agrega una línea a la página de dosis ("tampoco con respuesta tardía"); si alguna cumple, se informa como exploratoria y no cambia el veredicto de la 3.8.

   Resultado: tampoco con respuesta tardía. Ninguna de las 16 pruebas cumple tras Holm (`pipeline/dosis_meses.py`, `wiki/hallazgos/dosis_meses.md`).

3. **Dosis del pad y cercanía (2 h).** Dosis medida como arena total del pad hijo (no del pozo más cercano) y subconjunto a menos de 0,5 km con la interacción depleción por cercanía. Es la versión de la física más favorable a encontrar un efecto; si tampoco aparece, la lectura de "no hay dosis y respuesta en datos públicos" queda más firme. Preregistrar los dos cortes antes de correr.

   Resultado: sigue sin dosis y respuesta, ni con la arena del pad ni en la cercanía. Es una prueba agregada después de ver los resultados de la 3.8 y la página lo dice; la página también da la cota superior de los intervalos, que es el tamaño de efecto que no se descarta (`pipeline/dosis_pad.py`, `wiki/hallazgos/dosis_pad.md`). Cuánto efecto podía detectar este dato está en `wiki/hallazgos/potencia_dosis.md`.

## Lo que el dato público no resuelve

- **Geometría de las ramas:** hacen falta el azimut de la rama y las coordenadas de fondo, que no están en la base pública. La regla de parada del eje se cumplió y el proyecto ya no presenta un eje de interferencia (`wiki/hallazgos/eje_parada.md`).
- **Cierre preventivo o daño:** el dato mensual no los separa. Lo separan los registros de cierres con fecha y hora y la presión de cabeza o de fondo del padre durante la fractura del hijo (`wiki/hallazgos/decision_operador.md`, sección "Qué no se resuelve y qué dato interno lo resolvería"); el mismo estudio corre sobre los datos de un operador con `docs/operador-datos-propios.md`.
- **Si la huella vuelve a aparecer:** la prueba prospectiva quedó congelada el 2026-11-18 con los datos hasta 2026-09 y se puntúa con cada publicación nueva (`wiki/hallazgos/prospectiva.md`). No es una investigación nueva: es esperar el dato.
- **Actualización de datos:** la descarga corre solo desde una máquina en Argentina (`./refresh.sh`).

## Brechas abiertas, por prioridad

<!-- brechas:inicio -->
1. **B02** (código): El modo local no lee datos diarios de producción. (`README.md:5`)
2. **B03** (código): El modo local no lee registros de cierres de pozos. (`README.md:3`)
3. **B06** (datos del operador): El dato mensual no separa un cierre preventivo de un daño: hacen falta los registros de cierres con fecha y hora y la presión de cabeza o de fondo del padre. (`docs/proceso/siguientes-investigaciones.md:24`)
4. **B07** (datos del operador): La geometría de las ramas necesita el azimut y las coordenadas de fondo, que no están en la base pública. (`docs/proceso/siguientes-investigaciones.md:23`)
5. **B09** (código): Tratado y control se definen por la distancia entre bocas de pozo, no entre ramas; parte de los pares queda mal clasificada. (`wiki/hallazgos/causal.md:104`)
6. **B04** (leer la fuente): Las fuentes de producción por pozo de Montana, Nuevo México, Pennsylvania y Utah no se pudieron verificar (fuentes_mundo.md líneas 39, 40, 42 y 43). (`wiki/hallazgos/fuentes_mundo.md:39`)
7. **B05** (leer la fuente): Crespo 2020, Magneres 2020, Romero 2020, Fasola 2023 y Mamani 2024 y los demás estudios de Vaca Muerta se leyeron solo como metadatos (título, autores y DOI); no se comparó su muestra ni su método. (`wiki/hallazgos/literatura.md:43`)
<!-- brechas:fin -->
