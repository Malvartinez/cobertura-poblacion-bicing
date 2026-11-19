# Decisiones

Adaptación a Barcelona/Bicing del proyecto [cobertura-poblacion-bicimad](https://github.com/Malvartinez/cobertura-poblacion-bicimad).
Se mantiene el método íntegro (umbrales 250/500 m, corte 1.500 m, reparto por viviendas, Dijkstra multiorigen,
ranking con solapes, ampliación CELF) y la web; aquí solo se anotan las diferencias. Formato: qué y por qué.

## Fuentes

- Estaciones desde el feed GBFS oficial de Bicing (`barcelona-sp.publicbikesystem.net/.../station_information`): 544 estaciones, todas dentro del municipio; se excluirían las virtuales (`is_virtual_station`), aunque hoy no hay ninguna — sin API key y con coordenadas.
- Distritos (10) y barrios (73) desde Open Data BCN (conjunto `20170706-districtes-barris`), leídos por la API `datastore_search` de CKAN — la descarga directa del CSV devuelve 403 a clientes automáticos; la API sirve el mismo recurso con la geometría en WKT ETRS89.
- Municipio = unión de los 10 distritos — el límite OSM de Barcelona incluye aguas marítimas.
- Población: INE, Censo anual 2025 por sección (servicio ArcGIS de Esri España), municipio 08019: 1.068 secciones, 1.713.247 hab.; coincidencia 100 % con la cartografía de secciones 2025.
- Edificios: Catastro INSPIRE Buildings, dataset 08900-BARCELONA (69.911 edificios, 61.120 residenciales con viviendas).
- Red peatonal: extracto PBF de BBBike (Barcelona, datos del 2026-11-14) en lugar de Overpass — desde el entorno de cálculo Overpass cortaba la conexión o no respondía. Se aplica a mano exactamente el filtro de OSMnx 2.x para `network_type="walk"` (mismas claves y expresiones, semántica `!~` de Overpass), se construye el grafo con `graph_from_xml(bidirectional=True)`, se recorta al municipio + 1 km (`truncate_by_edge`) y se simplifica; el resto del script es idéntico.

## Proceso

- CRS EPSG:25831 (ETRS89 / UTM 31N) en lugar de 25830 — Barcelona está en el huso 31.
- La comprobación de total de población de `03_reparto_poblacion.py` compara con la suma del censo descargado en vez de una cifra fija.
- `04_distancias.py` y `08_ampliacion.py` ya no añaden líneas a este fichero en cada ejecución — en el original se duplicaban al relanzar.
- Ampliación con un máximo de 500 estaciones nuevas (1.000 en Madrid) — Barcelona tiene 544 estaciones y 102 km²; con 500 nuevas la cobertura ya llega al 99,4 % en verde y 0,0 % en rojo, más no aporta.
- Corrección de compatibilidad con pandas 3 en `03_reparto_poblacion.py` (asignación con máscara vacía).

## Resultados a vigilar

- 1.351 edificios (5.715 hab.) sin estación a ≤ 1.500 m por la red: 4.895 en Vallvidrera, el Tibidabo i les Planes (sin Bicing) y 756 en la parte alta de Sarrià — se cuentan como rojo.
- 0 estaciones a más de 150 m de la red peatonal.
- La distancia es plana: no tiene en cuenta la pendiente, que en Barcelona (Collserola, Carmel, Turó de la Rovira) pesa mucho para el acceso a pie y en bici.
