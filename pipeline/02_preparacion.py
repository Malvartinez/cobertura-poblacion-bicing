import geopandas as gpd, pandas as pd
P="data/processed/"
e=gpd.read_file(P+"edificios.gpkg",layer="edificios")
r=e[(e.uso=="1_residential")&(e.n_viviendas>0)][["edif_id","n_viviendas","geometry"]].copy()
r["geometry"]=r.geometry.representative_point()  # siempre dentro del poligono
print("residenciales:",len(r))
sec=gpd.read_file(P+"secciones.gpkg",layer="secciones")[["cusec","geometry"]]
bar=gpd.read_file(P+"barrios.gpkg",layer="barrios")[["cod_barrio","cod_distrito","geometry"]]

def asignar(pts,pol,cols):
    j=gpd.sjoin(pts,pol,predicate="within",how="left").drop(columns="index_right")
    j=j[~j.index.duplicated()]
    miss=j[cols[0]].isna()
    if miss.any():
        n=gpd.sjoin_nearest(pts.loc[miss[miss].index],pol,how="left").drop(columns="index_right")
        n=n[~n.index.duplicated()]
        for c in cols: j.loc[n.index,c]=n[c]
    return j,miss
r,m_sec=asignar(r[["edif_id","n_viviendas","geometry"]],sec,["cusec"])
r["asignacion"]=m_sec.map({True:"cercana",False:"dentro"})
b,m_bar=asignar(r[["geometry"]],bar,["cod_barrio","cod_distrito"])
r["cod_barrio"]=b.cod_barrio; r["cod_distrito"]=b.cod_distrito
print("fuera de seccion -> cercana:",int(m_sec.sum()),"| sin barrio -> cercano:",int(m_bar.sum()))
r=r[["edif_id","n_viviendas","cusec","cod_barrio","cod_distrito","asignacion","geometry"]]
r.to_parquet(P+"edificios_residenciales.parquet")
print("guardado",len(r))
