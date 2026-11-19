# Validacion de la ampliacion

Cobertura recalculada desde cero con Dijkstra multifuente (estaciones existentes + las k primeras nuevas, enganche exacto al nodo) y comparada con los totales registrados por el greedy (CELF).

| k nuevas | multifuente verde / amarillo / rojo | greedy verde / amarillo / rojo | dif. max (personas) |
|---:|---|---|---:|
| 0 | 1113089.20 / 544267.96 / 55889.84 | 1113089.20 / 544267.96 / 55889.84 | 0.0000 |
| 100 | 1447059.44 / 251235.52 / 14952.05 | 1447059.44 / 251235.52 / 14952.05 | 0.0000 |
| 500 | 1703658.27 / 9043.57 / 545.16 | 1703658.27 / 9043.57 / 545.16 | 0.0000 |

- Diferencia maxima: **0.0000** personas.
- k = 0 frente a agregados.json: verde 1113089.2 vs 1113089, amarillo 544268.0 vs 544268, rojo 55889.8 vs 55890.
- Candidatos: 18454; pares candidato-edificio a <= 500 m: 2381184.
