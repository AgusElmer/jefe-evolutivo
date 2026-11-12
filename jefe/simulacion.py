"""Funciones para correr combates completos."""
import numpy as np

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
