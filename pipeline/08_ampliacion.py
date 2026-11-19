# Ampliacion optima: hasta KMAX (500) nuevas estaciones elegidas con greedy (CELF) por mejora ponderada de cobertura.
# Reanudable: candidatos, cobertura por chunks y resultado del greedy se guardan en data/processed/.
import geopandas as gpd, pandas as pd, numpy as np, scipy.sparse as sp, json, time, os, heapq, pickle, shapely, sys
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from shapely import STRtree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
P = "data/processed/"; W = "web/data/"; t0 = time.time(); KMAX = 500; CHUNK = 2000; BATCH = 25
def log(*a): print(*a, round(time.time() - t0), "s", flush=True)
def atomic(path, writer, mode="wb"):
    tmp = path + ".tmp"
    with open(tmp, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f: writer(f)
    os.replace(tmp, path)
def jwrite(path, obj): atomic(path, lambda f: f.write(json.dumps(obj, separators=(",", ":"), ensure_ascii=False)), "w")
nod = pd.read_parquet(P + "red_nodos.parquet")
ed = gpd.read_file(P + "red_aristas.gpkg", layer="aristas")
bas = gpd.read_file(P + "bases.gpkg", layer="bases").reset_index(drop=True)
bld = gpd.read_parquet(P + "edificios_distancias.parquet")
N = len(nod); idx = pd.Series(np.arange(N), index=nod.node_id.values)
nx_, ny_ = nod.x.values, nod.y.values
U = idx[ed.u.values].values; V = idx[ed.v.values].values
L = np.maximum(ed.length.values.astype(float), 1e-6)
S = len(bas); nb = len(bld)
tree = cKDTree(np.c_[nx_, ny_])
sd, sn = tree.query(np.c_[bas.geometry.x, bas.geometry.y]); sd = np.maximum(sd, 1e-6)
# opciones de acceso de cada edificio (identicas a 04)
from _acceso import accesos, minimo
ob, on, oo, ini, dp = accesos(P, bld, ed, U, V, L, nx_, ny_)
pop = bld.poblacion.fillna(0).values.astype(float)
L0 = bld.nivel.values.astype(np.int8)
R = np.where(L0 > 0)[0]  # edificios que pueden mejorar
log("edificios", nb, "mejorables", len(R))
# --- candidatos ---
cf = P + "ampliacion_candidatos.npz"
if not os.path.exists(cf):
    mun = gpd.read_file(P + "municipio.gpkg").geometry.union_all()
    shapely.prepare(mun)
    ins = shapely.contains_xy(mun, nx_, ny_)
    ci = np.where(ins)[0]
    gx = np.floor(nx_[ci] / 50).astype(np.int64); gy = np.floor(ny_[ci] / 50).astype(np.int64)
    dc = np.hypot(nx_[ci] - (gx + .5) * 50, ny_[ci] - (gy + .5) * 50)
    o = np.lexsort((dc, gy, gx)); key = gx[o] * 10_000_000 + gy[o]
    first = np.r_[True, key[1:] != key[:-1]]
    cand = np.sort(ci[o[first]])
    atomic(cf, lambda f: np.savez(f, cand=cand))
    log("nodos en municipio", len(ci), "candidatos por celda 50 m", len(cand))
cand = np.load(cf)["cand"]
# --- cobertura por candidato (CSR por chunks) ---
G = sp.coo_matrix((L, (U, V)), shape=(N, N)).tocsr()
mR = np.isin(ob, R); onR, ooR, obR = on[mR], oo[mR], ob[mR]
iniR = np.r_[0, np.flatnonzero(np.diff(obR)) + 1]; assert len(iniR) == len(R)
nch = (len(cand) + CHUNK - 1) // CHUNK
for ch in range(nch):
    f = P + f"ampliacion_cobertura_{ch:03d}.npz"
    if os.path.exists(f): continue
    cs = cand[ch * CHUNK:(ch + 1) * CHUNK]; ptr = [0]; BI = []; LV = []
    for i0 in range(0, len(cs), BATCH):
        D = dijkstra(G, directed=False, indices=cs[i0:i0 + BATCH], limit=501)
        tot = minimo(D[:, onR] + ooR[None, :], iniR)
        del D
        for row in tot:
            j = np.where(row <= 500)[0]
            BI.append(R[j].astype(np.int32)); LV.append((row[j] >= 250).astype(np.int8)); ptr.append(ptr[-1] + len(j))
        del tot
    ptr = np.array(ptr, dtype=np.int64)
    atomic(f, lambda fh: np.savez(fh, ptr=ptr, bi=np.concatenate(BI), lv=np.concatenate(LV)))
    log("chunk", ch + 1, "/", nch)
ptrs = []; BIs = []; LVs = []; off = 0
for ch in range(nch):
    z = np.load(P + f"ampliacion_cobertura_{ch:03d}.npz")
    ptrs.append(z["ptr"][:-1] + off); off += int(z["ptr"][-1]); BIs.append(z["bi"]); LVs.append(z["lv"])
ptr = np.r_[np.concatenate(ptrs), off]; BI = np.concatenate(BIs); LV = np.concatenate(LVs)
log("candidatos", len(cand), "pares totales", len(BI))
# --- greedy CELF ---
rf = P + "ampliacion_resultado.pkl"
if os.path.exists(rf):
    res = pickle.load(open(rf, "rb"))
else:
    Lc = L0.copy()
    def gain(c):
        s, e = ptr[c], ptr[c + 1]; bi = BI[s:e]
        return float((pop[bi] * np.maximum(0, Lc[bi] - LV[s:e])).sum())
    heap = []
    for c in range(len(cand)):
        g = gain(c)
        if g > 0: heap.append((-g, c, 0))
    heapq.heapify(heap)
    tv = [pop[Lc == 0].sum()]; ta = [pop[Lc == 1].sum()]; tr = [pop[Lc == 2].sum()]
    kv = np.full(nb, -1, np.int32); ka = np.full(nb, -1, np.int32)
    picks = []; r = 0
    while r < KMAX and heap:
        ng, c, stamp = heapq.heappop(heap)
        if stamp != r:
            g = gain(c)
            if g > 0: heapq.heappush(heap, (-g, c, r))
            continue
        r += 1; s, e = ptr[c], ptr[c + 1]; bi = BI[s:e]; lv = LV[s:e]
        old = Lc[bi].copy(); new = np.minimum(old, lv); ch_ = new < old; bi, old, new = bi[ch_], old[ch_], new[ch_]
        Lc[bi] = new
        nv = new == 0; kv[bi[nv]] = r
        na = (old == 2); ka[bi[na]] = r
        gv = pop[bi[nv]].sum(); gr = pop[bi[na]].sum()
        picks.append((int(cand[c]), -ng, gv, gr))
        tv.append(pop[Lc == 0].sum()); ta.append(pop[Lc == 1].sum()); tr.append(pop[Lc == 2].sum())
        if r % 100 == 0: log("pick", r)
    res = dict(picks=picks, tv=tv, ta=ta, tr=tr, kv=kv, ka=ka)
    atomic(rf, lambda f: pickle.dump(res, f))
picks, tv, ta, tr, kv, ka = res["picks"], res["tv"], res["ta"], res["tr"], res["kv"], res["ka"]
K = len(picks); log("picks", K)
# --- validacion: multifuente desde cero ---
def coverage(nodes):
    nn = len(nodes); vs = N + np.arange(S + nn)
    Gv = sp.coo_matrix((np.r_[L, sd, np.full(nn, 1e-6)], (np.r_[U, N + np.arange(S), N + S + np.arange(nn)], np.r_[V, sn, nodes])), shape=(N + S + nn, N + S + nn)).tocsr()
    D = dijkstra(Gv, directed=False, indices=vs, min_only=True, limit=600)[:N]
    tot = minimo(D[on] + oo, ini)
    lev = np.where(~np.isfinite(tot), 2, np.where(tot < 250, 0, np.where(tot <= 500, 1, 2)))
    return [pop[lev == k].sum() for k in range(3)]
val = []; vmax = 0
for k in (0, 100, K):
    c = coverage(np.array([p[0] for p in picks[:k]], dtype=int)); g = (tv[k], ta[k], tr[k])
    d = max(abs(x - y) for x, y in zip(c, g)); vmax = max(vmax, d)
    val.append(f"| {k} | {c[0]:.2f} / {c[1]:.2f} / {c[2]:.2f} | {g[0]:.2f} / {g[1]:.2f} / {g[2]:.2f} | {d:.4f} |")
    log("validacion k", k, "dif max", d)
ag = json.load(open(P + "agregados.json", encoding="utf-8"))["ciudad"]
tot_pop = float(pop.sum())
open("docs/validacion_ampliacion.md", "w", encoding="utf-8").write(f"""# Validacion de la ampliacion

Cobertura recalculada desde cero con Dijkstra multifuente (estaciones existentes + las k primeras nuevas, enganche exacto al nodo) y comparada con los totales registrados por el greedy (CELF).

| k nuevas | multifuente verde / amarillo / rojo | greedy verde / amarillo / rojo | dif. max (personas) |
|---:|---|---|---:|
""" + "\n".join(val) + f"""

- Diferencia maxima: **{vmax:.4f}** personas.
- k = 0 frente a agregados.json: verde {tv[0]:.1f} vs {ag['pob_v']}, amarillo {ta[0]:.1f} vs {ag['pob_a']}, rojo {tr[0]:.1f} vs {ag['pob_r']}.
- Candidatos: {len(cand)}; pares candidato-edificio a <= 500 m: {len(BI)}.
""")
# --- exportacion ---
pxy = np.array([[nx_[p[0]], ny_[p[0]]] for p in picks])
pg = gpd.GeoDataFrame({"r": np.arange(1, K + 1)}, geometry=gpd.points_from_xy(pxy[:, 0], pxy[:, 1]), crs=25831)
for nm, fl in (("distrito", "distritos"), ("barrio", "barrios")):
    pl = gpd.read_file(P + fl + ".gpkg")[["nombre", "geometry"]].rename(columns={"nombre": nm})
    j = gpd.sjoin(pg[["r", "geometry"]], pl, how="left", predicate="within")
    j = j[~j.r.duplicated()].set_index("r")[nm]
    pg[nm] = pg.r.map(j).where(lambda s: s.notna(), None)
pg["g"] = [int(round(p[1])) for p in picks]; pg["gv"] = [int(round(p[2])) for p in picks]; pg["gr"] = [int(round(p[3])) for p in picks]
g4 = pg[["r", "g", "gv", "gr", "distrito", "barrio", "geometry"]].to_crs(4326)
g4["geometry"] = g4.geometry.set_precision(1e-5)
jwrite(W + "ampliacion_estaciones.geojson", json.loads(g4.to_json(drop_id=True, na="null", show_bbox=False)))
jwrite(W + "ampliacion_curva.json", {"total": int(round(tot_pop)), "v": [int(round(x)) for x in tv], "a": [int(round(x)) for x in ta], "r": [int(round(x)) for x in tr]})
md = json.load(open(W + "metadata.json", encoding="utf-8"))
md["ampliacion"] = {"max": KMAX, "objetivo": "mejora ponderada: rojo→amarillo +1, amarillo→verde +1, rojo→verde +2 por persona", "candidatos": "nodos de la red peatonal dentro del municipio (uno por celda de 50 m)"}
jwrite(W + "metadata.json", md)
log("geojson/curva/metadata listos")
from _pmtiles import escribir
extra = {}
for e, x, y in zip(bld.edif_id.values, ka, kv):
    d = {}
    if y > 0: d["kv"] = int(y)
    if x > 0: d["ka"] = int(x)
    if d: extra[e] = d
escribir(P, W + "edificios.pmtiles", extra)
# --- documentos (idempotente) ---
pcts = lambda k: tuple(100 * x / tot_pop for x in (tv[k], ta[k], tr[k]))
rows = "\n".join("| %d | %.1f %% | %.1f %% | %.1f %% |" % ((k,) + pcts(k)) for k in (0, 25, 50, 100, 250, 500) if k <= K)
top = "\n".join(f"{i+1}. {pg.distrito[i] or '-'} · {pg.barrio[i] or '-'} — ganancia ponderada {pg.g[i]:,}".replace(",", ".") for i in range(min(5, K)))
rfin = open("docs/resumen_final.md", encoding="utf-8").read() if os.path.exists("docs/resumen_final.md") else ""
if "## Ampliación óptima" not in rfin:
    with open("docs/resumen_final.md", "a", encoding="utf-8") as f:
        f.write(f"\n\n## Ampliación óptima\n\nSelección secuencial (greedy) de {K} nuevas estaciones que más mejoran la cobertura poblacional ({len(cand)} candidatos).\n\n| Nuevas estaciones | Verde | Amarillo | Rojo |\n|---:|---:|---:|---:|\n{rows}\n\nLas 5 primeras:\n\n{top}\n")
log("fin")
