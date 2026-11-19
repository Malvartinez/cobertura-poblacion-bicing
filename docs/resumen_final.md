# Resumen de resultados — cobertura poblacional de Bicing (Barcelona)

Datos generados el 2026-11-19. Población: INE, Censo anual de población a 1 de enero de 2025 (1.068 secciones,
1.713.247 habitantes). Estaciones: feed GBFS de Bicing descargado el 2026-11-19 (544 estaciones, todas dentro del
término municipal).

## Ciudad

| Distancia andando a la estación más cercana | Población | % |
|---|---:|---:|
| Menos de 250 m (verde) | 1.113.089 | 65,0 % |
| 250–500 m (amarillo) | 544.268 | 31,8 % |
| Más de 500 m (rojo) | 55.890 | 3,3 % |

## Distritos (ordenados por % en verde)

| Distrito | Población | Verde | Amarillo | Rojo |
|---|---:|---:|---:|---:|
| Eixample | 274.598 | 85.2 % | 14.8 % | 0.0 % |
| Sants-Montjuïc | 194.201 | 70.1 % | 29.4 % | 0.5 % |
| Ciutat Vella | 112.290 | 69.9 % | 30.1 % | 0.0 % |
| Les Corts | 83.643 | 68.8 % | 30.0 % | 1.1 % |
| Sant Andreu | 156.685 | 67.6 % | 32.3 % | 0.0 % |
| Sant Martí | 250.820 | 66.5 % | 32.8 % | 0.8 % |
| Gràcia | 126.052 | 58.0 % | 33.1 % | 8.9 % |
| Nou Barris | 181.463 | 52.2 % | 42.0 % | 5.7 % |
| Sarrià-Sant Gervasi | 151.850 | 51.1 % | 41.8 % | 7.1 % |
| Horta-Guinardó | 181.645 | 48.9 % | 40.3 % | 10.8 % |

Barrios con más población en rojo (en %): Vallvidrera, el Tibidabo i les Planes (100 %, 4.895 hab.), Vallbona
(100 %, 1.411), el Coll (92,8 %, 7.412), Torre Baró (80,6 %, 2.557) y Can Baró (38,7 %, 3.705). Son barrios de
montaña o periféricos (Collserola, Turó de la Rovira, borde con Montcada) donde no hay estaciones o están al pie de
fuertes pendientes.

## Estaciones con más población a < 250 m andando

1. C/ Cardenal Tedeschini, 13 (Sant Andreu) — 8.531 hab.
2. C/ Nàpols, 82 (Eixample) — 8.415
3. C/ Riera Alta, 6 (Ciutat Vella) — 8.304
4. Rambla Prim, 79 (Sant Martí) — 8.283
5. Pg. Fabra i Puig, 344 (Nou Barris) — 7.353

33 estaciones no tienen población residente a < 250 m (frente marítimo, parques, Zona Franca, campus).


## Ampliación óptima

Selección secuencial (greedy) de 500 nuevas estaciones que más mejoran la cobertura poblacional (18454 candidatos).

| Nuevas estaciones | Verde | Amarillo | Rojo |
|---:|---:|---:|---:|
| 0 | 65.0 % | 31.8 % | 3.3 % |
| 25 | 72.1 % | 26.5 % | 1.5 % |
| 50 | 77.4 % | 21.3 % | 1.4 % |
| 100 | 84.5 % | 14.7 % | 0.9 % |
| 250 | 95.1 % | 4.5 % | 0.4 % |
| 500 | 99.4 % | 0.5 % | 0.0 % |

Las 5 primeras:

1. Horta-Guinardó · el Carmel — ganancia ponderada 13.693
2. Ciutat Vella · el Barri Gòtic — ganancia ponderada 11.481
3. Horta-Guinardó · el Carmel — ganancia ponderada 9.804
4. Nou Barris · Ciutat Meridiana — ganancia ponderada 8.037
5. Sants-Montjuïc · Sants — ganancia ponderada 6.861
