"""Funciones para correr combates completos."""
import numpy as np

from . import config as C

from .arena import Arena, aptitud
from .jugadores import HeroeBot
from .red import RedesEnLote


def politica_red(genomas, indice_por_partida):
    redes = RedesEnLote(genomas, indice_por_partida)
    return lambda ar: redes(ar.observar())


def combatir(politica_jefe, estilos, rng, grabar=False, cada=2):
    """Juega len(estilos) combates en paralelo. Devuelve resultados (y fotos si grabar)."""
    ar = Arena(len(estilos), rng)
    heroe = HeroeBot(estilos, rng)
    fotos = []
    while ar.activa.any():
        if grabar and ar.t % cada == 0:
            fotos.append(ar.foto(0))
        ar.paso(politica_jefe(ar), heroe(ar))
    if grabar:
        fotos.append(ar.foto(0))
    res = ar.resultados()
    res["aptitud"] = aptitud(res)
    return (res, fotos) if grabar else res


def evaluar_genomas(genomas, estilos, repeticiones, rng):
    """Cada genoma pelea `repeticiones` veces contra cada estilo. Devuelve métricas por genoma."""
    genomas = np.atleast_2d(genomas)
    p = len(genomas)
    escenarios = [e for e in estilos for _ in range(repeticiones)]
    idx = np.repeat(np.arange(p), len(escenarios))
    todos = escenarios * p
    res = combatir(politica_red(genomas, idx), todos, rng)
    forma = (p, len(escenarios))
    return {k: np.asarray(v, dtype=float).reshape(forma) for k, v in res.items()}


def politica_heroe_red(genomas, indice_por_partida):
    """Convierte la salida de la red del héroe en un comando para la arena."""
    from .red import HEROE
    redes = RedesEnLote(genomas, indice_por_partida, HEROE)

    def politica(ar):
        o = redes(ar.observar_heroe())
        base = np.arctan2(ar.jy - ar.hy, ar.jx - ar.hx)
        return {"vx": o[:, 0], "vy": o[:, 1], "angulo": base + o[:, 2] * C.DESVIO_PUNTERIA, "disparar": o[:, 3] > 0}
    return politica


def combatir_politicas(politica_jefe, politica_heroe, b, rng, grabar=False, cada=2):
    """Como combatir(), pero el héroe también lo maneja una política arbitraria."""
    ar = Arena(b, rng)
    fotos = []
    while ar.activa.any():
        if grabar and ar.t % cada == 0:
            fotos.append(ar.foto(0))
        ar.paso(politica_jefe(ar), politica_heroe(ar))
    res = ar.resultados()
    res["aptitud"] = aptitud(res)
    return (res, fotos) if grabar else res


def evaluar_contra_redes(genomas, heroes, repeticiones, rng):
    """Cada jefe pelea `repeticiones` veces contra cada héroe-red. Devuelve métricas por jefe."""
    genomas, heroes = np.atleast_2d(genomas), np.atleast_2d(heroes)
    p, h = len(genomas), len(heroes)
    n = h * repeticiones
    idx_j = np.repeat(np.arange(p), n)
    idx_h = np.tile(np.repeat(np.arange(h), repeticiones), p)
    res = combatir_politicas(politica_red(genomas, idx_j), politica_heroe_red(heroes, idx_h), p * n, rng)
    return {k: np.asarray(v, dtype=float).reshape(p, n) for k, v in res.items()}
