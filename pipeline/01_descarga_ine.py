"""Descarga y estandariza secciones censales (INE 2025) y poblacion por seccion de Barcelona (08019). Idempotente."""
import io, json, zipfile, datetime, pathlib, requests, pandas as pd, geopandas as gpd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/ine"; PROC = ROOT / "data/processed"
RAW.mkdir(parents=True, exist_ok=True); PROC.mkdir(parents=True, exist_ok=True)
MUN = "08019"
URL_CART = "https://www.ine.es/prodyser/cartografia/seccionado_2025.zip"
URL_POB = "https://services1.arcgis.com/nCKYwcSONQTkPA4K/arcgis/rest/services/SeccionCensal25Continua_Spain/FeatureServer/0/query"
URL_ITEM = "https://www.arcgis.com/home/item.html?id=304cb4fe00f14ebca73e762ba2e02d7e"

# 1. Cartografia
zpath = RAW / "seccionado_2025.zip"
if not zpath.exists():
    zpath.write_bytes(requests.get(URL_CART, timeout=600).content)
ext = RAW / "seccionado_2025"
if not ext.exists():
    zipfile.ZipFile(zpath).extractall(ext)
shp = next(ext.rglob("*.shp"))
g = gpd.read_file(shp)
g = g[g.CUMUN == MUN].to_crs(25831)
sec = gpd.GeoDataFrame({"cusec": g.CUSEC.astype(str), "cod_distrito": g.CDIS.astype(str).str.zfill(2),
                        "cod_seccion": g.CSEC.astype(str).str.zfill(3)}, geometry=g.geometry.values, crs=25831)
sec.to_file(PROC / "secciones.gpkg", layer="secciones", driver="GPKG")

# 2. Poblacion 2025 por grupos de edad (Censo anual de poblacion 2025, servicio Esri Espana)
jpath = RAW / "censo2025_seccion_08019.json"
if not jpath.exists():
    feats, off = [], 0
    while True:
        r = requests.get(URL_POB, params={"where": f"Cod_MUN='{MUN}'", "outFields": "*", "returnGeometry": "false",
                                          "f": "json", "resultOffset": off, "resultRecordCount": 2000, "orderByFields": "Codigo"}, timeout=300).json()
        f = r["features"]; feats += f; off += len(f)
        if not f or not r.get("exceededTransferLimit"): break
    jpath.write_text(json.dumps(feats, ensure_ascii=False), encoding="utf-8")
feats = json.loads(jpath.read_text(encoding="utf-8"))
df = pd.DataFrame([x["attributes"] for x in feats])
ed = lambda a: [f"De_{i}_a_{i+4}_años" for i in range(a[0], a[1], 5)]
c1564 = ed((15, 65)); c65 = ed((65, 100)) + ["De_100_y_mas_años"]
pob = pd.DataFrame({"cusec": df.Codigo.astype(str), "poblacion": df.Total.astype(int),
                    "pob_15_64": df[c1564].sum(axis=1).astype(int), "pob_65": df[c65].sum(axis=1).astype(int)}).drop_duplicates("cusec")
years = {int(x) for x in df.FechaId.unique()}
pob.to_parquet(PROC / "poblacion_secciones.parquet", index=False)

a, b = set(pob.cusec), set(sec.cusec)
print(f"secciones={len(sec)} pob_filas={len(pob)} total={pob.poblacion.sum()} 15-64={pob.pob_15_64.sum()} 65+={pob.pob_65.sum()} fecha={years}")
print(f"cusec en pob sin cartografia={len(a-b)}; en cartografia sin pob={len(b-a)}")
(PROC / "meta_ine.json").write_text(json.dumps({
    "cartografia_url": URL_CART, "cartografia_anio": 2025,
    "poblacion_url": URL_ITEM, "poblacion_fuente": "INE, Censo anual de población 2025 por sección censal (servicio de Esri España)",
    "poblacion_anio_referencia": ["1 ene 2025"], "n_secciones": len(sec), "poblacion_total": int(pob.poblacion.sum()),
    "fecha_descarga": datetime.date.today().isoformat()}, indent=2, ensure_ascii=False), encoding="utf-8")
