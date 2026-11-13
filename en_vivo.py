"""Coevolución en vivo: jefes y héroes evolucionan mientras mirás cómo pelean.

    python en_vivo.py                 # 300 generaciones
    python en_vivo.py --gen 500 --semilla 3

A la izquierda: el mejor jefe contra el mejor héroe de la última generación.
A la derecha: cómo va la "carrera armamentista".
Espacio pausa el entrenamiento, +/- cambia la velocidad del combate, N salta al
último campeón, S sonido, Esc sale. Guarda en resultados/en_vivo/ y esos campeones aparecen en el menú de jugar.py.
"""
import argparse
import os
import multiprocessing as mp
import queue
from pathlib import Path

import numpy as np
import pygame

from jefe import config as C

CARPETA = Path(__file__).parent / "resultados" / "en_vivo"   # no pisa la corrida del informe
ANCHO, ALTO, LADO = 1280, 760, 700


def trabajador(cola, pausa, parar, semilla, generaciones):
    from jefe.coevolucion import Coevolucion
    co = Coevolucion(semilla=semilla, generaciones_previstas=generaciones)
    while co.gen < generaciones and not parar.is_set():
        if pausa.is_set():
            parar.wait(0.1)
            continue
        fila, j, h = co.paso()
        cola.put((fila, j, h))
        if co.gen % 10 == 0:
            co.guardar(CARPETA)
    co.guardar(CARPETA)
    cola.put(("fin", co.gen))


