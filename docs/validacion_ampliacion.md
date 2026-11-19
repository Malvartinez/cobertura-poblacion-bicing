# Validacion de la ampliacion

Cobertura recalculada desde cero con Dijkstra multifuente (estaciones existentes + las k primeras nuevas, enganche exacto al nodo) y comparada con los totales registrados por el greedy (CELF).

| k nuevas | multifuente verde / amarillo / rojo | greedy verde / amarillo / rojo | dif. max (personas) |
|---:|---|---|---:|
| 0 | 1269714.08 / 393622.54 / 49910.38 | 1269714.08 / 393622.54 / 49910.38 | 0.0000 |
| 100 | 1561219.89 / 140085.34 / 11941.77 | 1561219.89 / 140085.34 / 11941.77 | 0.0000 |
| 500 | 1711682.92 / 1441.27 / 122.81 | 1711682.92 / 1441.27 / 122.81 | 0.0000 |

- Diferencia maxima: **0.0000** personas.
- k = 0 frente a agregados.json: verde 1269714.1 vs 1269714, amarillo 393622.5 vs 393623, rojo 49910.4 vs 49910.
- Candidatos: 18454; pares candidato-edificio a <= 500 m: 2135558.
