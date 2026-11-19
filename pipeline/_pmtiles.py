# Escritor de edificios.pmtiles compartido por 06 y 08. extra: {edif_id: {"ka": int, "kv": int}}
import geopandas as gpd, pandas as pd, os, gzip, mercantile, numpy as np, shapely, mapbox_vector_tile
from shapely import affinity
from shapely.geometry import box
from pmtiles.writer import Writer
from pmtiles.tile import zxy_to_tileid, Compression, TileType
def escribir(P, out, extra=None):
    b = pd.DataFrame(gpd.read_parquet(P + "edificios_distancias.parquet"))
    b["geometry"] = None
    # --- Edificios: PMTiles (MVT) con huellas reales de Catastro ---
    bd = b[~b.edif_id.astype(str).str.startswith("SECCION_")]
    fp = gpd.read_file(P + "edificios.gpkg", layer="edificios")[["edif_id", "geometry"]]
    fp = fp[~fp.edif_id.duplicated()]
    t = fp.merge(pd.DataFrame(bd.drop(columns="geometry"))[["edif_id", "poblacion", "distancia", "nivel", "base_nombre"]], on="edif_id")
    t = gpd.GeoDataFrame(t, geometry="geometry", crs=fp.crs).to_crs(3857)
    t = t[~t.geometry.is_empty & t.geometry.notna()].reset_index(drop=True)
    t["p"] = t.poblacion.round().astype(int)
    q = [float(x) for x in np.quantile(t.p, [.2, .4, .6, .8])]
    CORTES = [int(round(x)) for x in q]
    t["k"] = sum((t.p > c).astype(int) for c in CORTES)
    t["area"] = t.geometry.area
    print("edificios en tiles:", len(t), "cortes k:", CORTES, "sin huella:", len(bd) - len(t))
    props = [{"p": int(p), "n": int(n), **({"d": int(round(d))} if pd.notna(d) else {}), **({"b": str(bn)} if isinstance(bn, str) else {}), "k": int(k)}
             for p, n, d, bn, k in zip(t.p, t.nivel, t.distancia, t.base_nombre, t.k)]
    if extra:
        for j, e in enumerate(t.edif_id.values):
            if e in extra: props[j].update(extra[e])
    SIMP = {12: (2.0, 30), 13: (1.0, 30)}
    EXT = 4096; Z0, Z1 = 12, 16
    ntiles = 0
    tmp = out + ".tmp"
    with open(tmp, "wb") as fh:
        wr = Writer(fh)
        for z in range(Z0, Z1 + 1):
            tol, amin = SIMP.get(z, (0, 0))
            idx = np.where(t.area.values >= amin)[0]
            geoms = t.geometry.values[idx]
            if tol: geoms = shapely.simplify(geoms, tol)
            bnds = shapely.bounds(geoms); tmap = {}
            for j, (x0, y0, x1, y1) in enumerate(bnds):
                if np.isnan(x0): continue
                w0, s0 = mercantile.lnglat(x0, y0); e0, n0 = mercantile.lnglat(x1, y1)
                for tl in mercantile.tiles(w0, s0, e0, n0, z, truncate=True):
                    tmap.setdefault((tl.x, tl.y), []).append(j)
            for (x, y), js in sorted(tmap.items(), key=lambda kv: zxy_to_tileid(z, *kv[0])):
                bb = mercantile.xy_bounds(x, y, z); sc = EXT / (bb.right - bb.left)
                clip = box(-64, -64, EXT + 64, EXT + 64); feats = []
                for j in js:
                    g = affinity.affine_transform(geoms[j], [sc, 0, 0, -sc, -bb.left * sc, bb.top * sc])
                    g = shapely.set_precision(g.intersection(clip), 1.0)
                    if g.is_empty: continue
                    if not g.is_valid: g = shapely.make_valid(g)
                    g = shapely.get_parts(g); g = [p for p in g if p.geom_type == "Polygon" and not p.is_empty]
                    if not g: continue
                    feats.append({"geometry": g[0] if len(g) == 1 else shapely.MultiPolygon(g), "properties": props[idx[j]]})
                if not feats: continue
                data = mapbox_vector_tile.encode([{"name": "edificios", "features": feats}], default_options={"extents": EXT, "y_coord_down": True})
                wr.write_tile(zxy_to_tileid(z, x, y), gzip.compress(data, 9, mtime=0)); ntiles += 1
            print("z", z, "tiles acumulados", ntiles, flush=True)
        bx = t.to_crs(4326).total_bounds
        wr.finalize({"tile_type": TileType.MVT, "tile_compression": Compression.GZIP, "min_zoom": Z0, "max_zoom": Z1,
                     "min_lon_e7": int(bx[0] * 1e7), "min_lat_e7": int(bx[1] * 1e7), "max_lon_e7": int(bx[2] * 1e7), "max_lat_e7": int(bx[3] * 1e7),
                     "center_zoom": 13, "center_lon_e7": int((bx[0] + bx[2]) / 2 * 1e7), "center_lat_e7": int((bx[1] + bx[3]) / 2 * 1e7)},
                    {"name": "edificios", "format": "pbf", "minzoom": str(Z0), "maxzoom": str(Z1), "type": "overlay",
                     "vector_layers": [{"id": "edificios", "fields": {"p": "Number", "d": "Number", "n": "Number", "b": "String", "k": "Number", "ka": "Number", "kv": "Number"}, "minzoom": Z0, "maxzoom": Z1}]})
    os.replace(tmp, out)
    print("pmtiles", round(os.path.getsize(out) / 1e6, 2), "MB", ntiles, "tiles")
    return CORTES
