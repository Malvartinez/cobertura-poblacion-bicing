import geopandas as gpd, pandas as pd, numpy as np
P="data/processed/"
r=gpd.read_parquet(P+"edificios_residenciales.parquet")
pob=pd.read_parquet(P+"poblacion_secciones.parquet")
sec=gpd.read_file(P+"secciones.gpkg",layer="secciones")[["cusec","geometry"]]
bar=gpd.read_file(P+"barrios.gpkg",layer="barrios")[["cod_barrio","cod_distrito","geometry"]]
tot_sec=r.groupby("cusec").n_viviendas.sum()
con_res=set(tot_sec.index)
pobd=pob.set_index("cusec").poblacion
sin_res=[c for c in pobd.index if pobd[c]>0 and c not in con_res]
print("secciones con poblacion sin residenciales:",len(sin_res))
extra=[]; n_otro=0; n_cent=0
if sin_res:
    e=gpd.read_file(P+"edificios.gpkg",layer="edificios")
    o=e[(e.n_viviendas>0)&(e.uso!="1_residential")|((e.n_viviendas>0)&e.uso.isna())][["edif_id","n_viviendas","geometry"]].copy()
    o["geometry"]=o.geometry.representative_point()
    o=gpd.sjoin(o,sec[sec.cusec.isin(sin_res)],predicate="within").drop(columns="index_right")
    o=o[~o.index.duplicated()]
    o["asignacion"]="otro_uso"
    b=gpd.sjoin(o[["geometry"]],bar,predicate="within",how="left")
    b=b[~b.index.duplicated()]
    o["cod_barrio"]=b.cod_barrio; o["cod_distrito"]=b.cod_distrito
    if o.cod_barrio.isna().any():
        m=o.cod_barrio.isna()
        nn=gpd.sjoin_nearest(o.loc[m,["geometry"]],bar,how="left"); nn=nn[~nn.index.duplicated()]
        o.loc[m,"cod_barrio"]=nn.cod_barrio; o.loc[m,"cod_distrito"]=nn.cod_distrito
    extra.append(o); n_otro=o.cusec.nunique()
    rest=[c for c in sin_res if c not in set(o.cusec)]
    if rest:
        s=sec[sec.cusec.isin(rest)].copy(); s["geometry"]=s.geometry.representative_point()
        b=gpd.sjoin(s[["geometry"]],bar,predicate="within",how="left"); b=b[~b.index.duplicated()]
        s["cod_barrio"]=b.cod_barrio; s["cod_distrito"]=b.cod_distrito
        if s.cod_barrio.isna().any():
            m=s.cod_barrio.isna()
            nn=gpd.sjoin_nearest(s.loc[m,["geometry"]],bar,how="left"); nn=nn[~nn.index.duplicated()]
            s.loc[m,"cod_barrio"]=nn.cod_barrio; s.loc[m,"cod_distrito"]=nn.cod_distrito
        s["edif_id"]="SECCION_"+s.cusec; s["n_viviendas"]=0; s["asignacion"]="centroide_seccion"
        extra.append(s); n_cent=len(s)
    print("resueltas otro_uso:",n_otro,"| centroide_seccion:",n_cent)
d=pd.concat([r]+extra,ignore_index=True)
d=gpd.GeoDataFrame(d,geometry="geometry",crs=r.crs)
for c in sin_res:
    pass
d["n_viviendas"]=d.n_viviendas.astype(int)
ts=d.groupby("cusec").n_viviendas.transform("sum")
ok=ts>0
m=d.asignacion=="centroide_seccion"
for col,src in [("poblacion","poblacion"),("pob_15_64","pob_15_64"),("pob_65","pob_65")]:
    ps=pob.set_index("cusec")[src]
    d[col]=0.0
    d.loc[ok,col]=d.cusec.map(ps)[ok]*d.n_viviendas[ok]/ts[ok]
    if m.any(): d.loc[m,col]=d.cusec[m].map(ps).astype(float)
    sx=d.groupby("cusec")[col].sum().reindex(ps.index).fillna(0)
    assert np.allclose(sx,ps,atol=1e-6), col
# checks
s=d.groupby("cusec").poblacion.sum().reindex(pobd.index).fillna(0)
bad=s[~np.isclose(s,pobd,rtol=1e-6,atol=1e-6)]
assert bad.empty, f"secciones no cuadran: {bad.head()}"
assert abs(d.poblacion.sum()-pobd.sum())<=1, (d.poblacion.sum(), pobd.sum())
z=pobd[pobd==0].index
print("secciones pob=0 con residenciales:",len(set(z)&con_res))
d=d[["edif_id","n_viviendas","cusec","cod_barrio","cod_distrito","asignacion","poblacion","pob_15_64","pob_65","geometry"]]
d.to_parquet(P+"edificios_poblacion.parquet")
print("edificios:",len(d),"poblacion:",d.poblacion.sum(), d.asignacion.value_counts().to_dict())
print("sin barrio:",int(d.cod_barrio.isna().sum()))
