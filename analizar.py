"""Describe *qué* aprendió el jefe: mide su comportamiento paso a paso.

Compara al mejor jefe de la generación 1, al jefe con reglas fijas y al campeón
en 200 combates contra cada héroe, y guarda resultados/comportamiento.csv.
"""
import csv
from pathlib import Path

import numpy as np

from jefe import config as C
from jefe.arena import Arena
from jefe.jugadores import TODOS, HeroeBot, jefe_manual
from jefe.simulacion import politica_red

R = Path(__file__).parent / "resultados"


def medir(politica, n, rng):
    estilos = [e for e in TODOS for _ in range(n)]
    ar = Arena(len(estilos), rng)
    heroe = HeroeBot(estilos, rng)
    dist, ajuste, vel, pasos = [], [], [], []
    while ar.activa.any():
        out = politica(ar)
        a = ar.activa.copy()
        dist.append(np.where(a, np.hypot(ar.hx - ar.jx, ar.hy - ar.jy), np.nan))
        ajuste.append(np.where(a, np.abs(out[:, 4]) * C.DESVIO_PUNTERIA, np.nan))
        ar.paso(out, heroe(ar))
        vel.append(np.where(a, np.hypot(ar.jvx, ar.jvy), np.nan))
    res = ar.resultados()
    seg = res["duracion"] / C.PASOS_POR_SEGUNDO
    return {
        "distancia_media_al_heroe": np.nanmean(dist),
        "ajuste_punteria_medio_grados": np.degrees(np.nanmean(ajuste)),
        "velocidad_media_rel": np.nanmean(vel) / C.JEFE_VEL,
        "disparos_por_segundo": (res["disparos"] / seg).mean(),
        "embestidas_por_segundo": (res["embestidas"] / seg).mean(),
        "precision_embestida": res["embestidas_acertadas"].sum() / max(1, res["embestidas"].sum()),
        "danio_recibido_por_segundo": (res["danio_recibido"] / seg).mean(),
        "victorias": res["gana_jefe"].mean(),
    }


def main():
    rng = np.random.default_rng(7)
    mejores = np.load(R / "mejores_por_generacion.npy")
    campeon = np.load(R / "campeon.npy")
    n = 200
    b = n * len(TODOS)
    jefes = {
        "Red, generación 1": politica_red(mejores[0], np.zeros(b, int)),
        "Reglas fijas (manual)": jefe_manual,
        "Red evolucionada (campeón)": politica_red(campeon, np.zeros(b, int)),
    }
    filas = []
    for nombre, pol in jefes.items():
        m = medir(pol, n, rng)
        filas.append({"jefe": nombre, **{k: round(float(v), 3) for k, v in m.items()}})
    with open(R / "comportamiento.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader(); w.writerows(filas)
    for k in filas[0]:
        print(f"{k:32s}" + "".join(f"{str(f[k]):>28s}" for f in filas))


if __name__ == "__main__":
    main()
