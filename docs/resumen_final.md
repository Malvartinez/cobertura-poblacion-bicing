# Resumen de resultados — cobertura poblacional de Bicing (Barcelona)

Datos generados el 2026-11-19 (recalculado el mismo día midiendo desde el borde de cada edificio; ver
`docs/decisiones.md`). Población: INE, Censo anual de población a 1 de enero de 2025 (1.068 secciones,
1.713.247 habitantes). Estaciones: feed GBFS de Bicing descargado el 2026-11-19 (544 estaciones, todas dentro del
término municipal).

## Ciudad

| Distancia andando a la estación más cercana | Población | % |
|---|---:|---:|
| Menos de 250 m (verde) | 1.269.714 | 74,1 % |
| 250–500 m (amarillo) | 393.623 | 23,0 % |
| Más de 500 m (rojo) | 49.910 | 2,9 % |

## Distritos (ordenados por % en verde)

| Distrito | Población | Verde | Amarillo | Rojo |
|---|---:|---:|---:|---:|
| Eixample | 274.598 | 90,7 % | 9,3 % | 0,0 % |
| Sant Andreu | 156.685 | 80,2 % | 19,8 % | 0,0 % |
| Sant Martí | 250.820 | 78,6 % | 21,0 % | 0,4 % |
| Les Corts | 83.643 | 78,3 % | 20,6 % | 1,0 % |
| Ciutat Vella | 112.290 | 77,9 % | 22,1 % | 0,0 % |
| Sants-Montjuïc | 194.201 | 77,7 % | 22,1 % | 0,2 % |
| Gràcia | 126.052 | 66,1 % | 25,6 % | 8,4 % |
| Nou Barris | 181.463 | 65,9 % | 28,9 % | 5,2 % |
| Sarrià-Sant Gervasi | 151.850 | 59,4 % | 34,1 % | 6,5 % |
| Horta-Guinardó | 181.645 | 55,5 % | 34,7 % | 9,7 % |

Barrios con más población en rojo (en %): Vallvidrera, el Tibidabo i les Planes (100 %, 4.895 hab.), Vallbona
(100 %, 1.411), el Coll (91,6 %, 7.320), Torre Baró (80,6 %, 2.557), Can Baró (37,1 %, 3.548) y Ciutat Meridiana
(35,0 %, 3.943). Son barrios de montaña o periféricos (Collserola, Turó de la Rovira, borde con Montcada) donde no
hay estaciones o están al pie de fuertes pendientes.

## Estaciones con más población a < 250 m andando

1. C/ Cardenal Tedeschini, 13 (Sant Andreu) — 10.874 hab.
2. C/ Riera Alta, 6 (Ciutat Vella) — 10.362
3. Rambla Prim, 79 (Sant Martí) — 9.705
4. Pl. dels Jardins d'Alfàbia, 1 (Nou Barris) — 9.059
5. C/ Nàpols, 82 (Eixample) — 8.807

24 estaciones no tienen población residente a < 250 m (frente marítimo, parques, Zona Franca, campus).

## Ampliación óptima

Selección secuencial (greedy) de 500 nuevas estaciones que más mejoran la cobertura poblacional (18.454 candidatos).

| Nuevas estaciones | Verde | Amarillo | Rojo |
|---:|---:|---:|---:|
| 0 | 74,1 % | 23,0 % | 2,9 % |
| 25 | 81,2 % | 17,6 % | 1,2 % |
| 50 | 85,4 % | 13,7 % | 0,9 % |
| 100 | 91,1 % | 8,2 % | 0,7 % |
| 250 | 98,0 % | 1,8 % | 0,2 % |
| 500 | 99,9 % | 0,1 % | 0,0 % |

Las 5 primeras:

1. Gràcia · el Coll — ganancia ponderada 14.465
2. Ciutat Vella · el Barri Gòtic — ganancia ponderada 10.550
3. Horta-Guinardó · el Carmel — ganancia ponderada 10.096
4. Nou Barris · Ciutat Meridiana — ganancia ponderada 8.938
5. Horta-Guinardó · la Teixonera — ganancia ponderada 8.238
