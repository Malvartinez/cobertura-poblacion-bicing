"""Puntos de acceso de cada edificio a la red peatonal (compartido por 04, 07 y 08).

Distancia de un edificio = minimo, sobre sus opciones de acceso, de (distancia por la red hasta el nodo + desfase).
Opciones (criterio de BicinRivas, ADR-0126 de aquel proyecto):
  1. Enganche del punto interior a la arista mas cercana: dos opciones, una por cada extremo de la arista
     (desfase = distancia perpendicular + tramo de arista hasta ese extremo). Garantiza acceso a todo edificio.
  2. Todos los nodos de la red a <= RADIO m de la huella del edificio, con desfase = distancia del nodo al borde.
     Evita que en las manzanas grandes el punto interior se enganche a la calle de atras.
Los edificios sinteticos SECCION_* (sin huella) solo tienen la opcion 1.
"""
import numpy as np, pandas as pd, geopandas as gpd, shapely
from shapely import STRtree

RADIO = 30.0


def accesos(P, bld, ed, U, V, L, nx_, ny_):
    """Devuelve (ob, on, oo, ini, dp): edificio, nodo y desfase de cada opcion, ordenadas por edificio;
    ini = posicion de la primera opcion de cada edificio (para np.minimum.reduceat); dp = distancia del punto
    interior a su arista mas cercana."""
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
    o = np.argsort(ob, kind="stable"); ob, on, oo = ob[o], on[o], oo[o]
    ini = np.r_[0, np.flatnonzero(np.diff(ob)) + 1]
    assert len(ini) == nb, "todo edificio debe tener al menos una opcion de acceso"
    print(f"accesos: {len(ob)} opciones ({len(ob) / nb:.1f} por edificio), {len(pi)} por borde a <= {RADIO:.0f} m", flush=True)
    return ob, on, oo, ini, dp


def minimo(vals, ini):
    """Minimo por edificio de un array de opciones (1D) o de una matriz (filas x opciones)."""
    return np.minimum.reduceat(vals, ini, axis=-1)
