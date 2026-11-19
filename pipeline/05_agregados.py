import geopandas as gpd, pandas as pd, json
P = "data/processed/"
b = pd.DataFrame(pd.read_parquet(P + "edificios_distancias.parquet").drop(columns="geometry"))
C = []
for pre, src in (("", "poblacion"), ("a_", "pob_15_64"), ("m_", "pob_65")):
    b[pre + "pob"] = b[src]
    for k, nv in zip("var", range(3)): b[pre + "pob_" + k] = b[src].where(b.nivel == nv, 0.0)
    C += [pre + s for s in ("pob", "pob_v", "pob_a", "pob_r")]
def fin(d):
    o = {k: int(round(d[k])) for k in C}
    for pre in ("", "a_", "m_"):
        for k in "var": o[pre + "pct_" + k] = round(100 * d[pre + "pob_" + k] / d[pre + "pob"], 1) if d[pre + "pob"] > 0 else 0.0
    return o
z = pd.Series({k: 0.0 for k in C})
gd, gb, gs = (b.groupby(k)[C].sum() for k in ("cod_distrito", "cod_barrio", "cusec"))
get = lambda g, c: g.loc[c] if c in g.index else z
res = {"ciudad": fin(b[C].sum())}
nd = gpd.read_file(P + "distritos.gpkg").set_index("cod_distrito").nombre
nb = gpd.read_file(P + "barrios.gpkg").set_index("cod_barrio")[["nombre", "cod_distrito"]]
sec = gpd.read_file(P + "secciones.gpkg")
res["distritos"] = [{"cod": c, "nombre": n, **fin(get(gd, c))} for c, n in nd.items()]
res["barrios"] = [{"cod": c, "nombre": r.nombre, "cod_distrito": r.cod_distrito, "distrito": nd.get(r.cod_distrito), **fin(get(gb, c))} for c, r in nb.iterrows()]
res["secciones"] = [{"cod": c, **fin(get(gs, c))} for c in sec.cusec]
for k in ["distritos", "barrios", "secciones"]:
    print(k, len(res[k]), "suma", sum(x["pob"] for x in res[k]), "ciudad", res["ciudad"]["pob"])
json.dump(res, open(P + "agregados.json", "w", encoding="utf-8"), ensure_ascii=False)
print(res["ciudad"])
