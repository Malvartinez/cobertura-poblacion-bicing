import geopandas as gpd, pandas as pd, json, os, datetime
P = "data/processed/"; W = "web/data/"
def dump(gdf, path, dec=5):
    g = gdf.to_crs(4326).copy()
    g["geometry"] = g.geometry.set_precision(10 ** -dec)
    d = json.loads(g.to_json(drop_id=True, na="null", show_bbox=False))
    json.dump(d, open(path, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
ag = json.load(open(P + "agregados.json", encoding="utf-8"))
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pmtiles import escribir
CORTES = escribir(P, W + "edificios.pmtiles")
if os.path.exists(W + "edificios.geojson"): os.remove(W + "edificios.geojson")
dnames = {d["cod"]: d["nombre"] for d in ag["distritos"]}
FL = [p + k for p in ("",) for k in ("pob", "pob_v", "pob_a", "pob_r", "pct_v", "pct_a", "pct_r")]
def poly(layer, key, rows, tol, extra=()):
    g = gpd.read_file(P + layer + ".gpkg")
    g["cod"] = g[key]
    if "nombre" not in g: g["nombre"] = None
    df = pd.DataFrame(rows).set_index("cod")[FL]
    g = g.join(df, on="cod")
    for c in FL:
        g[c] = g[c].fillna(0.0) if "pct" in c else g[c].fillna(0).astype(int)
    if "distrito" in extra: g["distrito"] = g.cod_distrito.map(dnames)
    g = g[["cod", "nombre"] + list(extra) + FL + ["geometry"]].copy()
    g["geometry"] = g.geometry.simplify(tol, preserve_topology=True)
    return g
dump(poly("secciones", "cusec", ag["secciones"], 5), W + "secciones.geojson")
dump(poly("barrios", "cod_barrio", ag["barrios"], 10, ("cod_distrito", "distrito")), W + "barrios.geojson")
dump(poly("distritos", "cod_distrito", ag["distritos"], 10), W + "distritos.geojson")
dump(gpd.read_file(P + "bases.gpkg", layer="bases")[["base_id", "nombre", "geometry"]], W + "bases.geojson")  # solo base_id/nombre; 07_ranking_bases.py (tras 06) lo reescribe con el ranking
strip = lambda o: {k: v for k, v in o.items() if not k.startswith(("a_", "m_"))}
json.dump({"ciudad": strip(ag["ciudad"]), "distritos": [strip(x) for x in ag["distritos"]], "barrios": [strip(x) for x in ag["barrios"]]}, open(W + "agregados.json", "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
m = lambda f: json.load(open(P + f, encoding="utf-8"))
bl, ine, cat = m("meta_bicing_limites.json"), m("meta_ine.json"), m("meta_catastro.json")
try: osm = m("meta_osm.json")
except Exception: osm = {}
f = bl["fuentes"]
hoy = datetime.date.today().isoformat()
fu = [
 {"nombre": "Bicing GBFS station_information", "url": f["bicing_gbfs_station_information"], "fecha_descarga": bl["fecha_descarga"], "referencia": bl.get("fecha_estaciones")},
 {"nombre": "Límites administrativos (distritos y barrios), Ajuntament de Barcelona (Open Data BCN)", "url": f["distritos"], "fecha_descarga": bl["fecha_descarga"], "referencia": "vigente en la descarga"},
 {"nombre": "INE cartografía de secciones censales", "url": ine["cartografia_url"], "fecha_descarga": ine["fecha_descarga"], "referencia": str(ine["cartografia_anio"])},
 {"nombre": ine["poblacion_fuente"], "url": ine["poblacion_url"], "fecha_descarga": ine["fecha_descarga"], "referencia": str(ine["poblacion_anio_referencia"][0])},
 {"nombre": "Catastro INSPIRE Buildings", "url": cat["url"], "fecha_descarga": cat["fecha_descarga"], "referencia": cat["fecha_datos"][:10]},
 {"nombre": "OpenStreetMap (red viaria peatonal)", "url": "https://www.openstreetmap.org", "fecha_descarga": osm.get("fecha_descarga", hoy), "referencia": str(osm.get("fecha_datos", osm.get("referencia", "fecha de descarga")))}]
json.dump({"generado": hoy, "cortes_poblacion_edificio": CORTES, "parametros": {"umbral_verde": 250, "umbral_amarillo": 500, "corte": 1500}, "fuentes": fu},
          open(W + "metadata.json", "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
for n in sorted(os.listdir(W)): print(n, round(os.path.getsize(W + n) / 1e6, 2), "MB")
