# Resumen de resultados — cobertura poblacional de Bicing (Barcelona)

Datos generados el 2026-11-19 (recalculado el 2026-11-20 midiendo desde los portales del Catastro; ver
`docs/decisiones.md`). Población: INE, Censo anual de población a 1 de enero de 2025 (1.068 secciones,
1.713.247 habitantes). Estaciones: feed GBFS de Bicing descargado el 2026-11-19 (544 estaciones, todas dentro del
término municipal).

## Ciudad

| Distancia andando a la estación más cercana | Población | % |
|---|---:|---:|
| Menos de 250 m (verde) | 1.247.364 | 72,8 % |
| 250–500 m (amarillo) | 413.921 | 24,2 % |
| Más de 500 m (rojo) | 51.962 | 3,0 % |

## Distritos (ordenados por % en verde)

| Distrito | Población | Verde | Amarillo | Rojo |
|---|---:|---:|---:|---:|
| Eixample | 274.598 | 91,1 % | 8,9 % | 0,0 % |
| Sant Andreu | 156.685 | 78,7 % | 21,3 % | 0,0 % |
| Les Corts | 83.643 | 78,2 % | 20,6 % | 1,2 % |
| Sant Martí | 250.820 | 77,3 % | 22,2 % | 0,5 % |
| Sants-Montjuïc | 194.201 | 76,3 % | 23,2 % | 0,5 % |
| Ciutat Vella | 112.290 | 75,0 % | 25,0 % | 0,0 % |
| Gràcia | 126.052 | 64,8 % | 26,7 % | 8,5 % |
| Nou Barris | 181.463 | 64,0 % | 30,5 % | 5,5 % |
| Sarrià-Sant Gervasi | 151.850 | 57,7 % | 35,7 % | 6,6 % |
| Horta-Guinardó | 181.645 | 53,2 % | 36,8 % | 10,0 % |

Barrios con más población en rojo (en %): Vallvidrera, el Tibidabo i les Planes (100 %, 4.895 hab.), Vallbona
(100 %, 1.411), el Coll (91,6 %, 7.989 hab. en el barrio), Torre Baró (80,6 %, 3.174), Can Baró (37,6 %, 9.572),
Ciutat Meridiana (35,0 %, 11.260) y la Teixonera (33,9 %, 12.526). Son barrios de montaña o periféricos (Collserola, Turó de la Rovira, borde con Montcada) donde no
hay estaciones o están al pie de fuertes pendientes.

## Estaciones con más población a < 250 m andando

1. C/ Cardenal Tedeschini, 13 (Sant Andreu) — 10.052 hab.
2. C/ Riera Alta, 6 (Ciutat Vella) — 9.555
3. Rambla Prim, 79 (Sant Martí) — 9.453
4. C/ Antilles, 8 (Sant Andreu) — 8.844
5. C/ Nàpols, 82 (Eixample) — 8.804

27 estaciones no tienen población residente a < 250 m (frente marítimo, parques, Zona Franca, campus).

## Ampliación óptima

Selección secuencial (greedy) de 500 nuevas estaciones que más mejoran la cobertura poblacional (18.454 candidatos).

| Nuevas estaciones | Verde | Amarillo | Rojo |
|---:|---:|---:|---:|
| 0 | 72,8 % | 24,2 % | 3,0 % |
| 25 | 79,9 % | 18,7 % | 1,3 % |
| 50 | 84,3 % | 14,6 % | 1,0 % |
| 100 | 90,4 % | 8,9 % | 0,7 % |
| 250 | 97,7 % | 2,1 % | 0,2 % |
| 500 | 99,9 % | 0,1 % | 0,0 % |

Las 5 primeras:

1. Horta-Guinardó · el Carmel — ganancia ponderada 14.248
2. Ciutat Vella · el Barri Gòtic — ganancia ponderada 11.433
3. Horta-Guinardó · el Carmel — ganancia ponderada 10.061
4. Nou Barris · Ciutat Meridiana — ganancia ponderada 9.030
5. Nou Barris · les Roquetes — ganancia ponderada 7.107
