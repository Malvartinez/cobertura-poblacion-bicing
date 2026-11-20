# Validacion de la ampliacion

Cobertura recalculada desde cero con Dijkstra multifuente (estaciones existentes + las k primeras nuevas, enganche exacto al nodo) y comparada con los totales registrados por el greedy (CELF).

| k nuevas | multifuente verde / amarillo / rojo | greedy verde / amarillo / rojo | dif. max (personas) |
|---:|---|---|---:|
| 0 | 1247363.84 / 413921.28 / 51961.88 | 1247363.84 / 413921.28 / 51961.88 | 0.0000 |
| 100 | 1548513.42 / 152947.88 / 11785.70 | 1548513.42 / 152947.88 / 11785.70 | 0.0000 |
| 500 | 1711283.85 / 1813.20 / 149.95 | 1711283.85 / 1813.20 / 149.95 | 0.0000 |

- Diferencia maxima: **0.0000** personas.
- k = 0 frente a agregados.json: verde 1247363.8 vs 1247364, amarillo 413921.3 vs 413921, rojo 51961.9 vs 51962.
- Candidatos: 18454; pares candidato-edificio a <= 500 m: 2190400.
