import geopandas as gpd, pandas as pd, numpy as np, scipy.sparse as sp, networkx as nx, time, shapely
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from shapely import STRtree
P = "data/processed/"; t0 = time.time()
nod = pd.read_parquet(P + "red_nodos.parquet")
ed = gpd.read_file(P + "red_aristas.gpkg", layer="aristas")
bas = gpd.read_file(P + "bases.gpkg", layer="bases").reset_index(drop=True)
bld = gpd.read_parquet(P + "edificios_poblacion.parquet")
N = len(nod); idx = pd.Series(np.arange(N), index=nod.node_id.values)
nx_, ny_ = nod.x.values, nod.y.values
U = idx[ed.u.values].values; V = idx[ed.v.values].values
L = np.maximum(ed.length.values.astype(float), 1e-6)  # scipy ignora ceros explicitos
S = len(bas)
tree = cKDTree(np.c_[nx_, ny_])
sd, sn = tree.query(np.c_[bas.geometry.x, bas.geometry.y])
big = int((sd > 150).sum())
print("estaciones con snap >150m:", big, bas.nombre[sd > 150].tolist()[:10])
sd = np.maximum(sd, 1e-6)
vs = N + np.arange(S)
G = sp.coo_matrix((np.r_[L, sd], (np.r_[U, vs], np.r_[V, sn])), shape=(N + S, N + S)).tocsr()
D, pred, src = dijkstra(G, directed=False, indices=vs, min_only=True, limit=1600, return_predecessors=True)
D = D[:N]; src = src[:N]  # src: indice del nodo virtual de origen
# edificios
geoms = ed.geometry.values; stree = STRtree(geoms)
pts = bld.geometry.values
qi, dist = stree.query_nearest(pts, return_distance=True, all_matches=False)
eg = np.empty(len(pts), dtype=int); eg[qi[0]] = qi[1]
dp = np.empty(len(pts)); dp[qi[0]] = dist
line = geoms[eg]; ln = shapely.length(line)
proj = shapely.line_locate_point(line, pts)
t = np.where(ln > 0, proj / ln, 0)
st = shapely.get_point(line, 0)
sx, sy = shapely.get_x(st), shapely.get_y(st)
u = U[eg]; v = V[eg]; Le = L[eg]
du = np.hypot(nx_[u] - sx, ny_[u] - sy); dv = np.hypot(nx_[v] - sx, ny_[v] - sy)
start = np.where(du <= dv, u, v); end = np.where(du <= dv, v, u)
a = t * Le; b = (1 - t) * Le
ds = D[start] + a; de = D[end] + b
us = ds <= de
tot = dp + np.where(us, ds, de)
s_ = src[np.where(us, start, end)]
ok = np.isfinite(tot) & (tot <= 1500) & (s_ >= N)
dist_f = np.where(ok, tot, np.nan)
bi = np.where(ok, s_ - N, -1)
out = bld.copy()
out["distancia"] = dist_f
out["base_id"] = [bas.base_id.iloc[i] if i >= 0 else None for i in bi]
out["base_nombre"] = [bas.nombre.iloc[i] if i >= 0 else None for i in bi]
out["nivel"] = np.where(np.isnan(dist_f), 2, np.where(dist_f < 250, 0, np.where(dist_f <= 500, 1, 2))).astype(int)
out["d_perp"] = dp
out.to_parquet(P + "edificios_distancias.parquet")
nfar = int((~ok).sum()); print("edificios sin base <=1500m:", nfar, "nivel:", out.nivel.value_counts().to_dict())
# validacion independiente con networkx
rng = np.random.default_rng(42)
sm = rng.choice(np.where(ok)[0], 50, replace=False)
g = nx.Graph()
for uu, vv, ll in zip(ed.u.values, ed.v.values, ed.length.values):
    if not g.has_edge(uu, vv) or g[uu][vv]["weight"] > ll: g.add_edge(uu, vv, weight=float(ll))
nid = nod.node_id.values
for j in range(S): g.add_edge(("S", j), int(nid[sn[j]]), weight=float(sd[j]))
errs = []
for i in sm:
    g.add_edge("B", int(nid[start[i]]), weight=float(dp[i] + a[i]))
    g.add_edge("B", int(nid[end[i]]), weight=float(dp[i] + b[i]))
    dd = nx.single_source_dijkstra_path_length(g, "B", cutoff=3000)
    ref = min(dd.get(("S", j), np.inf) for j in range(S))
    errs.append(abs(ref - dist_f[i]) / ref)
    g.remove_node("B")
errs = np.array(errs); n_ok = int((errs <= 0.05).sum())
print("validacion", n_ok, "/50 max err", errs.max())
open("docs/validacion_distancias.md", "w", encoding="utf-8").write(f"""# Validacion de distancias

Muestra aleatoria de 50 edificios (semilla 42) con distancia finita; ruta individual recalculada con networkx (Dijkstra desde un nodo temporal del edificio hacia los nodos virtuales de estaciones, mismas aristas y pesos de enganche).

- Coinciden dentro del 5 %: **{n_ok}/50**
- Error relativo maximo: **{errs.max()*100:.4f} %**
- Estaciones con snap > 150 m: {big}
- Edificios sin base a <= 1500 m: {nfar}
""")
print("t", time.time() - t0)
