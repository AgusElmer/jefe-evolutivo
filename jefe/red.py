"""Redes neuronales de los agentes: perceptrón multicapa (MLP) de una capa oculta.

El "cromosoma" de cada individuo es simplemente el vector con todos los pesos
y sesgos de la red, aplanados. El algoritmo genético opera sobre ese vector;
la red lo decodifica (genotipo -> fenotipo) para decidir las acciones.

Hay dos arquitecturas: la del jefe y la del héroe (usada en la coevolución).
"""
import numpy as np

from . import config as C


class Arquitectura:
    def __init__(self, n_entradas, n_ocultas, n_salidas):
        self.formas = [
            ("W1", (n_entradas, n_ocultas)),
            ("b1", (n_ocultas,)),
            ("W2", (n_ocultas, n_salidas)),
            ("b2", (n_salidas,)),
        ]
        self.n_genes = sum(int(np.prod(f)) for _, f in self.formas)

    def decodificar(self, genomas):
        """Convierte genomas (P, n_genes) en matrices de pesos con eje de individuo."""
        genomas = np.atleast_2d(genomas)
        partes, i = {}, 0
        for nombre, forma in self.formas:
            n = int(np.prod(forma))
            partes[nombre] = genomas[:, i:i + n].reshape((genomas.shape[0],) + forma)
            i += n
        return partes

    def aleatorios(self, n, rng, escala=0.5):
        return rng.normal(0.0, escala, size=(n, self.n_genes))


JEFE = Arquitectura(C.N_ENTRADAS, C.N_OCULTAS, C.N_SALIDAS)
HEROE = Arquitectura(C.HEROE_N_ENTRADAS, C.HEROE_N_OCULTAS, C.HEROE_N_SALIDAS)

# Compatibilidad con el código original (solo jefe)
N_GENES = JEFE.n_genes
decodificar = JEFE.decodificar


class RedesEnLote:
    """Evalúa muchas redes a la vez: la red k-ésima corresponde a la partida k."""

    def __init__(self, genomas, indice_por_partida, arq=JEFE):
        p = arq.decodificar(genomas)
        idx = np.asarray(indice_por_partida)
        self.W1, self.b1 = p["W1"][idx], p["b1"][idx]
        self.W2, self.b2 = p["W2"][idx], p["b2"][idx]

    def __call__(self, x):
        h = np.tanh(np.einsum("bi,bih->bh", x, self.W1) + self.b1)
        return np.tanh(np.einsum("bh,bho->bo", h, self.W2) + self.b2)


def genomas_aleatorios(n, rng, escala=0.5):
    return JEFE.aleatorios(n, rng, escala)
