# Prueba prospectiva

Página generada por `pipeline/prospectiva.py`. El resultado principal se midió sobre datos ya publicados; esta página congela dos predicciones con los datos hasta 2026-09 y las puntúa cuando se publican los meses siguientes, para un operador de Vaca Muerta que quiere saber si la huella vuelve a aparecer en meses que nadie había visto. La regla, los mínimos y el veredicto se fijaron en el código antes de congelar. Complementa [Interferencia entre fracturas](interferencia.md), las [pruebas de falsación](placebo.md) y los [bloques espaciales](bloques.md).

## Estado

- **Pendiente.** El warehouse llega a 2026-09, sin meses posteriores a los congelados (2026-09): no hay nada que puntuar. Se puntúa cuando se publique un mes nuevo.

## Lo congelado

- Fecha de congelado: 2026-11-18. Datos hasta 2026-09.
- sha256 del archivo congelado (`data/prospectiva_congelada.json`): `7a49f4135d042ff064e77914cab0d0c2997b4ae1d1d022aabacf58c2fab83e6c`.
- sha256 de `data/manifest.json` al congelar: `fb843ffcf005383eeece5a71c963ee864324b1cf5173a4b208b1f0b56d4e382f`; CSV de producción: `61cecc31c8dd`; CSV de fractura: `ff95734bf485`.
- P1: brecha del mes 1 de -22,9 puntos de índice, con intervalo predicho de -28,7 a -16,8 (IC 95% por bloques de 5 km del resultado principal). Entran los eventos con fractura del hijo desde 2026-09; al congelar se conocían 0 cercanos y 17 controles.
- P2: brecha del mes 6 a menos de 5,0 puntos de cero (-2,1 puntos con los datos hasta 2026-09). Entran los eventos con fractura del hijo desde 2026-04; al congelar se conocían 129 cercanos y 1.235 controles.
- Del gas no se predice nada: el estudio del padre gasífero dio "no firme" por pretendencia.

## Regla de puntuación

- Los eventos se recalculan con el warehouse nuevo con las reglas del resultado principal (base de los meses -3 a -1, padre de al menos 6 meses, el hijo más cercano fija la banda: cercano a menos de 1 km, control de 2 a 5 km). Entran también los hijos que la carga de fracturas agregue después de congelar: la predicción es sobre la regla, y lo que la hace prospectiva es que el mes medido no estaba publicado.
- Brecha: mediana del índice de los cercanos menos la de los controles, con IC 95% por bootstrap de bloques de 5 km del pad hijo.
- Mínimos: 100 cercanos y 100 controles con dato en el mes, y 15 bloques de 5 km; debajo, "sin muestra". Un evento sin dato en el mes no cuenta y no se imputa; sin IC calculable, "no firme".
- P1. Sostiene: IC bajo cero que se superpone con el intervalo predicho. No se sostiene: IC entero fuera del intervalo predicho (por arriba, brecha menor o nula; por abajo, mayor). No firme: cualquier otro caso.
- P2. Sostiene: brecha a menos de 5,0 puntos con IC entero entre -10,0 y 10,0. No se sostiene: IC que excluye cero con brecha de 5,0 puntos o más. No firme: cualquier otro caso.
- La puntuación se niega si el sha256 del archivo congelado no coincide con el de al lado y con el del código.

## Límites

- Repite el diseño sobre meses nuevos, no prueba causa.
- Entran unos 30 eventos cercanos por mes de fractura con la carga al día, y la carga de fracturas viene atrasada: pasan varias publicaciones antes de salir de "sin muestra", y con poca muestra lo esperable es "no firme".
- Cada publicación vuelve a puntuar con más eventos: son miradas repetidas sin ajuste por eso; cada veredicto va con el mes de sus datos.
