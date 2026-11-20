"""01 - Portales de los edificios (Catastro INSPIRE Addresses) y arista de la red por la que se accede a cada uno.

El Catastro publica, por municipio, cada direccion con su punto. Las de tipo `Entrance` son el portal, situado sobre
la fachada que da a la calle de la direccion. Con ellas la distancia de un edificio se mide desde su portal y no
desde cualquier calle que lo bordee (ver _acceso.py).

Arista de acceso de cada portal: la mas cercana. Si esa arista tiene nombre y es OTRA calle (portal en una esquina) y
hay a <= R_NOMBRE m una arista de la calle de la direccion, se usa esta. Las aristas sin nombre (aceras, sendas) se
aceptan tal cual: suelen ser la acera de la propia fachada.

Mismo paso que en cobertura-bici-publica-espana (pipeline/01_direcciones.py), municipio 08900-BARCELONA.
Si falta data/raw/osm/red_walk.osm (se genera en 01_descarga_osm) no se corrigen esquinas por nombre.
Salida: portales.parquet (refcat, x, y, via, numero, arista, d_arista) y meta_direcciones.json."""
import datetime as dt, html, json, re, time, unicodedata, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, shapely, requests
from shapely import STRtree

ROOT = Path(__file__).resolve().parents[1]
P = str(ROOT / "data/processed") + "/"; RAW = ROOT / "data/raw"
CRS = EPSG = gpd.read_file(P + "red_aristas.gpkg", layer="aristas", rows=1).crs.to_epsg()  # 25830 Madrid, 25831 Barcelona
C = {"tipo": "nacional", "codigo": "08900-BARCELONA"}

def get(url, intentos=6, stream_to=None):
    for i in range(intentos):
        try:
            if stream_to:
                tmp = Path(str(stream_to) + ".part")
                with requests.get(url, stream=True, timeout=900) as r:
                    r.raise_for_status()
                    with open(tmp, "wb") as f:
                        for c in r.iter_content(1 << 20): f.write(c)
                tmp.replace(stream_to); return stream_to
            r = requests.get(url, timeout=300); r.raise_for_status(); return r
        except Exception as e:
            if i == intentos - 1: raise
            print("reintento", i + 1, url, repr(e)[:120], flush=True); time.sleep(5 * (i + 1))

R_NOMBRE = 40.0
OUT = P + "portales.parquet"; META = P + "meta_direcciones.json"
RC = RAW / "catastro"; RC.mkdir(exist_ok=True)
num = C["codigo"][:5]; pr = num[:2]
FEED = f"https://www.catastro.hacienda.gob.es/INSPIRE/addresses/{pr}/ES.SDGC.ad.atom_{pr}.xml"
fecha_datos = None
try:
    raw = get(FEED).content
    try: feed = raw.decode("utf-8")
    except UnicodeDecodeError: feed = raw.decode("latin-1")
    ent = [e for e in feed.split("<entry>") if re.search(rf"<title>\s*{num}-", e)]
except Exception as e:
    print("aviso: feed no disponible", e); ent = []
if ent:
    m = re.search(r'rel="enclosure"[^>]*href="([^"]+)"', ent[0]) or re.search(r'href="([^"]+\.zip)"', ent[0])
    URL = html.unescape(m.group(1))
    m = re.search(r"<updated>([^<]+)</updated>", ent[0]); fecha_datos = m.group(1) if m else None
else:
    print("aviso:", num, "no aparece en el feed; se usa la ruta directa")
    URL = f"https://www.catastro.hacienda.gob.es/INSPIRE/Addresses/{pr}/{C['codigo']}/A.ES.SDGC.AD.{num}.zip"
ZIP = RC / f"A.ES.SDGC.AD.{num}.zip"; GML = f"A.ES.SDGC.AD.{num}.gml"
if ZIP.exists() and not zipfile.is_zipfile(ZIP): ZIP.unlink()
if not ZIP.exists():
    get(URL, stream_to=ZIP)
    if not zipfile.is_zipfile(ZIP): raise SystemExit(f"La descarga no es un ZIP: {URL}")
if not (RC / GML).exists(): zipfile.ZipFile(ZIP).extract(GML, RC)

# --- lectura del GML (ISO-8859-1): direcciones y nombres de via
txt = (RC / GML).read_bytes().decode("latin-1")
srs = re.search(r'srsName="urn:ogc:def:crs:EPSG::(\d+)"', txt).group(1)
tn = dict(re.findall(r'<AD:ThoroughfareName gml:id="([^"]+)">.*?<GN:text>([^<]*)</GN:text>', txt, flags=re.S))
rows = []
for m in re.finditer(r'<AD:Address gml:id="[^"]+">(.*?)</AD:Address>', txt, flags=re.S):
    b = m.group(1)
    if "<AD:specification>Entrance<" not in b: continue  # Parcel = punto de parcela, no de portal
    lid = re.search(r"<base:localId>([^<]+)", b).group(1)
    x, y = map(float, re.search(r"<gml:pos>\s*([-\d.]+)\s+([-\d.]+)", b).group(1, 2))
    t = re.search(r'xlink:href="#(ES\.SDGC\.TN\.[^"]+)"', b)
    nu = re.search(r"<AD:LocatorDesignator>\s*<AD:designator>([^<]*)", b)
    rows.append((lid[-14:], x, y, tn.get(t.group(1), "").strip() if t else "", nu.group(1) if nu else ""))
