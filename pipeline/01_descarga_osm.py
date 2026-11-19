"""Descarga la red peatonal OSM de Barcelona municipio (+1 km) y la guarda en parquet/gpkg."""
import json, time, datetime as dt
from pathlib import Path
import osmnx as ox, networkx as nx, geopandas as gpd, pandas as pd
from shapely.geometry import LineString

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
f_nod, f_ari, f_meta = OUT/"red_nodos.parquet", OUT/"red_aristas.gpkg", OUT/"meta_osm.json"
if f_nod.exists() and f_ari.exists() and f_meta.exists():
    print("Salidas existentes; nada que hacer"); raise SystemExit

import re, gc, osmium
ox.settings.log_console = False
ox.settings.useful_tags_way = ["highway", "name"]
def log(m): print(time.strftime("%H:%M:%S"), m, flush=True)
# Overpass no es accesible de forma fiable desde el entorno de calculo: la red se construye desde el
# extracto PBF de BBBike (Barcelona) aplicando el mismo filtro que OSMnx usa para network_type="walk".
URL_PBF = "https://download.bbbike.org/osm/bbbike/Barcelona/Barcelona.osm.pbf"
RAW = ROOT / "data/raw/osm"; RAW.mkdir(parents=True, exist_ok=True)
PBF = RAW / "Barcelona.osm.pbf"; XML = RAW / "red_walk.osm"
if not PBF.exists():
    import requests
    with requests.get(URL_PBF, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(PBF, "wb") as f:
            for c in r.iter_content(1 << 20): f.write(c)
fecha_osm = osmium.io.Reader(str(PBF)).header().get("osmosis_replication_timestamp")
NEG = {"area": "yes", "access": "private",
       "highway": "abandoned|bus_guideway|construction|cycleway|motor|no|planned|platform|proposed|raceway|razed|rest_area|services",
       "foot": "no", "service": "private", "sidewalk": "separate", "sidewalk:both": "separate",
       "sidewalk:left": "separate", "sidewalk:right": "separate"}
NEG = {k: re.compile(v) for k, v in NEG.items()}  # semantica Overpass "!~": la clave falta o no casa

t0 = time.time()
g = gpd.read_file(OUT / "municipio.gpkg").to_crs(25831)
print("area km2:", round(g.geometry.area.sum()/1e6, 1))
poly = gpd.GeoSeries([g.geometry.union_all().buffer(1000)], crs=25831).to_crs(4326).iloc[0]

def ok(tags):
    if "highway" not in tags: return False
    return not any(k in tags and rx.search(tags[k]) for k, rx in NEG.items())
ways, need = [], set()
for w in osmium.FileProcessor(str(PBF), osmium.osm.WAY):
    t = dict(w.tags)
    if ok(t):
        refs = [n.ref for n in w.nodes]
        ways.append((w.id, refs, {k: t[k] for k in ("highway", "name", "oneway") if k in t})); need.update(refs)
from xml.sax.saxutils import quoteattr as q
with open(XML, "w", encoding="utf-8") as fh:
    fh.write("<?xml version='1.0' encoding='UTF-8'?>\n<osm version='0.6'>\n")
    for n in osmium.FileProcessor(str(PBF), osmium.osm.NODE):
        if n.id in need: fh.write(f"<node id='{n.id}' lat='{n.location.lat:.7f}' lon='{n.location.lon:.7f}'/>\n")
    for wid, refs, t in ways:
        fh.write(f"<way id='{wid}'>" + "".join(f"<nd ref='{r}'/>" for r in refs) +
                 "".join(f"<tag k={q(k)} v={q(v)}/>" for k, v in t.items()) + "</way>\n")
    fh.write("</osm>\n")
log("xml peatonal: %d vias, %d nodos" % (len(ways), len(need))); del ways, need; gc.collect()
G = ox.graph_from_xml(XML, bidirectional=True, simplify=False, retain_all=True)
G = ox.truncate.truncate_graph_polygon(G, poly, truncate_by_edge=True)
G = ox.simplify_graph(G)
ep = URL_PBF
log("grafo construido: %d nodos" % len(G))
comp = max(nx.weakly_connected_components(G), key=len)
G = G.subgraph(comp).copy()
log("LCC ok"); G = ox.project_graph(G, to_crs="EPSG:25831"); gc.collect(); log("proyectado")
nodes, edges = ox.graph_to_gdfs(G)
edges = edges.reset_index()
xy = nodes[["x", "y"]]
geoms = edges.geometry.copy()
miss = geoms.isna()
if miss.any():
    geoms[miss] = [LineString([(xy.at[u,"x"],xy.at[u,"y"]),(xy.at[v,"x"],xy.at[v,"y"])])
                   for u, v in zip(edges.u[miss], edges.v[miss])]
edges["geometry"] = geoms
edges["a"] = edges[["u","v"]].min(axis=1); edges["b"] = edges[["u","v"]].max(axis=1)
edges = edges[edges.a != edges.b].sort_values("length").drop_duplicates(["a","b"])
edges = edges.assign(u=edges.a.astype("int64"), v=edges.b.astype("int64"))
ar = gpd.GeoDataFrame(edges[["u","v","length"]].astype({"length":float}),
                      geometry=edges.geometry.values, crs=25831)
# nodos: solo los que quedan en alguna arista
ids = set(ar.u) | set(ar.v)
nd = pd.DataFrame({"node_id": nodes.index.astype("int64"), "x": nodes.x.astype(float).values, "y": nodes.y.astype(float).values})
nd = nd[nd.node_id.isin(ids)].reset_index(drop=True)
log("aristas listas"); nd.to_parquet(f_nod, index=False)
ar.to_file(f_ari, layer="aristas", driver="GPKG")
meta = dict(fecha_descarga=dt.date.today().isoformat(), fuente=ep, fecha_datos=fecha_osm, nodos=len(nd), aristas=len(ar),
            longitud_total_km=round(float(ar.length.sum())/1000, 1), area_municipio_km2=round(g.geometry.area.sum()/1e6,1))
f_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
print(meta, "segundos:", round(time.time()-t0))
