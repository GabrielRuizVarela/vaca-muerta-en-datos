# Resumen para un operador de Vaca Muerta

Cada número se recalcula con `uv run python -m pipeline.claims`.

## Qué se ve

- **Primero días, después caudal.** El mes de la fractura, entre 79 y 88% de la caída del padre son días sin producir. En el mes 1, cerca de la mitad ya es menos petróleo por día producido.
- **Caída del padre en el mes 1.** Los padres a menos de 1 km rinden entre 19 y 23 puntos menos de su caudal previo que los controles a 2 a 5 km (2.094 eventos). 23 es la cota superior contra este control: ya había una brecha antes de la fractura. Va de 14,7 puntos menos con padres de 6 a 11 meses a 24,8 puntos menos con padres de 48 meses o más.
- **Se sostiene.** Sacando de a un operador, la brecha queda entre 22,2 y 24,1 puntos menos (sin YPF, 23,0); sacando de a un área, entre 20,2 y 29,3 puntos menos. El intervalo del 95% queda siempre por debajo de cero (el límite alto más alto es de -15,3).
- **A los 6 meses.** La brecha queda en 2,1 puntos menos con el control principal y llega a 4,8 puntos menos con la variante de control de mayor brecha: dentro de 5 puntos, no cero. En volumen (puntos logarítmicos) el intervalo sigue por debajo de cero: no está probado que llegue después.
- **El agua sigue arriba.** El corte de agua del padre sube 13,8 puntos porcentuales en el mayor de los meses 0 y 1 (447 padres) y en los meses 6 a 12 sigue 10,9 puntos arriba (media de cada mes; regla fijada después de ver D2). En los meses 10 a 12 es cerca de la mitad del pico, con intervalos superpuestos y sin prueba de la baja. Medida mes a mes, no como el mayor de dos meses, resiste la cota de Rambachan y Roth con Mbar = 1 (se rompe en 1,83) y la serie cortada en otra fractura a menos de 1 km. Depende de YPF: sin sus pozos da 7,1, con un intervalo que incluye cero.
- **Diferido.** El volumen que falta contra el control en los meses 0 a 6 es de 869 m3 de petróleo por padre en promedio (intervalo del 95%: 574 a 1.150).

## Qué no se sabe

- Si lo diferido se recupera del todo y si el cierre del padre fue preventivo: el dato mensual no lo separa; tus datos diarios, presión de monitoreo y cierres sí.
- Si la dosis explica la caída: no se ve, pero el efecto mínimo detectable con 80% de potencia, de 0,31 desvíos de la caída por desvío de la dosis, es optimista según la simulación: uno menor puede pasar inadvertido.
- Si la caída del petróleo es una causa: es una huella; no resiste la cota de Rambachan y Roth ni con Mbar = 0.

## Qué hacer con esto

Corré parte del estudio con el dato mensual de tus pozos: `uv run python -m pipeline.local` (`docs/operador-datos-propios.md`). Da la brecha, el modelo de dosis y el corte de agua: lee el agua mensual opcional; no lee diario. Para valorar el diferido: `wiki/hallazgos/decision_operador.md`.

No es una recomendación de operación: describe asociaciones en pozos de varios operadores.
