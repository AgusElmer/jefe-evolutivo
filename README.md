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
| Coevolución | `jefe/coevolucion.py` | Jefes y héroes (ambos redes neuronales) evolucionan uno contra el otro. |
| Gráficos del juego | `jefe/render.py` | Partículas, halos, estela de embestida, sacudida de pantalla y sonidos sintetizados. |
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
python en_vivo.py       # coevolución en vivo: jefes y héroes evolucionan mientras mirás
python coevolucionar.py # la misma coevolución sin ventana (guarda resultados/coevolucion/)
python analizar.py      # indicadores de comportamiento (qué aprendió)
python diagramas.py     # diagramas conceptuales del informe
```

## Coevolución

En la versión base el jefe aprende contra héroes programados a mano. En la coevolución
(`jefe/coevolucion.py`) los héroes también son redes neuronales (14 → 12 → 4) y evolucionan
al mismo tiempo: cada especie es el rival de la otra. Para que ninguna "olvide" cómo vencer a
rivales anteriores, también pelean contra un salón de la fama con los campeones de cada
generación. Cada 5 generaciones se toma un examen contra rivales fijos (bots y jefe de reglas),
porque la aptitud en la coevolución es relativa.

![Coevolución](resultados/coevolucion/coevolucion.png)

## Jefe final y revancha

`entrenar_jefe_final.py` sigue entrenando al jefe (ajuste fino, con mutación suave) contra los bots
y contra héroes coevolucionados de distintas generaciones. Contra el héroe coevolucionado final, que
no vio, gana el 80 % de las veces (el campeón, el 55 %).

Jugando, encontré una debilidad: si mantenés distancia, rodeás al jefe y te corrés de costado antes
de la embestida, el jefe no tiene respuesta. Esa estrategia es el bot `kiteador`, que le gana al
campeón el 100 % de las veces. `python entrenar_jefe_final.py --extra kiteador --salida revancha`
entrena al jefe sumando ese bot como rival: aprende a ganarle el 47 % de las veces, a costa de rendir
peor contra los demás héroes.

## Jugar

`./jugar.sh` (o `python jugar.py`) abre un menú con tres opciones:

- **Jugar:** elegís la dificultad. Fácil = jefe de la generación 1, Medio = generación 50,
  Difícil = campeón, Revancha = jefe entrenado contra la estrategia de "kitear" (ver abajo).
- **Mirar una pelea:** combates armados entre jefes y héroes (recién nacido vs. bot, campeón vs. bot,
  campeón vs. kiteador, revancha vs. kiteador, coevolucionados).
- **Ver la evolución en vivo:** abre `en_vivo.py`.

Cuando jugás vos, el combate dura 60 s y tus balas hacen más daño que las de los bots.

El sonido se activa o desactiva con **M**. En WSL hace falta la biblioteca de PulseAudio (`sudo apt install libpulse0`); sin ella el juego anda igual, en silencio.

Los bots disponibles son `agresivo`, `francotirador`, `escurridizo` (entrenamiento), `impredecible` (prueba) y `kiteador`.
El balance original está calibrado para los bots, que disparan sin pausa y apuntan muy bien; por eso el
modo humano tiene sus propias reglas (`HUMANO_*` en `jefe/config.py`).

## Datos

No se usa ningún dataset externo: los datos de entrenamiento se **generan por simulación**
(cada combate es un ejemplo). Los resultados de la corrida reportada están en `resultados/`:

- `historial.csv` — aptitud máxima/media/desvío y victorias por generación.
- `comparacion.csv` — 300 combates de cada jefe contra cada estilo de héroe.
- `campeon.npy`, `mejores_por_generacion.npy`, `poblacion_final.npy` — genomas (pesos) guardados.
- `*.png`, `*.gif` — figuras usadas en el informe.

La semilla por defecto es 42, así que `python entrenar.py` reproduce la misma corrida.
