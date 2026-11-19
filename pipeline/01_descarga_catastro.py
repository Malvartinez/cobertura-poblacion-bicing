"""Descarga Catastro INSPIRE Buildings (Barcelona, 08900) y genera data/processed/edificios.gpkg."""
import datetime as dt, json, re, zipfile
from pathlib import Path
import geopandas as gpd, pandas as pd, requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/catastro"; OUT = ROOT / "data/processed"
RAW.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
FEED = "https://www.catastro.hacienda.gob.es/INSPIRE/buildings/08/ES.SDGC.bu.atom_08.xml"
URL = "https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/08/08900-BARCELONA/A.ES.SDGC.BU.08900.zip"
ZIP = RAW / "A.ES.SDGC.BU.08900.zip"; GML = "A.ES.SDGC.BU.08900.building.gml"

# fecha de actualizacion del dataset segun el feed
feed = requests.get(FEED, timeout=60).text
m = re.search(r"08900-BARCELONA buildings.*?<updated>([^<]+)</updated>", feed, re.S)
data_date = m.group(1) if m else None

if not ZIP.exists():
    with requests.get(URL, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(ZIP, "wb") as f:
            for c in r.iter_content(1 << 20): f.write(c)
if not (RAW / GML).exists():
    zipfile.ZipFile(ZIP).extract(GML, RAW)

g = gpd.read_file(RAW / GML, engine="pyogrio",
                  columns=["localId", "currentUse", "numberOfDwellings", "numberOfBuildingUnits"])
if g.crs is None or g.crs.to_epsg() != 25831:
    g = g.to_crs(25831)
g = g[g.geometry.notna() & ~g.geometry.is_empty]
out = gpd.GeoDataFrame({
    "edif_id": g["localId"].astype(str),
    "uso": g["currentUse"].astype("string").astype(object),
    "n_viviendas": pd.to_numeric(g["numberOfDwellings"], errors="coerce").fillna(0).astype(int),
    "n_unidades": pd.to_numeric(g["numberOfBuildingUnits"], errors="coerce").fillna(0).astype(int),
}, geometry=g.geometry, crs=25831)
out.to_file(OUT / "edificios.gpkg", layer="edificios", driver="GPKG")
json.dump({"fuente": "Catastro INSPIRE Buildings (ATOM), municipio 08900 BARCELONA", "url": URL,
           "feed": FEED, "fecha_datos": data_date,
           "fecha_descarga": dt.date.today().isoformat(), "crs": "EPSG:25831",
           "n_edificios": len(out)}, open(OUT / "meta_catastro.json", "w"), indent=2)
print("total", len(out), "| residential", (out.uso == "1_residential").sum(),
      "| viv>0", (out.n_viviendas > 0).sum(), "| sum viv", out.n_viviendas.sum())
print(out.uso.value_counts(dropna=False).to_string())
