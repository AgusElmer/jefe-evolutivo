"""Parámetros del juego, de la red neuronal y del algoritmo genético.

Todas las distancias están en "unidades de arena": la arena es un cuadrado de 1 x 1.
El tiempo se mide en pasos de simulación (30 pasos = 1 segundo de juego).
"""

# ---------------------------------------------------------------- Juego
PASOS_POR_SEGUNDO = 30
DURACION_MAX = 30 * PASOS_POR_SEGUNDO       # 30 segundos por combate

# Jefe
JEFE_RADIO = 0.05
JEFE_VEL = 0.009
JEFE_VIDA = 150.0
JEFE_BALA_VEL = 0.020
JEFE_BALA_DANIO = 8.0
JEFE_DISPARO_CD = 20                        # pasos entre disparos
JEFE_EMBESTIDA_VEL = 0.035
JEFE_EMBESTIDA_DURACION = 10
JEFE_EMBESTIDA_CD = 60
JEFE_EMBESTIDA_DANIO = 12.0
JEFE_CONTACTO_DANIO = 0.3                   # por paso, si se tocan sin embestida

# Héroe (jugador)
HEROE_RADIO = 0.025
HEROE_VEL = 0.012
HEROE_VIDA = 100.0
HEROE_BALA_VEL = 0.025
HEROE_BALA_DANIO = 5.0
HEROE_DISPARO_CD = 12

BALA_RADIO = 0.008
MAX_BALAS = 8                               # balas simultáneas por bando

# ---------------------------------------------------------------- Red neuronal
N_ENTRADAS = 15
N_OCULTAS = 16
N_SALIDAS = 5                               # mover x, mover y, embestir, disparar, ajuste de puntería
DESVIO_PUNTERIA = 0.6                       # radianes máximos de ajuste de puntería

# ---------------------------------------------------------------- Algoritmo genético
POBLACION = 80
GENERACIONES = 200
ELITISMO = 4
TORNEO_K = 4
PROB_CRUCE = 0.8
PROB_MUTACION = 0.08                        # probabilidad por gen
SIGMA_MUTACION = 0.30
SIGMA_MUTACION_MIN = 0.05
COMBATES_POR_RIVAL = 2                      # combates contra cada héroe de entrenamiento

# ---------------------------------------------------------------- Aptitud (fitness)
PREMIO_VICTORIA = 50.0
PREMIO_RAPIDEZ = 30.0
PESO_DANIO_RECIBIDO = 0.5

# ---------------------------------------------------------------- Coevolución (héroes que también aprenden)
HEROE_N_ENTRADAS = 14
HEROE_N_OCULTAS = 12
HEROE_N_SALIDAS = 4                         # mover x, mover y, ajuste de puntería, disparar
COEVO_POBLACION = 60                        # por especie
COEVO_RIVALES = 4                           # combates contra la población rival actual
COEVO_SALON = 2                             # combates contra campeones históricos ("salón de la fama")
COEVO_EXAMEN_CADA = 5                       # cada cuántas generaciones se mide contra rivales fijos

# ---------------------------------------------------------------- Modo humano (jugar.py)
HUMANO_DURACION = 60 * PASOS_POR_SEGUNDO    # una persona necesita más tiempo que un bot
HUMANO_BALA_DANIO = 7.0
