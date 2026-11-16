# Siguientes investigaciones (lista ordenada por valor por hora)

Escrita el 2026-11-16, después de cerrar la 3.8. Cada punto se preregistra en el encabezado de su módulo y se commitea antes de correr, como en la fase 5. Las cifras de este documento pueden quedar viejas: valen las de la wiki.

Estado: las secciones 3.1 a 3.10 del plan de la fase 3 están hechas. La 3.8 dio "sin dosis y respuesta" en el índice del mes 1 y en la parte de caudal por día (`wiki/hallazgos/dosis.md`).

## Ordenadas

1. **Cierre a 6 meses con otros controles (3 h).** La brecha del mes 1 ya se publica contra el anillo de 5 a 10 km (`mart_descomposicion_distancia`), pero la afirmación de que la brecha se cierra a los 6 meses (`recuperacion_mes6`) solo se mide contra el control de 2 a 5 km, que por la propia descomposición recibe algo de efecto (brecha de 2,8 puntos entre 5 a 10 y 2 a 5 km). Cuatro controles: 2 a 5 km (de referencia), 5 a 10 km, 2 a 10 km, y 2 a 5 km sin padres con otro hijo a menos de 2 km en los meses -6 a +6. Meses k = 1 y 6, IC por pads hijo. Regla: la afirmación es robusta si en los cuatro controles la brecha del mes 1 es menor que -0,10 y la del mes 6 tiene valor absoluto menor que 0,05; si en alguno el mes 6 no cumple, el README y la página de recuperación dicen con qué control se cierra y con cuál no.
2. **Dosis mes a mes (3 h).** La 3.8 mira solo k = 1. Una respuesta tardía (golpe que se nota en k = 2 a 4) no aparecería. Mismo modelo conjunto de `pipeline/dosis.py` para k = 1 a 4 en la parte de caudal por día, Holm sobre 16 pruebas (4 variables por 4 meses). Regla: si ninguna cumple, se agrega una línea a la página de dosis ("tampoco con respuesta tardía"); si alguna cumple, se informa como exploratoria y no cambia el veredicto de la 3.8.
3. **Dosis del pad y cercanía (2 h).** Dosis medida como arena total del pad hijo (no del pozo más cercano) y subconjunto a menos de 0,5 km con la interacción depleción por cercanía. Es la versión de la física más favorable a encontrar un efecto; si tampoco aparece, la lectura de "no hay dosis y respuesta en datos públicos" queda más firme. Preregistrar los dos cortes antes de correr.

## Bloqueadas

- **Modelo de ramas del eje:** necesita azimut de rama y coordenadas de fondo, que no están en la base pública. Se retoma si aparecen.
- **Actualización de datos con la próxima publicación mensual:** la descarga corre solo desde una máquina en Argentina (`./refresh.sh`); no se puede hacer desde este entorno.
- **Prueba prospectiva del eje congelado:** hace falta esperar unos 2 años de eventos nuevos.
