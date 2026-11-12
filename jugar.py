"""¡Enfrentá vos mismo al jefe!

    python jugar.py                 # contra el campeón
    python jugar.py --gen 1         # contra el mejor jefe de la generación 1
    python jugar.py --gen 50
    python jugar.py --bot escurridizo   # mirar al jefe contra un héroe bot

Controles: WASD o flechas para moverse, apuntar con el mouse, clic (o barra
espaciadora) para disparar. R reinicia, Esc sale.
"""
import argparse
from pathlib import Path

import numpy as np
import pygame

from jefe import config as C
from jefe.arena import Arena
from jefe.jugadores import TODOS, HeroeBot
from jefe.red import RedesEnLote

R = Path(__file__).parent / "resultados"
LADO = 640


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", type=int, default=None, help="generación (por defecto: el campeón)")
    ap.add_argument("--bot", choices=list(TODOS), default=None,
                    help="en vez de jugar vos, mirar al jefe contra un héroe bot")
    ap.add_argument("--cuadros", type=int, default=0, help="(pruebas) cerrar tras N cuadros")
    args = ap.parse_args()

    if args.gen is None:
        genoma, nombre = np.load(R / "campeon.npy"), "Campeón"
    else:
        genoma, nombre = np.load(R / "mejores_por_generacion.npy")[args.gen - 1], f"Generación {args.gen}"
    red = RedesEnLote(genoma, [0])

    pygame.init()
    pantalla = pygame.display.set_mode((LADO, LADO + 50))
    pygame.display.set_caption(f"Jefe evolutivo - {nombre}")
    reloj = pygame.time.Clock()
    letra = pygame.font.SysFont(None, 26)
    p = lambda x, y: (int(x * LADO), int(50 + (1 - y) * LADO))

    def nueva():
        rng = np.random.default_rng()
        return Arena(1, rng), (HeroeBot([args.bot], rng) if args.bot else None)

    ar, bot = nueva()
    if args.bot:
        nombre += f" vs. bot «{args.bot}»"
    mensaje, cuadro = "", 0
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                pygame.quit(); return
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
                (ar, bot), mensaje = nueva(), ""

        if ar.activa[0] and bot is not None:
            ar.paso(red(ar.observar()), bot(ar))
            if not ar.activa[0]:
                r = ar.resultados()
                mensaje = ("Ganó el bot" if r["gana_heroe"][0] else
                           "Ganó el jefe" if r["gana_jefe"][0] else "Tiempo agotado") + "  (R para repetir)"
        elif ar.activa[0]:
            k = pygame.key.get_pressed()
            vx = (k[pygame.K_d] or k[pygame.K_RIGHT]) - (k[pygame.K_a] or k[pygame.K_LEFT])
            vy = (k[pygame.K_w] or k[pygame.K_UP]) - (k[pygame.K_s] or k[pygame.K_DOWN])
            mx, my = pygame.mouse.get_pos()
            objetivo = (mx / LADO, 1 - (my - 50) / LADO)
            ang = np.arctan2(objetivo[1] - ar.hy[0], objetivo[0] - ar.hx[0])
            disparar = pygame.mouse.get_pressed()[0] or k[pygame.K_SPACE]
            cmd = {"vx": np.array([float(vx)]), "vy": np.array([float(vy)]),
                   "disparar": np.array([bool(disparar)]), "angulo": np.array([ang])}
            ar.paso(red(ar.observar()), cmd)
            if not ar.activa[0]:
                r = ar.resultados()
                mensaje = ("¡Ganaste!" if r["gana_heroe"][0] else
                           "El jefe te venció" if r["gana_jefe"][0] else "Tiempo agotado") + "  (R para reintentar)"

        f = ar.foto(0)
        pantalla.fill((24, 24, 30))
        pantalla.blit(letra.render(f"{nombre}   t={f['t'] / C.PASOS_POR_SEGUNDO:4.1f}s   {mensaje}",
                                   True, (230, 230, 230)), (10, 6))
        for i, (v, col) in enumerate([(f["jvida"], (235, 104, 52)), (f["hvida"], (90, 160, 240))]):
            pygame.draw.rect(pantalla, col, (10 + i * 320, 32, int(300 * v), 10))
        for x, y in f["balas_jefe"]:
            pygame.draw.circle(pantalla, (255, 140, 100), p(x, y), 5)
        for x, y in f["balas_heroe"]:
            pygame.draw.circle(pantalla, (170, 210, 255), p(x, y), 3)
        pygame.draw.circle(pantalla, (90, 160, 240), p(*f["heroe"]), int(C.HEROE_RADIO * LADO))
        pygame.draw.circle(pantalla, (255, 210, 90) if f["embistiendo"] else (235, 104, 52),
                           p(*f["jefe"]), int(C.JEFE_RADIO * LADO))
        pygame.display.flip()
        reloj.tick(C.PASOS_POR_SEGUNDO)
        cuadro += 1
        if args.cuadros and cuadro >= args.cuadros:
            pygame.quit(); return


if __name__ == "__main__":
    main()