def grafico(pantalla, fuente, rect, titulo, series, n_total):
    x, y, w, h = rect
    pygame.draw.rect(pantalla, (20, 20, 28), rect, border_radius=8)
    pantalla.blit(fuente.render(titulo, True, (220, 220, 230)), (x + 12, y + 8))
    gx, gy, gw, gh = x + 44, y + 36, w - 60, h - 60
    for v in (0, 50, 100):
        yy = gy + gh - gh * v / 100
        pygame.draw.line(pantalla, (40, 40, 52), (gx, yy), (gx + gw, yy))
        pantalla.blit(fuente.render(f"{v}%", True, (110, 110, 125)), (x + 6, yy - 8))
    n = max(n_total, 2)
    xl = x + w - 12
    for nombre, valores, color in reversed(series):
        pts = [(gx + gw * k / (n - 1), gy + gh - gh * v) for k, v in enumerate(valores) if v == v]
        if len(pts) > 1:
            pygame.draw.lines(pantalla, color, False, pts, 2)
        t = fuente.render("● " + nombre, True, color)
        xl -= t.get_width() + 14
        pantalla.blit(t, (xl + 14, y + h - 22))
    pantalla.blit(fuente.render("generación →", True, (110, 110, 125)), (gx, y + h - 22))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", type=int, default=300)
    ap.add_argument("--semilla", type=int, default=7)
    ap.add_argument("--cuadros", type=int, default=0, help="(pruebas) cerrar tras N cuadros")
    args = ap.parse_args()

    from jefe.arena import Arena
    from jefe.red import RedesEnLote
    from jefe.render import AZUL, BLANCO, GRIS, NARANJA, Escena, Sonidos
    from jefe.simulacion import politica_heroe_red

    cola, pausa, parar = mp.Queue(), mp.Event(), mp.Event()
    proc = mp.Process(target=trabajador, args=(cola, pausa, parar, args.semilla, args.gen), daemon=True)
    proc.start()

    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Jefe evolutivo · coevolución en vivo")
    reloj = pygame.time.Clock()
    f_g = pygame.font.SysFont("DejaVu Sans", 34, bold=True)
    f_m = pygame.font.SysFont("DejaVu Sans", 18, bold=True)
    f_c = pygame.font.SysFont("DejaVu Sans", 14)
    sonidos = Sonidos()
    sonidos.activo = False
    escena = Escena(LADO, (20, 20), sonidos)

    historial, ultimo, terminado = [], None, False
    combate, gen_combate, espera, velocidad, cuadro = None, 0, 0, 2, 0

    def nuevo_combate():
        nonlocal combate, gen_combate
        fila, j, h = ultimo
        ar = Arena(1, np.random.default_rng())
        combate = (ar, RedesEnLote(j, [0]), politica_heroe_red(h, [0]))
        gen_combate = fila["generacion"]
        escena.reiniciar()

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                parar.set(); proc.join(timeout=10); pygame.quit(); return
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_SPACE:
                    pausa.clear() if pausa.is_set() else pausa.set()
                elif ev.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                    velocidad = min(16, velocidad * 2)
                elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    velocidad = max(1, velocidad // 2)
                elif ev.key == pygame.K_n and ultimo:
                    nuevo_combate()
                elif ev.key == pygame.K_s:
                    sonidos.activo = not sonidos.activo

        try:
            while True:
                msg = cola.get_nowait()
                if msg[0] == "fin":
                    terminado = True
                else:
                    ultimo = msg
                    historial.append(msg[0])
        except queue.Empty:
            pass

        pantalla.fill((8, 8, 12))
        # ---------------------------------------------------------- combate
        if combate is None and ultimo:
            nuevo_combate()
        if combate:
            ar, red_j, pol_h = combate
            for _ in range(velocidad):
                if ar.activa[0]:
                    ar.paso(red_j(ar.observar()), pol_h(ar))
                    escena.actualizar(ar.foto(0), sacudir_heroe=False)
            msg = ""
            if not ar.activa[0]:
                r = ar.resultados()
                msg = "GANA EL JEFE" if r["gana_jefe"][0] else ("GANA EL HÉROE" if r["gana_heroe"][0] else "TIEMPO")
                espera += 1
                if espera > 45:
                    espera = 0
                    nuevo_combate()
            escena.dibujar(pantalla, ar.foto(0), titulo=f"campeones de la generación {gen_combate}   x{velocidad}",
                           subtitulo=msg, nombres=("Mejor jefe", "Mejor héroe"))
        else:
            t = f_m.render("Arrancando la evolución…", True, GRIS)
            pantalla.blit(t, (20 + LADO // 2 - t.get_width() // 2, 20 + LADO // 2))

        # ---------------------------------------------------------- panel
        x0 = LADO + 50
        pantalla.blit(f_m.render("COEVOLUCIÓN EN VIVO", True, GRIS), (x0, 24))
        g = historial[-1]["generacion"] if historial else 0
        pantalla.blit(f_g.render(f"Generación {g}", True, BLANCO), (x0, 50))
        estado = "terminó" if terminado else ("en pausa" if pausa.is_set() else "evolucionando…")
        pantalla.blit(f_c.render(f"{estado}   ·   {C.COEVO_POBLACION} jefes y {C.COEVO_POBLACION} héroes por generación",
                                 True, GRIS), (x0, 96))
        n = max(args.gen, 2)
        grafico(pantalla, f_c, (x0, 130, ANCHO - x0 - 20, 260),
                "Quién gana entre las poblaciones actuales",
                [("jefes", [h["victorias_jefes"] for h in historial], NARANJA),
                 ("héroes", [h["victorias_heroes"] for h in historial], AZUL)], n)
        grafico(pantalla, f_c, (x0, 405, ANCHO - x0 - 20, 260),
                "Examen contra rivales fijos (progreso real)",
                [("jefe vs. bots", [h["examen_jefe"] for h in historial], NARANJA),
                 ("héroe vs. jefe de reglas", [h["examen_heroe"] for h in historial], AZUL)], n)
        ayuda = "Espacio: pausa   +/-: velocidad   N: último campeón   S: sonido   Esc: salir"
        pantalla.blit(f_c.render(ayuda, True, GRIS), (x0, ALTO - 40))

        pygame.display.flip()
        reloj.tick(C.PASOS_POR_SEGUNDO)
        cuadro += 1
        if args.cuadros and cuadro >= args.cuadros:
            if os.environ.get("CAPTURA"):
                pygame.image.save(pantalla, os.environ["CAPTURA"])
            parar.set(); proc.join(timeout=10); pygame.quit(); return


if __name__ == "__main__":
    main()
