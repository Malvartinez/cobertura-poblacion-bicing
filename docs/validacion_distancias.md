# Validacion de distancias

Muestra aleatoria de 50 edificios (semilla 42) con distancia finita; ruta individual recalculada con networkx (Dijkstra desde un nodo temporal del edificio hacia los nodos virtuales de estaciones, mismas aristas y pesos de enganche).

- Coinciden dentro del 5 %: **50/50**
- Error relativo maximo: **0.0000 %**
- Estaciones con snap > 150 m: 0
- Edificios sin base a <= 1500 m: 1346
