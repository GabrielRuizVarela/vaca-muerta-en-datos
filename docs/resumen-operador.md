# Resumen para un operador de Vaca Muerta

Una página con lo que el dato público dice y no dice sobre fracturar un hijo cerca de un padre en producción. Cada número se verifica contra el warehouse con `uv run python -m pipeline.claims`.

## Qué se ve

- **Caída del padre en el mes 1.** Un mes después de fracturar un hijo, los padres a menos de 1 km rinden 23,0 puntos menos de su caudal previo que los controles a 2 a 5 km (2.094 eventos). Va de 14,7 puntos menos con padres de 6 a 11 meses de producción a 24,8 puntos menos con padres de 48 meses o más.
- **Se sostiene.** Sacando de a un operador, la brecha queda entre 22,2 y 24,1 puntos menos (sin YPF, 23,0); sacando de a un área, entre 20,2 y 29,3 puntos menos. El intervalo del 95% queda siempre por debajo de cero (el límite alto más alto es de -15,3).
- **A los 6 meses.** La brecha queda en 2,1 puntos menos con el control principal y llega a 4,8 puntos menos con la variante de control de mayor brecha entre las cuatro: dentro de 5 puntos, que no es cero.
- **Diferido.** El volumen que falta contra el control en los meses 0 a 6 (el diferido; no se sabe si llega después) es de 869 m3 de petróleo por padre en promedio (intervalo del 95%: 574 a 1.150).

## Qué no se sabe

- No se sabe si lo diferido se recupera del todo ni si el cierre del padre fue preventivo: el dato mensual público no lo separa.
- Con este dato no se ve que la dosis explique la caída, pero la cuenta analítica da un efecto mínimo detectable, con 80% de potencia, de 0,31 desvíos de la caída por desvío de la dosis, y la simulación de planta y recupera muestra que esa cuenta es optimista: hace falta más. Un efecto de 0,2 puede pasar inadvertido.
- El dato es público y mensual; no trae espaciamiento real entre ramas, presión de monitoreo ni registros de cierre.

## Qué hacer con esto

Corré el mismo estudio sobre tus pozos, en tu máquina, con `uv run python -m pipeline.local` (`docs/operador-datos-propios.md`). Lo que más achicaría la duda: espaciamiento real, presión de monitoreo del padre durante la fractura del hijo y fecha y hora de los cierres. Para valorar el diferido con tu precio y tu tasa: `wiki/hallazgos/decision_operador.md`.

No es una recomendación de operación: describe asociaciones en pozos de varios operadores.
