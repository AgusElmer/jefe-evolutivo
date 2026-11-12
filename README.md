# Jefe evolutivo

Un jefe final de videojuego que **aprende a pelear solo** por neuroevolución: su
comportamiento lo decide una red neuronal y los pesos de esa red se optimizan con
un algoritmo genético, sin que nadie programe reglas a mano.

Trabajo Práctico Integrador de Inteligencia Artificial (Universidad de Palermo).
Agustín Elmer García — Prof. Ignacio Casais.

![Generación 1 vs. campeón](resultados/gen1_vs_campeon.gif)

## Cómo funciona

| Componente | Archivo | Qué hace |
|---|---|---|
| Entorno | `jefe/arena.py` | Arena 2D: el jefe dispara y embiste, el héroe dispara y esquiva. Simula cientos de combates en paralelo con NumPy. |
| Agente (jefe) | `jefe/red.py` | Perceptrón multicapa 15 → 16 → 5 (341 pesos). Percibe 15 variables y decide 5 acciones. |
| Rivales | `jefe/jugadores.py` | 3 héroes bot de entrenamiento (agresivo, francotirador, escurridizo), 1 de prueba nunca visto (impredecible) y un jefe con reglas fijas como línea de base. |
| Aprendizaje | `jefe/genetico.py` | Algoritmo genético: selección por torneo, cruce uniforme, mutación gaussiana decreciente, elitismo. |
| Parámetros | `jefe/config.py` | Todo lo ajustable: balance del juego, red y algoritmo genético. |

**Percepciones del jefe (entradas):** posición relativa y distancia al héroe, velocidad del héroe,
posición y dirección de la bala enemiga más cercana, posición propia (paredes),
si puede embestir o disparar, su vida y la del héroe.

**Acciones (salidas):** dirección de movimiento (x, y), embestir, disparar y ajuste de puntería
(le permite aprender a "adelantar" el tiro).

**Aptitud (fitness):** daño causado − 0,5 × daño recibido + premio por ganar + premio por ganar rápido,
promediado en 6 combates (2 contra cada héroe de entrenamiento).

## Uso

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python entrenar.py      # ~2-3 min en una PC común; guarda resultados/
python evaluar.py       # tablas y gráficos
python grabar.py        # GIF generación 1 vs. campeón
python jugar.py         # jugá vos contra el campeón (WASD + mouse)
python jugar.py --gen 1 # ...o contra el jefe recién nacido
python jugar.py --bot escurridizo   # mirar al jefe contra un héroe bot
python analizar.py      # indicadores de comportamiento (qué aprendió)
python diagramas.py     # diagramas conceptuales del informe
```

Los bots disponibles son `agresivo`, `francotirador`, `escurridizo` (entrenamiento) e `impredecible` (prueba).
El balance del juego está calibrado para los bots, que disparan sin pausa y apuntan muy bien: para una
persona, ganarle incluso al jefe de la generación 1 antes de los 30 segundos es difícil.

## Datos

No se usa ningún dataset externo: los datos de entrenamiento se **generan por simulación**
(cada combate es un ejemplo). Los resultados de la corrida reportada están en `resultados/`:

- `historial.csv` — aptitud máxima/media/desvío y victorias por generación.
- `comparacion.csv` — 300 combates de cada jefe contra cada estilo de héroe.
- `campeon.npy`, `mejores_por_generacion.npy`, `poblacion_final.npy` — genomas (pesos) guardados.
- `*.png`, `*.gif` — figuras usadas en el informe.

La semilla por defecto es 42, así que `python entrenar.py` reproduce la misma corrida.
