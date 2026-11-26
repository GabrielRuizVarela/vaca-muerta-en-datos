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
| entra agua en los días producidos | Se conserva con la salvedad: entra agua en los días que el padre produce; el volumen del mes no sube porque se pierden días. |
| el corte sube porque cae el petróleo | Se quita "comunicación física" de la entrada. La frase pasa a: la primera fractura de un hijo a menos de 1 km sube el corte de agua del padre porque cae su petróleo; su agua no sube más de la cota (IC alto). La regla de D2 le había dado el nombre "comunicación física"; D3, fijado después, muestra que ese nombre no se gana. El README deja de decir que hay una afirmación de agua que entra; el límite "no dice cuál de las dos domina" se reemplaza por la respuesta. `wiki/index.md` deja de decir "el corte de agua como canal físico". |
| no firme, sin muestra o no sobrevive | También se quita "comunicación física" de la entrada: la suba del corte se sostiene, el canal queda sin identificar, y se dice por qué D3 no decide. |

El placebo de nunca tratados sobre dW, si rompe (IC que excluye cero y 2 puntos porcentuales o más), se dice en la misma fila
del README y en el resumen de D2, como hallazgo posterior a su regla.

## D4. Dosis

- Distancia del primer golpe en tres bandas: 0 a 0,5 km y 0,5 a 1 km parten los tratados de D2; 1 a 2 km es una cohorte nueva
  (primer golpe a menos de 2 km entre 1 y 2 km, ninguno a menos de 1 km en la ventana, mismas condiciones y mismos controles).
  La banda de 3 a 5 km es el placebo de distancia falsa ya medido; se reimprime como cuarto punto.
- Decide sobre dW de D2; dA de D3 se publica igual. **Gradiente** si las tres bandas bajan de cerca a lejos y el IC de cerca
  menos lejos (mismos sorteos) queda sobre cero; **sin gradiente** si ese IC incluye cero; **sin muestra** si una banda tiene
  menos de 100 tratados; **no firme** en otro caso.
- Tamaño: agua de fractura del hijo de la cohorte (`dim_fractura_pozo.agua_m3`), terciles entre los tratados de D2 que la
  tienen; mismo veredicto con el tercil alto menos el bajo; **sin dato** si la tiene menos de 70% de los tratados. La longitud
  de rama se publica sin veredicto.
- Ya publicado y conocido: costado 16,2 contra punta 7,8 puntos porcentuales. D4 no lo repite.

## D5. Forma en el tiempo

- Serie de e = -6 a 12, H = 12, mes por mes (no el máximo): dW(e), dA(e), dO(e). Controles aún no tratados hasta g + 12.
- Mide la primera fractura y lo que venga después: no se exige limpieza después del mes 1 (D1b mostró que exigirla vacía la
  muestra). Se publica cuántos tratados reciben otro golpe a 2 km en los meses 2 a 12.
- Veredicto sobre la media de dW en los meses 6 a 12: **persiste** (IC bajo sobre cero), **se cura** (IC incluye cero y su IC
  alto es menor que la mitad de dW de los meses 0 y 1), **sin muestra** (menos de 200), **no firme**. El primer mes con IC
  sobre cero se publica sin veredicto.

## D6. Dónde se sostiene

- Todos los cortes publicados, sin elegir: cada operador con 50 tratados o más (dentro y sin él), grupo de edad del padre,
  período de la cohorte (hasta 2018, 2019 a 2021, 2022 en adelante) y área con 50 tratados o más. La formación no es corte:
  el universo es Vaca Muerta shale. Sin ajuste por comparaciones múltiples; ningún subgrupo tiene veredicto.
- Veredicto sobre dW: **general** si sin cada operador el IC bajo sigue sobre cero; **depende de un operador** (con nombre).

## D7. Colorado

- Mismo diseño y mismas constantes sobre el warehouse opcional de Colorado: pozos horizontales con coordenadas, mes de
  fractura de `co_hijo` sin fecha dudosa, producción con agua y días.
- Compuerta: **sin dato de agua** si menos de 70% de los meses base de los tratados tienen agua y días. Si pasa, D2 y D3 con
  sus veredictos tal cual, y: **se repite** (D2 sostiene y D3 da lo mismo que en Vaca Muerta), **se repite en parte** (D2
  sostiene, D3 distinto), **no se repite** (D2 no sostiene), **sin muestra**.

## D8. Lectura operativa

Solo si D3 da agua que entra y D4 da gradiente de distancia: un párrafo sobre qué distancia y qué tamaño de hijo concentran el
efecto. Sin dinero ni veredicto.

## Qué no va a poder decir ningún resultado

Sigue siendo causa bajo los supuestos de `pipeline.causal` (tendencias paralelas condicionales, sin anticipación más allá de
3 meses, sin derrame sobre controles limpios a 2 km), no un hecho físico medido. D3 ve el agua en el volumen mensual, no
el agua entrando: la tabla (e) de `docs/plan-causal.md` (presión, producción diaria, trazadores) sigue siendo lo que la
cargaría.
