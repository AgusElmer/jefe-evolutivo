"""Evalúa al jefe entrenado contra líneas de base y genera los gráficos del informe.

Requiere haber corrido entrenar.py. Escribe en resultados/:
    comparacion.csv, curva_aptitud.png, victorias_por_generacion.png,
    comparacion_jefes.png, trayectorias.png
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from jefe import config as C
from jefe.jugadores import ENTRENAMIENTO, PRUEBA, TODOS, jefe_manual, jefe_quieto
from jefe.simulacion import combatir, evaluar_genomas, politica_red

R = Path(__file__).parent / "resultados"
N_COMBATES = 300

# Paleta (validada para daltonismo; ver README)
AZUL, NARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GRIS, GRIS_CLARO = "#8a8984", "#d6d5d0"
TINTA, TINTA2 = "#0b0b0b", "#52514e"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.edgecolor": GRIS_CLARO, "axes.labelcolor": TINTA2,
    "xtick.color": TINTA2, "ytick.color": TINTA2,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#ecebe7", "grid.linewidth": 0.8,
    "axes.titleweight": "bold", "axes.titlecolor": TINTA, "axes.titlesize": 11,
    "figure.dpi": 150, "savefig.bbox": "tight", "legend.frameon": False,
})


def leer_historial():
    with open(R / "historial.csv") as f:
        filas = list(csv.DictReader(f))
    return {k: np.array([float(r[k]) for r in filas]) for k in filas[0]}


def grafico_aptitud(h):
    g = h["generacion"]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.fill_between(g, h["aptitud_media"] - h["aptitud_desvio"], h["aptitud_media"] + h["aptitud_desvio"],
                    color=AZUL, alpha=0.12, linewidth=0, label="Media ± 1 desvío")
    ax.plot(g, h["aptitud_max"], color=NARANJA, lw=2, label="Mejor individuo")
    ax.plot(g, h["aptitud_media"], color=AZUL, lw=2, label="Media de la población")
    ax.axhline(0, color=GRIS, lw=0.8)
    ax.set_xlabel("Generación")
    ax.set_ylabel("Aptitud (fitness)")
    ax.set_title("Evolución de la aptitud de la población")
    ax.legend(loc="lower right")
    fig.savefig(R / "curva_aptitud.png")
    plt.close(fig)


def grafico_victorias(mejores, manual_ent, manual_pru, rng):
    gens = list(range(0, len(mejores), 5)) + [len(mejores) - 1]
    ent, pru = [], []
    for g in gens:
        ent.append(evaluar_genomas(mejores[g], list(ENTRENAMIENTO), 20, rng)["gana_jefe"].mean())
        pru.append(evaluar_genomas(mejores[g], list(PRUEBA), 60, rng)["gana_jefe"].mean())
    x = np.array(gens) + 1
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(x, np.array(ent) * 100, color=AZUL, lw=2, marker="o", ms=3, label="Héroes de entrenamiento")
    ax.plot(x, np.array(pru) * 100, color=NARANJA, lw=2, marker="o", ms=3, label="Héroe nunca visto (prueba)")
    ax.axhline(manual_ent * 100, color=GRIS, lw=1.2, ls="--")
    ax.text(x[-1], manual_ent * 100 + 2, "Jefe con reglas fijas", color=TINTA2, ha="right", fontsize=9)
    ax.set_ylim(0, 105)
    ax.set_xlabel("Generación")
    ax.set_ylabel("Victorias del jefe (%)")
    ax.set_title("Porcentaje de victorias del mejor jefe de cada generación")
    ax.legend(loc="center right")
    fig.savefig(R / "victorias_por_generacion.png")
    plt.close(fig)
    return dict(zip(x.tolist(), zip(ent, pru)))


def comparar_jefes(campeon, mejores, rng):
    jefes = {
        "Quieto (solo dispara)": lambda e: combatir(jefe_quieto, e, rng),
        "Reglas fijas (manual)": lambda e: combatir(jefe_manual, e, rng),
        "Red, generación 1": lambda e: combatir(politica_red(mejores[0], np.zeros(len(e), int)), e, rng),
        f"Red, generación {len(mejores) // 4}": lambda e: combatir(
            politica_red(mejores[len(mejores) // 4 - 1], np.zeros(len(e), int)), e, rng),
        "Red evolucionada (campeón)": lambda e: combatir(politica_red(campeon, np.zeros(len(e), int)), e, rng),
    }
    filas = []
    for nombre, f in jefes.items():
        for estilo in TODOS:
            r = f([estilo] * N_COMBATES)
            filas.append({
                "jefe": nombre, "heroe": estilo,
                "conjunto": "entrenamiento" if estilo in ENTRENAMIENTO else "prueba",
                "victorias_jefe": r["gana_jefe"].mean(),
                "victorias_heroe": r["gana_heroe"].mean(),
                "empates": max(0.0, 1 - r["gana_jefe"].mean() - r["gana_heroe"].mean()),
                "danio_hecho": r["danio_hecho"].mean(),
                "danio_recibido": r["danio_recibido"].mean(),
                "duracion_s": r["duracion"].mean() / C.PASOS_POR_SEGUNDO,
                "precision_embestida": r["embestidas_acertadas"].sum() / max(1, r["embestidas"].sum()),
                "aptitud": r["aptitud"].mean(),
            })
    with open(R / "comparacion.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        for fila in filas:
            w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in fila.items()})
    return filas


def grafico_comparacion(filas):
    gen_media = next(f["jefe"] for f in filas if f["jefe"].startswith("Red, generación") and not f["jefe"].endswith(" 1"))
    series = [("Red, generación 1", GRIS), ("Reglas fijas (manual)", AZUL),
              (gen_media, AQUA), ("Red evolucionada (campeón)", NARANJA)]
    estilos = list(TODOS)
    etiquetas = [e.capitalize() + ("\n(no visto)" if e in PRUEBA else "") for e in estilos]
    x = np.arange(len(estilos))
    w = 0.21
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for i, (nombre, color) in enumerate(series):
        v = [next(f["victorias_jefe"] for f in filas if f["jefe"] == nombre and f["heroe"] == e) * 100
             for e in estilos]
        barras = ax.bar(x + (i - 1.5) * w, v, w - 0.03, color=color, label=nombre, zorder=3)
        ax.bar_label(barras, fmt="%.0f", fontsize=7, color=TINTA2, padding=2)
    ax.set_xticks(x, etiquetas)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Victorias del jefe (%)")
    ax.set_title(f"Victorias del jefe según estilo de héroe ({N_COMBATES} combates c/u)")
    ax.legend(loc="upper center", ncol=2, fontsize=8.5, bbox_to_anchor=(0.5, -0.18))
    ax.grid(axis="x", visible=False)
    fig.savefig(R / "comparacion_jefes.png")
    plt.close(fig)


def grafico_trayectorias(campeon, mejores):
    fig, axs = plt.subplots(1, 2, figsize=(7, 3.7))
    for ax, (titulo, genoma) in zip(axs, [("Generación 1", mejores[0]), ("Campeón (generación final)", campeon)]):
        rng = np.random.default_rng(3)
        res, fotos = combatir(politica_red(genoma, [0]), ["escurridizo"], rng, grabar=True, cada=1)
        j = np.array([f["jefe"] for f in fotos])
        hh = np.array([f["heroe"] for f in fotos])
        ax.plot(hh[:, 0], hh[:, 1], color=GRIS, lw=1, label="Héroe")
        ax.plot(j[:, 0], j[:, 1], color=NARANJA, lw=1.6, label="Jefe")
        ax.plot(*j[0], "o", color=NARANJA, ms=6)
        ax.plot(*hh[0], "o", color=GRIS, ms=5)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(True)
        ganador = "gana el jefe" if res["gana_jefe"][0] else ("gana el héroe" if res["gana_heroe"][0] else "tiempo agotado")
        ax.set_title(f"{titulo}\n{len(fotos) / C.PASOS_POR_SEGUNDO:.1f} s, {ganador}", fontsize=10)
    fig.legend(*axs[0].get_legend_handles_labels(), loc="lower center", ncol=2, fontsize=8.5,
               bbox_to_anchor=(0.5, -0.04))
    fig.suptitle("Recorrido de un combate contra el héroe «escurridizo»", fontweight="bold", fontsize=11)
    fig.savefig(R / "trayectorias.png")
    plt.close(fig)


def main():
    rng = np.random.default_rng(2024)
    campeon = np.load(R / "campeon.npy")
    mejores = np.load(R / "mejores_por_generacion.npy")
    h = leer_historial()

    grafico_aptitud(h)
    filas = comparar_jefes(campeon, mejores, rng)
    man = [f for f in filas if f["jefe"].startswith("Reglas")]
    man_ent = np.mean([f["victorias_jefe"] for f in man if f["conjunto"] == "entrenamiento"])
    man_pru = np.mean([f["victorias_jefe"] for f in man if f["conjunto"] == "prueba"])
    grafico_victorias(mejores, man_ent, man_pru, rng)
    grafico_comparacion(filas)
    grafico_trayectorias(campeon, mejores)

    print(f"{'jefe':30s} {'héroe':14s} {'victorias':>9s} {'daño hecho':>10s} {'duración':>8s}")
    for f in filas:
        print(f"{f['jefe']:30s} {f['heroe']:14s} {f['victorias_jefe']:9.0%} {f['danio_hecho']:10.1f} "
              f"{f['duracion_s']:7.1f}s")


if __name__ == "__main__":
    main()
