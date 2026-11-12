"""Entrena al jefe por neuroevolución y guarda los resultados en resultados/.

Uso:
    python entrenar.py                 # 200 generaciones (config.py)
    python entrenar.py --gen 50 --semilla 7
"""
import argparse
import csv
import time
from pathlib import Path

import numpy as np

from jefe import config as C
from jefe.genetico import nueva_generacion, sigma_en
from jefe.jugadores import ENTRENAMIENTO
from jefe.red import N_GENES, genomas_aleatorios
from jefe.simulacion import evaluar_genomas

SALIDA = Path(__file__).parent / "resultados"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", type=int, default=C.GENERACIONES)
    ap.add_argument("--pob", type=int, default=C.POBLACION)
    ap.add_argument("--semilla", type=int, default=42)
    args = ap.parse_args()

    SALIDA.mkdir(exist_ok=True)
    rng = np.random.default_rng(args.semilla)
    estilos = list(ENTRENAMIENTO)
    poblacion = genomas_aleatorios(args.pob, rng)
    mejores = np.zeros((args.gen, N_GENES))
    historial = []
    t0 = time.time()

    print(f"Neuroevolución: población {args.pob}, {N_GENES} genes por individuo, "
          f"{args.gen} generaciones, {len(estilos) * C.COMBATES_POR_RIVAL} combates por individuo")

    for g in range(args.gen):
        m = evaluar_genomas(poblacion, estilos, C.COMBATES_POR_RIVAL, rng)
        apt = m["aptitud"].mean(axis=1)
        victorias = m["gana_jefe"].mean(axis=1)
        mejor = int(np.argmax(apt))
        mejores[g] = poblacion[mejor]
        fila = {
            "generacion": g + 1,
            "aptitud_max": apt.max(),
            "aptitud_media": apt.mean(),
            "aptitud_min": apt.min(),
            "aptitud_desvio": apt.std(),
            "victorias_mejor": victorias[mejor],
            "victorias_media": victorias.mean(),
            "danio_hecho_media": m["danio_hecho"].mean(),
            "danio_recibido_media": m["danio_recibido"].mean(),
            "sigma": sigma_en(g, args.gen),
        }
        historial.append(fila)
        if g % 10 == 0 or g == args.gen - 1:
            print(f"gen {g + 1:4d} | aptitud máx {apt.max():7.1f} media {apt.mean():7.1f} | "
                  f"victorias: mejor {victorias[mejor]:.0%} media {victorias.mean():.0%} | "
                  f"{time.time() - t0:5.0f}s")
        if g < args.gen - 1:
            poblacion = nueva_generacion(poblacion, apt, g, args.gen, rng)

    # Elegir campeón: los 10 mejores de la última generación juegan 60 combates más cada uno
    m = evaluar_genomas(poblacion, estilos, C.COMBATES_POR_RIVAL, rng)
    top = np.argsort(-m["aptitud"].mean(axis=1))[:10]
    m2 = evaluar_genomas(poblacion[top], estilos, 20, rng)
    campeon = poblacion[top[int(np.argmax(m2["aptitud"].mean(axis=1)))]]

    np.save(SALIDA / "campeon.npy", campeon)
    np.save(SALIDA / "mejores_por_generacion.npy", mejores)
    np.save(SALIDA / "poblacion_final.npy", poblacion)
    with open(SALIDA / "historial.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(historial[0]))
        w.writeheader()
        for fila in historial:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in fila.items()})
    print(f"Listo en {time.time() - t0:.0f}s. Resultados en {SALIDA}/")


if __name__ == "__main__":
    main()
