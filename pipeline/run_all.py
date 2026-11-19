import subprocess, sys, os
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
for s in ["01_descarga_bicing_limites", "01_descarga_ine", "01_descarga_catastro", "01_descarga_osm",
          "02_preparacion", "03_reparto_poblacion", "04_distancias", "05_agregados", "06_exportar_web", "07_ranking_bases", "08_ampliacion"]:
    print("==", s, flush=True)
    if subprocess.run([sys.executable, os.path.join(D, s + ".py")], cwd=R).returncode:
        sys.exit(f"Fallo en {s}")
