"""Graba un GIF comparando al jefe de la generación 1 con el campeón.

    python grabar.py                       # resultados/gen1_vs_campeon.gif
    python grabar.py --heroe francotirador --semilla 5

También guarda resultados/secuencia.png, una tira de cuadros para el informe.
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from jefe import config as C
from jefe.simulacion import combatir, politica_red

R = Path(__file__).parent / "resultados"
LADO = 300
FONDO, BORDE = (24, 24, 30), (70, 70, 80)
JEFE, JEFE_EMB = (235, 104, 52), (255, 210, 90)
HEROE = (90, 160, 240)
BALA_J, BALA_H = (255, 140, 100), (170, 210, 255)


def fuente(tam):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", tam)
    except OSError:
        return ImageFont.load_default()


def dibujar(foto, titulo):
    im = Image.new("RGB", (LADO, LADO + 40), FONDO)
    d = ImageDraw.Draw(im)
    p = lambda x, y: (x * LADO, 40 + (1 - y) * LADO)          # y hacia arriba
    d.rectangle([0, 40, LADO - 1, LADO + 39], outline=BORDE)
    d.text((8, 4), titulo, fill=(240, 240, 240), font=fuente(13))
    d.text((8, 22), f"t = {foto['t'] / C.PASOS_POR_SEGUNDO:4.1f} s", fill=(160, 160, 170), font=fuente(10))
    # Barras de vida
    for i, (v, col, et) in enumerate([(foto["jvida"], JEFE, "Jefe"), (foto["hvida"], HEROE, "Héroe")]):
        x0 = 140 + i * 80
        d.text((x0, 4), et, fill=col, font=fuente(10))
        d.rectangle([x0, 20, x0 + 70, 28], outline=BORDE)
        d.rectangle([x0, 20, x0 + 70 * v, 28], fill=col)
    for x, y in foto["balas_jefe"]:
        cx, cy = p(x, y); r = 3
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BALA_J)
    for x, y in foto["balas_heroe"]:
        cx, cy = p(x, y); r = 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BALA_H)
    cx, cy = p(*foto["heroe"]); r = C.HEROE_RADIO * LADO
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=HEROE)
    cx, cy = p(*foto["jefe"]); r = C.JEFE_RADIO * LADO
    col = JEFE_EMB if foto["embistiendo"] else JEFE
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    return im


def partida(genoma, heroe, semilla):
    rng = np.random.default_rng(semilla)
    _, fotos = combatir(politica_red(genoma, [0]), [heroe], rng, grabar=True, cada=2)
    return fotos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--heroe", default="escurridizo")
    ap.add_argument("--semilla", type=int, default=3)
    args = ap.parse_args()

    mejores = np.load(R / "mejores_por_generacion.npy")
    campeon = np.load(R / "campeon.npy")
    a = partida(mejores[0], args.heroe, args.semilla)
    b = partida(campeon, args.heroe, args.semilla)
    n = max(len(a), len(b))
    cuadros = []
    for i in range(n):
        fa = dibujar(a[min(i, len(a) - 1)], "Generación 1")
        fb = dibujar(b[min(i, len(b) - 1)], f"Campeón (gen {len(mejores)})")
        im = Image.new("RGB", (LADO * 2 + 10, LADO + 40), (12, 12, 16))
        im.paste(fa, (0, 0)); im.paste(fb, (LADO + 10, 0))
        cuadros.append(im)
    cuadros += [cuadros[-1]] * 30
    cuadros[0].save(R / "gen1_vs_campeon.gif", save_all=True, append_images=cuadros[1:], duration=66, loop=0)

    # Tira de 4 cuadros del campeón para el informe
    idx = np.linspace(0, len(b) - 1, 4).astype(int)
    tira = Image.new("RGB", (LADO * 4 + 30, LADO + 40), (255, 255, 255))
    for k, i in enumerate(idx):
        tira.paste(dibujar(b[i], f"Campeón"), (k * (LADO + 10), 0))
    tira.save(R / "secuencia.png")
    print(f"GIF: {R / 'gen1_vs_campeon.gif'} ({n} cuadros)")


if __name__ == "__main__":
    main()
