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

- 1.346 edificios (5.667 hab.) sin estación a ≤ 1.500 m por la red, casi todos en Vallvidrera, el Tibidabo i les Planes (sin Bicing) y la parte alta de Sarrià — se cuentan como rojo.
- 0 estaciones a más de 150 m de la red peatonal.
- La distancia es plana: no tiene en cuenta la pendiente, que en Barcelona (Collserola, Carmel, Turó de la Rovira) pesa mucho para el acceso a pie y en bici.

## Distancia desde el borde del edificio (2026-11-19)

- La distancia de cada edificio es la de su mejor punto de acceso: los dos extremos de la arista más cercana a su punto interior (como antes) o cualquier nodo de la red a ≤ 30 m de su huella, sumando la distancia del nodo al borde (`pipeline/_acceso.py`, usado por 04, 07 y 08) — mismo criterio que el proyecto BicinRivas (ADR-0126): en las manzanas grandes el punto interior se enganchaba a la calle de atrás y el método era claramente pesimista. Es algo optimista (supone que el portal da a la calle más favorable). Barcelona pasa de 65,0 % a 74,1 % de población a menos de 250 m.

## Distancia desde los portales del Catastro (2026-11-20)

- A propuesta del usuario: la dirección catastral de un edificio es la calle por la que se entra, así que la distancia se mide desde sus portales y no desde cualquier punto de la fachada.
- Fuente: Catastro INSPIRE Addresses (08900-BARCELONA), direcciones con `specification = Entrance` (punto del portal sobre la fachada), enlazadas al edificio por la referencia catastral (los 14 últimos caracteres del `localId`). Las de tipo `Parcel` no se usan. El GML viene en ISO-8859-1.
- Cada portal se engancha a la arista más cercana. Si esa arista es otra calle con nombre (portal en una esquina) y hay a ≤ 40 m una arista de la calle de su dirección, se usa esta. Las aristas sin nombre (aceras, sendas) se aceptan tal cual. Opciones del edificio: los dos extremos de la arista de cada portal (desfase = portal-arista + tramo hasta el extremo); el mínimo.
- Edificios sin portal en el Catastro: método de borde anterior (sin cambios).
- Solo portal, sin regla mixta: el usuario la eligió sabiendo que el Catastro registra a menudo una única dirección por parcela, lo que penaliza a las manzanas cerradas y conjuntos con varios portales reales.
- Paso nuevo `pipeline/01_descarga_direcciones.py` (copia adaptada del de cobertura-bici-publica-espana) y `pipeline/_acceso.py` igual al del proyecto nacional.
- Resultado: 45.053 edificios (74 %) con portal; 94,5 % de los portales en una arista de su calle. Población a menos de 250 m: 74,1 % → 72,8 %; a 250–500 m: 23,0 % → 24,2 %; a más de 500 m: 2,9 % → 3,0 %. Validación con networkx: 50/50.
