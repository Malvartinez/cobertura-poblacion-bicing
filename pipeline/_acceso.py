"""Puntos de acceso de cada edificio a la red peatonal (compartido por 04, 07 y 08).

Distancia de un edificio = minimo, sobre sus opciones de acceso, de (distancia por la red hasta el nodo + desfase).
Opciones (criterio de BicinRivas, ADR-0126 de aquel proyecto):
  1. Enganche del punto interior a la arista mas cercana: dos opciones, una por cada extremo de la arista
     (desfase = distancia perpendicular + tramo de arista hasta ese extremo). Garantiza acceso a todo edificio.
  2. Todos los nodos de la red a <= RADIO m de la huella del edificio, con desfase = distancia del nodo al borde.
     Evita que en las manzanas grandes el punto interior se enganche a la calle de atras.
Los edificios sinteticos SECCION_* (sin huella) solo tienen la opcion 1.

Portales (desde 2026-11-20, a propuesta del usuario): si el edificio tiene portal en el Catastro INSPIRE Addresses
(portales.parquet, paso 01_direcciones), sus opciones 1 y 2 se sustituyen por las de sus portales: por cada portal, los
dos extremos de su arista de acceso (desfase = distancia portal-arista + tramo hasta ese extremo). El acceso esta en
la calle de la direccion y no en cualquier calle que bordee el edificio. Sin portal (o catastro foral, cuyo punto es
el centroide): opciones 1 y 2.
"""
import os
import numpy as np, pandas as pd, geopandas as gpd, shapely
from shapely import STRtree

RADIO = 30.0


def accesos(P, bld, ed, U, V, L, nx_, ny_, portales=True):
    """Devuelve (ob, on, oo, ini, dp): edificio, nodo y desfase de cada opcion, ordenadas por edificio;
    ini = posicion de la primera opcion de cada edificio (para np.minimum.reduceat); dp = distancia del punto
    interior a su arista mas cercana. portales=False: solo metodo de borde (figuras de comparacion)."""
    nb = len(bld)
    geoms = ed.geometry.values; pts = bld.geometry.values
    qi, dist = STRtree(geoms).query_nearest(pts, return_distance=True, all_matches=False)
    eg = np.empty(nb, dtype=int); eg[qi[0]] = qi[1]
    dp = np.empty(nb); dp[qi[0]] = dist
    line = geoms[eg]; ln = shapely.length(line)
    t = np.where(ln > 0, shapely.line_locate_point(line, pts) / np.where(ln > 0, ln, 1), 0)
    st = shapely.get_point(line, 0); sx, sy = shapely.get_x(st), shapely.get_y(st)
    u = U[eg]; v = V[eg]; Le = L[eg]
    du = np.hypot(nx_[u] - sx, ny_[u] - sy); dv = np.hypot(nx_[v] - sx, ny_[v] - sy)
    start = np.where(du <= dv, u, v); end = np.where(du <= dv, v, u)
    ib = np.arange(nb)
    B, N, O = [ib, ib], [start, end], [dp + t * Le, dp + (1 - t) * Le]
    # nodos a <= RADIO m de la huella
    fp = gpd.read_file(P + "edificios.gpkg", columns=["edif_id"]).drop_duplicates("edif_id")
    hu = pd.Series(fp.geometry.values, index=fp.edif_id.values).reindex(bld.edif_id.astype(str).values)
    con = np.flatnonzero(hu.notna().values)
    poly = shapely.make_valid(hu.values[con])
    npts = shapely.points(nx_, ny_)
    pi, ni = STRtree(npts).query(shapely.buffer(poly, RADIO), predicate="contains")
    if len(pi):
        B.append(con[pi]); N.append(ni); O.append(shapely.distance(npts[ni], poly[pi]))
    ob = np.concatenate(B); on = np.concatenate(N).astype(np.int64); oo = np.concatenate(O).astype(float)
    # portales: sustituyen a las opciones anteriores en los edificios que los tienen
    npor = 0
    if portales and os.path.exists(P + "portales.parquet"):
        pt = pd.read_parquet(P + "portales.parquet")
        pos = pd.Series(np.arange(nb), index=bld.edif_id.astype(str).str[:14].values)
        pos = pos[~pos.index.duplicated()]
        pt = pt[pt.refcat.isin(pos.index)]
        if len(pt):
            pbi = pos[pt.refcat.values].values; e = pt.arista.values.astype(int)
            pp = shapely.points(pt.x.values, pt.y.values); line = geoms[e]; ln = shapely.length(line)
            tp = np.where(ln > 0, shapely.line_locate_point(line, pp) / np.where(ln > 0, ln, 1), 0)
            s0 = shapely.get_point(line, 0); x0, y0 = shapely.get_x(s0), shapely.get_y(s0)
            uu, vv, Lp = U[e], V[e], L[e]
            d0 = np.hypot(nx_[uu] - x0, ny_[uu] - y0) <= np.hypot(nx_[vv] - x0, ny_[vv] - y0)
            a0 = np.where(d0, uu, vv); a1 = np.where(d0, vv, uu); dpp = pt.d_arista.values
            con_p = np.zeros(nb, bool); con_p[pbi] = True
            keep = ~con_p[ob]
            ob = np.r_[ob[keep], pbi, pbi]; on = np.r_[on[keep], a0, a1].astype(np.int64)
            oo = np.r_[oo[keep], dpp + tp * Lp, dpp + (1 - tp) * Lp].astype(float)
            npor = int(con_p.sum())
    o = np.argsort(ob, kind="stable"); ob, on, oo = ob[o], on[o], oo[o]
    ini = np.r_[0, np.flatnonzero(np.diff(ob)) + 1]
    assert len(ini) == nb, "todo edificio debe tener al menos una opcion de acceso"
    print(f"accesos: {len(ob)} opciones ({len(ob) / nb:.1f} por edificio), {len(pi)} por borde a <= {RADIO:.0f} m; "
          f"{npor} edificios ({npor / nb:.0%}) por portal", flush=True)
    return ob, on, oo, ini, dp


def minimo(vals, ini):
    """Minimo por edificio de un array de opciones (1D) o de una matriz (filas x opciones)."""
    return np.minimum.reduceat(vals, ini, axis=-1)
