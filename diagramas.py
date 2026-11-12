"""Genera los diagramas conceptuales del informe en resultados/."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

R = Path(__file__).parent / "resultados"
AZUL, NARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
TINTA, TINTA2, BORDE = "#0b0b0b", "#52514e", "#bdbcb6"
plt.rcParams.update({"font.family": "DejaVu Sans", "figure.dpi": 150, "savefig.bbox": "tight"})


def caja(ax, x, y, w, h, texto, color, sub=None):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.04",
                                fc=color + "22", ec=color, lw=1.5))
    ax.text(x, y + (0.035 if sub else 0), texto, ha="center", va="center", fontsize=10, fontweight="bold", color=TINTA)
    if sub:
        ax.text(x, y - (0.07 if "\n" in sub else 0.05), sub, ha="center", va="center", fontsize=8, color=TINTA2)


def flecha(ax, a, b, texto=None, curva=0.0, dx=0, dy=0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=12, lw=1.3, color=TINTA2,
                                 connectionstyle=f"arc3,rad={curva}"))
    if texto:
        ax.text((a[0] + b[0]) / 2 + dx, (a[1] + b[1]) / 2 + dy, texto, ha="center", va="center",
                fontsize=8, color=TINTA2, style="italic")


def ciclo_agente():
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.set_xlim(0, 1); ax.set_ylim(0.05, 1.12); ax.axis("off")
    caja(ax, 0.17, 0.72, 0.26, 0.2, "Arena (entorno)", AZUL, "jefe, héroe, balas")
    caja(ax, 0.5, 0.72, 0.26, 0.2, "Red neuronal", NARANJA, "15 → 16 → 5")
    caja(ax, 0.83, 0.72, 0.26, 0.2, "Acciones", NARANJA, "mover, embestir,\ndisparar, apuntar")
    caja(ax, 0.5, 0.2, 0.28, 0.2, "Algoritmo genético", AQUA, "selección · cruce · mutación")
    caja(ax, 0.17, 0.2, 0.26, 0.2, "Aptitud", AQUA, "daño, victoria, rapidez")
    flecha(ax, (0.30, 0.72), (0.37, 0.72), "percepciones", dy=-0.14)
    flecha(ax, (0.63, 0.72), (0.70, 0.72))
    flecha(ax, (0.83, 0.83), (0.17, 0.83), "las acciones modifican el entorno (30 veces por segundo)", curva=0.3, dy=0.25)
    flecha(ax, (0.17, 0.62), (0.17, 0.30), "fin del combate", dx=-0.09)
    flecha(ax, (0.30, 0.2), (0.35, 0.2))
    flecha(ax, (0.5, 0.30), (0.5, 0.62), "nuevos pesos\n(genoma)", dx=0.08)
    ax.text(0.68, 0.2, "Bucle rápido: el jefe juega.\nBucle lento: la especie evoluciona.",
            ha="left", va="center", fontsize=8, color=TINTA2)
    fig.savefig(R / "diagrama_agente.png")
    plt.close(fig)


def red():
    entradas = ["Δx héroe", "Δy héroe", "distancia", "vel. x héroe", "vel. y héroe", "Δx bala", "Δy bala",
                "dir. x bala", "dir. y bala", "pos. x propia", "pos. y propia", "¿embestida lista?",
                "¿disparo listo?", "vida propia", "vida héroe"]
    salidas = ["mover x", "mover y", "embestir", "disparar", "ajuste puntería"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.axis("off"); ax.set_xlim(-0.35, 1.3); ax.set_ylim(-0.05, 1.05)
    capas = [(0.0, len(entradas)), (0.5, 16), (1.0, len(salidas))]
    pos = []
    for x, n in capas:
        ys = [1 - (i + 0.5) / n for i in range(n)]
        pos.append([(x, y) for y in ys])
    for a, b in [(0, 1), (1, 2)]:
        for p in pos[a]:
            for q in pos[b]:
                ax.plot([p[0], q[0]], [p[1], q[1]], color=BORDE, lw=0.25, alpha=0.6, zorder=1)
    for i, (capa, color) in enumerate(zip(pos, [AZUL, TINTA2, NARANJA])):
        for x, y in capa:
            ax.scatter(x, y, s=55, color="white", edgecolor=color, lw=1.4, zorder=3)
    for (x, y), t in zip(pos[0], entradas):
        ax.text(x - 0.04, y, t, ha="right", va="center", fontsize=7.5, color=TINTA)
    for (x, y), t in zip(pos[2], salidas):
        ax.text(x + 0.04, y, t, ha="left", va="center", fontsize=8, color=TINTA)
    for x, t in [(0, "Entradas (15)\npercepciones"), (0.5, "Capa oculta (16)\ntanh"), (1.0, "Salidas (5)\ntanh ∈ [-1, 1]")]:
        ax.text(x, 1.04, t, ha="center", va="bottom", fontsize=9, fontweight="bold", color=TINTA)
    ax.text(0.5, -0.05, "15×16 + 16 + 16×5 + 5 = 341 pesos = 341 genes del cromosoma",
            ha="center", fontsize=8.5, color=TINTA2)
    fig.savefig(R / "diagrama_red.png")
    plt.close(fig)


def ciclo_ag():
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.set_xlim(0, 1); ax.set_ylim(-0.05, 1); ax.axis("off")
    pasos = [("Población", "80 redes\nal azar"), ("Evaluación", "6 combates\nc/u"),
             ("Selección", "torneo\nde 4"), ("Cruce", "uniforme\np = 0,8"), ("Mutación", "gaussiana\nσ decreciente")]
    xs = [0.1 + i * 0.2 for i in range(5)]
    for x, (t, s) in zip(xs, pasos):
        caja(ax, x, 0.62, 0.15, 0.4, t, AQUA if t != "Evaluación" else NARANJA, s)
    for a, b in zip(xs, xs[1:]):
        flecha(ax, (a + 0.085, 0.62), (b - 0.085, 0.62))
    flecha(ax, (xs[-1], 0.38), (xs[0], 0.38), "nueva generación (los 4 mejores pasan intactos: elitismo) · se repite 200 veces",
           curva=-0.18, dy=-0.33)
    fig.savefig(R / "diagrama_ag.png")
    plt.close(fig)


if __name__ == "__main__":
    R.mkdir(exist_ok=True)
    ciclo_agente(); red(); ciclo_ag()
    print("Diagramas guardados en", R)