del txt
pt = pd.DataFrame(rows, columns=["refcat", "x", "y", "via", "numero"])
g = gpd.GeoSeries(shapely.points(pt.x.values, pt.y.values), crs=f"EPSG:{srs}").to_crs(CRS)
pt["x"], pt["y"] = g.x.values, g.y.values
print("portales (Entrance):", len(pt))

# --- nombres de las aristas: via OSM con nombre que pasa por el punto medio de la arista
ed = gpd.read_file(P + "red_aristas.gpkg", layer="aristas")
coords, lines, names = {}, [], []
XML = RAW / "osm" / "red_walk.osm"
if not XML.exists(): print("aviso: falta", XML, "- sin correccion de esquinas por nombre")
for ev, el in (ET.iterparse(str(XML)) if XML.exists() else []):
    if el.tag == "node": coords[el.get("id")] = (float(el.get("lon")), float(el.get("lat")))
    elif el.tag == "way":
        nm = [t.get("v") for t in el.findall("tag") if t.get("k") == "name"]
        if nm:
            ps = [coords[n.get("ref")] for n in el.findall("nd") if n.get("ref") in coords]
            if len(ps) > 1: lines.append(shapely.LineString(ps)); names.append(nm[0])
        el.clear()
del coords
enom = np.full(len(ed), "", dtype=object)
if lines:
    wl = gpd.GeoSeries(lines, crs=4326).to_crs(EPSG).values
    mid = shapely.line_interpolate_point(ed.geometry.values, 0.5, normalized=True)
    qi = STRtree(wl).query_nearest(mid, max_distance=1.0, all_matches=False)
    enom[qi[0]] = np.array(names, dtype=object)[qi[1]]

TIPOS = set(("calle cl carrer c avenida av avda avinguda paseo ps pseo passeig pg plaza pl pz placa plazuela travesia tr "
             "travessera ronda rd camino cm cami carretera ctra cr glorieta gl pasaje pj psje passatge via vi callejon cj "
             "urbanizacion ur barrio bo poligono costanilla cuesta cu calleja senda sd rambla rb rua r rua kalea k "
             "etorbidea pasealekua plazuela").split())
STOP = set("de del la las el los y d l a en dels i do da das dos".split())
def toks(s, cat=False):
    s = unicodedata.normalize("NFKD", s.lower()); s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\([^)]*\)", " ", s)  # sufijo de barrio del Catastro: "(JSL)"
    if cat and "," in s: a, b = s.split(",", 1); s = b + " " + a  # "CL ABANTO, MARTIN DE"
    t = re.findall(r"[a-z0-9]+", s)
    if t and t[0] in TIPOS: t = t[1:]
    return frozenset(x for x in t if x not in STOP and x not in TIPOS)
def casa(s, t): return bool(s) and bool(t) and (s <= t or t <= s or len(s & t) / len(s | t) >= 0.5)
etok = np.array([toks(n) if n else frozenset() for n in enom], dtype=object)
ptok = [toks(v, cat=True) for v in pt.via.values]

pp = shapely.points(pt.x.values, pt.y.values); eg = ed.geometry.values
tr = STRtree(eg)
qi, qd = tr.query_nearest(pp, return_distance=True, all_matches=False)
ar = np.empty(len(pt), dtype=np.int64); ar[qi[0]] = qi[1]
da = np.empty(len(pt)); da[qi[0]] = qd
otra = np.array([bool(etok[e]) and not casa(ptok[i], etok[e]) for i, e in enumerate(ar)])
a, b = tr.query(shapely.buffer(pp[otra], R_NOMBRE), predicate="intersects")
cand = pd.DataFrame({"p": np.flatnonzero(otra)[a], "e": b})
cand["d"] = shapely.distance(pp[cand.p.values], eg[cand.e.values])
cand = cand[(cand.d.values <= R_NOMBRE) & np.array([casa(ptok[p], etok[e]) for p, e in zip(cand.p.values, cand.e.values)], dtype=bool)]
cand = cand.sort_values("d").drop_duplicates("p")
ar[cand.p.values] = cand.e.values; da[cand.p.values] = cand.d.values
pt["arista"] = ar; pt["d_arista"] = da
pt.to_parquet(OUT, index=False)
mas = float(np.mean([casa(ptok[i], etok[e]) for i, e in enumerate(ar)]))
json.dump({"fuente": f"Catastro INSPIRE Addresses (DG del Catastro), municipio {C['codigo']}", "url": URL,
           "fecha_datos": fecha_datos, "fecha_descarga": dt.date.today().isoformat(), "n_portales": len(pt),
           "aristas_con_nombre": round(float((enom != "").mean()), 3), "portales_corregidos_por_nombre": int(len(cand)),
           "portales_en_arista_de_su_calle": round(mas, 3)},
          open(META, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"aristas con nombre {np.mean(enom != ''):.1%} | portales en arista de su calle {mas:.1%} | corregidos por nombre "
      f"(esquinas) {len(cand)} | distancia portal-arista p50 {np.median(da):.1f} m p90 {np.percentile(da, 90):.1f} m")
