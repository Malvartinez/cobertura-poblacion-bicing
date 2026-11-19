# Ranking de estaciones: poblacion que vive a <250 m (p250) y 250-500 m (p500) de CADA estacion por red,
# con solapes (una persona cuenta para todas las estaciones a su alcance). Se ejecuta DESPUES de 06
# y reescribe web/data/bases.geojson (06 solo lo crea con base_id/nombre).
import geopandas as gpd, pandas as pd, numpy as np, scipy.sparse as sp, json, time, shapely
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from shapely import STRtree
P = "data/processed/"; W = "web/data/"; t0 = time.time()
nod = pd.read_parquet(P + "red_nodos.parquet")
ed = gpd.read_file(P + "red_aristas.gpkg", layer="aristas")
bas = gpd.read_file(P + "bases.gpkg", layer="bases").reset_index(drop=True)
bld = gpd.read_parquet(P + "edificios_distancias.parquet")
N = len(nod); idx = pd.Series(np.arange(N), index=nod.node_id.values)
nx_, ny_ = nod.x.values, nod.y.values
U = idx[ed.u.values].values; V = idx[ed.v.values].values
L = np.maximum(ed.length.values.astype(float), 1e-6)
S = len(bas)
tree = cKDTree(np.c_[nx_, ny_])
sd, sn = tree.query(np.c_[bas.geometry.x, bas.geometry.y]); sd = np.maximum(sd, 1e-6)
# grafo sin nodos virtuales (evita atajos entre estaciones); distancia = sd + D[desde nodo enganchado]
G = sp.coo_matrix((L, (U, V)), shape=(N, N)).tocsr()
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# opciones de acceso de cada edificio (identicas a 04)
from _acceso import accesos, minimo
ob, on, oo, ini, dp = accesos(P, bld, ed, U, V, L, nx_, ny_)
pop = bld.poblacion.fillna(0).values.astype(float)
nb = len(bld)
p250 = np.zeros(S); p500 = np.zeros(S)
mind = np.full(nb, np.inf)
BATCH = 25
for i0 in range(0, S, BATCH):
    ids = np.arange(i0, min(S, i0 + BATCH))
    D = dijkstra(G, directed=False, indices=sn[ids], limit=501)  # (B, N)
    D = D + sd[ids][:, None]
    tot = minimo(D[:, on] + oo[None, :], ini)
    tot[~np.isfinite(tot)] = np.inf
    mind = np.minimum(mind, tot.min(axis=0))
    p250[ids] = ((tot < 250) * pop[None, :]).sum(axis=1)
    p500[ids] = (((tot >= 250) & (tot <= 500)) * pop[None, :]).sum(axis=1)
    del D, tot
    if (i0 // BATCH) % 5 == 0: print("batch", i0, round(time.time() - t0), "s", flush=True)
# checks
d04 = bld.distancia.values.astype(float); d04 = np.where(np.isnan(d04), np.inf, d04)
rel = (mind <= 500) | (d04 <= 500)
both_inf = np.isinf(mind) & np.isinf(d04)
bad = rel & ~(np.abs(np.where(np.isinf(mind), 1e9, mind) - np.where(np.isinf(d04), 1e9, d04)) <= 1e-6)
print("CHECK1 edificios comparados:", int(rel.sum()), "discrepancias:", int(bad.sum()))
if bad.any(): print(pd.DataFrame({"mind": mind[bad], "d04": d04[bad]}).head(10))
verde = pop[mind < 250].sum()
ag = json.load(open(P + "agregados.json", encoding="utf-8"))
print("CHECK2 pob con alguna estacion <250:", round(verde), "agregados pob_v:", ag["ciudad"]["pob_v"], "dif:", round(verde - ag["ciudad"]["pob_v"], 2))
# cercanas
bid = bld.base_id.values
pc = pd.DataFrame({"base_id": bid, "n": bld.nivel.values, "p": pop}).dropna(subset=["base_id"])
c250 = pc[pc.n == 0].groupby("base_id").p.sum(); c500 = pc[pc.n == 1].groupby("base_id").p.sum()
# distrito / barrio
bp = bas[["base_id", "nombre", "geometry"]].copy()
for nm, f in (("distrito", "distritos"), ("barrio", "barrios")):
    pl = gpd.read_file(P + f + ".gpkg")[["nombre", "geometry"]].rename(columns={"nombre": nm})
    j = gpd.sjoin(bp[["base_id", "geometry"]], pl, how="left", predicate="within")
    j = j[~j.base_id.duplicated()].set_index("base_id")[nm]
    bp[nm] = bp.base_id.map(j).where(lambda s: s.notna(), None)
bp["p250"] = np.round(p250).astype(int); bp["p500"] = np.round(p500).astype(int)
bp["p250_cercana"] = np.round(bp.base_id.map(c250).fillna(0)).astype(int)
bp["p500_cercana"] = np.round(bp.base_id.map(c500).fillna(0)).astype(int)
cols = ["base_id", "nombre", "distrito", "barrio", "p250", "p500", "p250_cercana", "p500_cercana"]
pd.DataFrame(bp[cols]).to_parquet(P + "ranking_bases.parquet")
g = bp[cols + ["geometry"]].to_crs(4326).copy()
g["geometry"] = g.geometry.set_precision(1e-5)
d = json.loads(g.to_json(drop_id=True, na="null", show_bbox=False))
json.dump(d, open(W + "bases.geojson", "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
for k in ("p250", "p500"):
    print("TOP", k); print(bp.nlargest(5, k)[["nombre", "distrito", k]].to_string(index=False))
print("p250=0:", int((bp.p250 == 0).sum()), "p500=0 y p250=0:", int(((bp.p250 == 0) & (bp.p500 == 0)).sum()))
import os; print("bases.geojson KB", round(os.path.getsize(W + "bases.geojson") / 1e3), "parquet KB", round(os.path.getsize(P + "ranking_bases.parquet") / 1e3), "t", round(time.time() - t0), "s")
