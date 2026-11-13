"""Coevolución sin ventana (más rápida). Para verla en vivo usá en_vivo.py.

    python coevolucionar.py               # 300 generaciones, semilla 7
    python coevolucionar.py --gen 500

Guarda en resultados/coevolucion/: historial.csv, mejores jefes y héroes por
generación, el jefe y el héroe finales (que aparecen en el menú de jugar.py) y
el gráfico coevolucion.png.
"""
import argparse
import csv
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from jefe.coevolucion import Coevolucion

CARPETA = Path(__file__).parent / "resultados" / "coevolucion"
NARANJA, AZUL, GRIS = "#eb6834", "#2a78d6", "#8a8984"


def suavizar(x, k=9):
    x = np.asarray(x, float)
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, mode="valid")


def graficar():
    with open(CARPETA / "historial.csv") as f:
        filas = list(csv.DictReader(f))
    h = {k: np.array([float(r[k]) for r in filas]) for k in filas[0]}
    g = h["generacion"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True, "grid.color": "#ecebe7"})
    fig, axs = plt.subplots(2, 1, figsize=(7, 6), sharex=True)
    ax = axs[0]
    ax.plot(g, h["victorias_jefes"] * 100, color=NARANJA, alpha=0.25, lw=1)
    ax.plot(g, h["victorias_heroes"] * 100, color=AZUL, alpha=0.25, lw=1)
    ax.plot(g, suavizar(h["victorias_jefes"]) * 100, color=NARANJA, lw=2, label="Jefes")
    ax.plot(g, suavizar(h["victorias_heroes"]) * 100, color=AZUL, lw=2, label="Héroes")
    ax.set_ylim(0, 100); ax.set_ylabel("Victorias (%)")
    ax.set_title("Carrera armamentista: combates entre las poblaciones actuales", fontweight="bold", fontsize=11)
    ax.legend(frameon=False, loc="upper right", ncol=2)
    ax = axs[1]
    m = ~np.isnan(h["examen_jefe"])
    idx = np.r_[True, (np.diff(h["examen_jefe"][m]) != 0) | (np.diff(h["examen_heroe"][m]) != 0)]
    gx = g[m][idx]
    ax.plot(gx, h["examen_jefe"][m][idx] * 100, color=NARANJA, lw=1.6, marker="o", ms=2.5, label="Jefe vs. héroes bot")
    ax.plot(gx, h["examen_heroe"][m][idx] * 100, color=AZUL, lw=1.6, marker="o", ms=2.5, label="Héroe vs. jefe de reglas")
    ax.set_ylim(0, 105); ax.set_ylabel("Victorias (%)"); ax.set_xlabel("Generación")
    ax.set_title("Examen contra rivales fijos", fontweight="bold", fontsize=11)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    fig.savefig(CARPETA / "coevolucion.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", type=int, default=300)
    ap.add_argument("--semilla", type=int, default=7)
    ap.add_argument("--solo-grafico", action="store_true")
    args = ap.parse_args()
    if not args.solo_grafico:
        co = Coevolucion(semilla=args.semilla, generaciones_previstas=args.gen)
        t0 = time.time()
        for _ in range(args.gen):
            f, _, _ = co.paso()
            if f["generacion"] % 10 == 0:
                print(f"gen {f['generacion']:4d} | victorias jefes {f['victorias_jefes']:4.0%} "
                      f"héroes {f['victorias_heroes']:4.0%} | examen jefe {f['examen_jefe']:4.0%} "
                      f"héroe {f['examen_heroe']:4.0%} | {time.time() - t0:4.0f}s", flush=True)
        co.guardar(CARPETA)
    graficar()
    print("Listo:", CARPETA)


if __name__ == "__main__":
    main()
