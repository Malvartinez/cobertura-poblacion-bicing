"""01 - Descarga y estandariza estaciones Bicing (GBFS) y limites de Barcelona (distritos, barrios)."""
import json, datetime as dt
from pathlib import Path
import requests, pandas as pd, geopandas as gpd
from shapely import wkt

ROOT = Path(__file__).resolve().parent.parent
RAW_B = ROOT / "data/raw/bicing"; RAW_L = ROOT / "data/raw/limites"; PROC = ROOT / "data/processed"
for p in (RAW_B, RAW_L, PROC): p.mkdir(parents=True, exist_ok=True)
CRS = "EPSG:25831"
HOY = dt.date.today().isoformat()
URL_GBFS = "https://barcelona-sp.publicbikesystem.net/customer/gbfs/v2/en/station_information"
# Open Data BCN, conjunto 20170706-districtes-barris. La descarga directa del CSV devuelve 403 a
# clientes automaticos; se lee el mismo recurso por la API datastore de CKAN.
API = "https://opendata-ajuntament.barcelona.cat/data/api/action/datastore_search"
RES_DIS, RES_BAR = "576bc645-9481-4bc4-b8bf-f5972c20df3f", "b21fa550-56ea-4f4c-9adc-b8009381896e"
URL_DATASET = "https://opendata-ajuntament.barcelona.cat/data/es/dataset/20170706-districtes-barris"

def get(url, **kw):
    r = requests.get(url, timeout=120, **kw); r.raise_for_status(); return r

# 1. Estaciones
existentes = sorted(RAW_B.glob("station_information_*.json"))
raw_f = existentes[-1] if existentes else RAW_B / f"station_information_{HOY}.json"
if not existentes: raw_f.write_bytes(get(URL_GBFS).content)
fecha_est = raw_f.stem.split("_")[-1]
st = pd.DataFrame(json.loads(raw_f.read_text(encoding="utf-8"))["data"]["stations"])
st = st.dropna(subset=["lat", "lon"]).drop_duplicates("station_id")
st = st[(st.lat != 0) & (st.lon != 0)]
if "is_virtual_station" in st: st = st[st.is_virtual_station != True]
bases = gpd.GeoDataFrame(
    {"base_id": st.station_id.astype(str), "nombre": st.name.astype(str).str.strip()},
    geometry=gpd.points_from_xy(st.lon, st.lat), crs="EPSG:4326").to_crs(CRS)
bases = bases.drop_duplicates(subset=["nombre", "geometry"])
bases.to_file(PROC / "bases.gpkg", layer="bases", driver="GPKG")

# 2. Limites (geometria_etrs89 = EPSG:25831)
def recurso(rid, name):
    f = RAW_L / f"{name}.json"
    if not f.exists():
        recs, off = [], 0
        while True:
            r = get(API, params={"resource_id": rid, "limit": 100, "offset": off}).json()["result"]["records"]
            recs += r; off += len(r)
            if len(r) < 100: break
        f.write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
    df = pd.DataFrame(json.loads(f.read_text(encoding="utf-8"))).rename(columns=str.lower)
    return gpd.GeoDataFrame(df, geometry=df.geometria_etrs89.map(wkt.loads), crs=CRS)

dis, bar = recurso(RES_DIS, "districtes"), recurso(RES_BAR, "barris")
cod = lambda s: pd.to_numeric(s).astype(int).astype(str).str.zfill(2)
distritos = gpd.GeoDataFrame({"cod_distrito": cod(dis.codi_districte), "nombre": dis.nom_districte},
    geometry=dis.geometry, crs=CRS).dissolve("cod_distrito", aggfunc="first").reset_index()
barrios = gpd.GeoDataFrame({"cod_barrio": cod(bar.codi_barri), "nombre": bar.nom_barri,
    "cod_distrito": cod(bar.codi_districte)}, geometry=bar.geometry, crs=CRS)
barrios = barrios.dissolve("cod_barrio", aggfunc="first").reset_index()[["cod_barrio", "nombre", "cod_distrito", "geometry"]]
distritos = distritos[["cod_distrito", "nombre", "geometry"]].sort_values("cod_distrito").reset_index(drop=True)
barrios = barrios.sort_values("cod_barrio").reset_index(drop=True)
muni = gpd.GeoDataFrame({"nombre": ["Barcelona"]}, geometry=[distritos.geometry.union_all()], crs=CRS)
distritos.to_file(PROC / "distritos.gpkg", layer="distritos", driver="GPKG")
barrios.to_file(PROC / "barrios.gpkg", layer="barrios", driver="GPKG")
muni.to_file(PROC / "municipio.gpkg", layer="municipio", driver="GPKG")

# 3. Metadatos
meta = {"fecha_descarga": HOY, "fecha_estaciones": fecha_est, "crs": CRS,
        "fuentes": {"bicing_gbfs_station_information": URL_GBFS, "distritos": URL_DATASET, "barrios": URL_DATASET},
        "n": {"bases": len(bases), "distritos": len(distritos), "barrios": len(barrios)}}
(PROC / "meta_bicing_limites.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
print(meta["n"], "bases dentro del municipio:", int(bases.within(muni.geometry.iloc[0]).sum()),
      "area km2:", round(muni.area.iloc[0] / 1e6, 1))
