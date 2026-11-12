"""Algoritmo genético que evoluciona los pesos de la red del jefe (neuroevolución).

Ciclo clásico: población -> evaluación (aptitud) -> selección por torneo ->
cruce uniforme -> mutación gaussiana -> nueva generación (con elitismo).
"""
import numpy as np

from . import config as C


def seleccion_torneo(aptitudes, n, rng, k=C.TORNEO_K):
    """Elige n índices: en cada torneo compiten k individuos al azar y gana el más apto."""
    candidatos = rng.integers(0, len(aptitudes), size=(n, k))
    ganador = np.argmax(aptitudes[candidatos], axis=1)
    return candidatos[np.arange(n), ganador]


def cruce_uniforme(padres_a, padres_b, rng, prob=C.PROB_CRUCE):
    """Cada gen del hijo viene de uno u otro padre con probabilidad 1/2."""
    mascara = rng.random(padres_a.shape) < 0.5
    hijos = np.where(mascara, padres_a, padres_b)
    sin_cruce = rng.random(len(padres_a)) > prob
    hijos[sin_cruce] = padres_a[sin_cruce]
    return hijos


def mutacion_gaussiana(genomas, sigma, rng, prob=C.PROB_MUTACION):
    """Suma ruido normal N(0, sigma) a cada gen con probabilidad `prob`."""
    mascara = rng.random(genomas.shape) < prob
    return genomas + mascara * rng.normal(0, sigma, genomas.shape)


def sigma_en(generacion, total):
    """La mutación arranca grande (explorar) y se achica (refinar)."""
    frac = generacion / max(1, total - 1)
    return C.SIGMA_MUTACION + (C.SIGMA_MUTACION_MIN - C.SIGMA_MUTACION) * frac


def nueva_generacion(poblacion, aptitudes, generacion, total, rng):
    orden = np.argsort(-aptitudes)
    elite = poblacion[orden[:C.ELITISMO]].copy()
    n_hijos = len(poblacion) - C.ELITISMO
    a = poblacion[seleccion_torneo(aptitudes, n_hijos, rng)]
    b = poblacion[seleccion_torneo(aptitudes, n_hijos, rng)]
    hijos = cruce_uniforme(a, b, rng)
    hijos = mutacion_gaussiana(hijos, sigma_en(generacion, total), rng)
    return np.vstack([elite, hijos])
