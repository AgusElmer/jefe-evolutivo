"""Red neuronal del jefe: perceptrón multicapa (MLP) de una capa oculta.

El "cromosoma" de cada individuo es simplemente el vector con todos los pesos
y sesgos de la red, aplanados. El algoritmo genético opera sobre ese vector;
la red lo decodifica (genotipo -> fenotipo) para decidir las acciones.
"""
import numpy as np

from . import config as C

FORMAS = [
    ("W1", (C.N_ENTRADAS, C.N_OCULTAS)),
    ("b1", (C.N_OCULTAS,)),
    ("W2", (C.N_OCULTAS, C.N_SALIDAS)),
    ("b2", (C.N_SALIDAS,)),
]
N_GENES = sum(int(np.prod(f)) for _, f in FORMAS)


def decodificar(genomas):
    """Convierte genomas (P, N_GENES) en matrices de pesos con eje de individuo."""
    genomas = np.atleast_2d(genomas)
    partes, i = {}, 0
    for nombre, forma in FORMAS:
        n = int(np.prod(forma))
        partes[nombre] = genomas[:, i:i + n].reshape((genomas.shape[0],) + forma)
        i += n
    return partes


class RedesEnLote:
    """Evalúa muchas redes a la vez: la red k-ésima corresponde a la partida k."""

    def __init__(self, genomas, indice_por_partida):
        p = decodificar(genomas)
        idx = np.asarray(indice_por_partida)
        self.W1, self.b1 = p["W1"][idx], p["b1"][idx]
        self.W2, self.b2 = p["W2"][idx], p["b2"][idx]

    def __call__(self, x):
        h = np.tanh(np.einsum("bi,bih->bh", x, self.W1) + self.b1)
        return np.tanh(np.einsum("bh,bho->bo", h, self.W2) + self.b2)


def genomas_aleatorios(n, rng, escala=0.5):
    return rng.normal(0.0, escala, size=(n, N_GENES))
