"""Jugá contra el jefe, o mirá cómo pelea contra los héroes bot.

    python jugar.py                       # menú (o ./jugar.sh)
    python jugar.py --gen 1               # directo contra el jefe de la generación 1
    python jugar.py --bot escurridizo     # directo: campeón vs. bot

Menú: ↑/↓ elige el jefe, ←/→ elige quién pelea, Enter empieza.
En combate: WASD/flechas para moverte, mouse para apuntar, clic o espacio para
disparar. R reinicia, P pausa, S sonido, +/- velocidad (al mirar), Esc vuelve al menú.

Cuando jugás vos, el combate dura 60 s y tus balas pegan más fuerte que las de
los bots: el balance original está pensado para bots, que apuntan casi perfecto.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pygame

from jefe import config as C
from jefe.arena import Arena
from jefe.jugadores import TODOS, HeroeBot
from jefe.red import RedesEnLote
from jefe.render import AZUL, BLANCO, GRIS, NARANJA, Escena, Sonidos
from jefe.simulacion import politica_heroe_red

R = Path(__file__).parent / "resultados"
LADO = 700
ANCHO, ALTO = LADO + 20, LADO + 60


def cargar_jefes():
    mejores = np.load(R / "mejores_por_generacion.npy")
    jefes = [("Fácil · generación 1", mejores[0]),
             ("Medio · generación 50", mejores[min(49, len(mejores) - 1)]),
             ("Difícil · campeón", np.load(R / "campeon.npy"))]
    for carpeta, nombre in (("coevolucion", "Coevolucionado"), ("en_vivo", "Tu evolución en vivo")):
        archivo = R / carpeta / "jefe_final.npy"
        if archivo.exists():
            jefes.append((nombre, np.load(archivo)))
    return jefes


def cargar_heroes():
    heroes = [("Jugador", None)] + [(f"Bot {e}", e) for e in TODOS]
    for carpeta, nombre in (("coevolucion", "Héroe coevolucionado"), ("en_vivo", "Héroe de tu evolución")):
        archivo = R / carpeta / "heroe_final.npy"
        if archivo.exists():
            heroes.append((nombre, np.load(archivo)))
    return heroes


def comando_humano(ar):
    k = pygame.key.get_pressed()
    vx = (k[pygame.K_d] or k[pygame.K_RIGHT]) - (k[pygame.K_a] or k[pygame.K_LEFT])
    vy = (k[pygame.K_w] or k[pygame.K_UP]) - (k[pygame.K_s] or k[pygame.K_DOWN])
    mx, my = pygame.mouse.get_pos()
    ox, oy = (mx - 10) / LADO, 1 - (my - 10) / LADO
    ang = np.arctan2(oy - ar.hy[0], ox - ar.hx[0])
    disparar = pygame.mouse.get_pressed()[0] or k[pygame.K_SPACE]
    return {"vx": np.array([float(vx)]), "vy": np.array([float(vy)]),
            "disparar": np.array([bool(disparar)]), "angulo": np.array([ang])}


class Combate:
    def __init__(self, jefe, heroe, escena):
        self.jefe, self.heroe = jefe, heroe
        (self.nombre_j, genoma_j), (self.nombre_h, h) = jefe, heroe
        self.humano = h is None
        rng = np.random.default_rng()
        if self.humano:
            self.ar = Arena(1, rng, duracion=C.HUMANO_DURACION, heroe_danio=C.HUMANO_BALA_DANIO)
            self.pol_h = comando_humano
        elif isinstance(h, str):
            self.ar, self.pol_h = Arena(1, rng), HeroeBot([h], rng)
        else:
            self.ar, self.pol_h = Arena(1, rng), politica_heroe_red(h, [0])
        self.red = RedesEnLote(genoma_j, [0])
        self.escena = escena
        escena.reiniciar()
        self.resultado = None

    def paso(self):
        if not self.ar.activa[0]:
            return
        self.ar.paso(self.red(self.ar.observar()), self.pol_h(self.ar))
        self.escena.actualizar(self.ar.foto(0))
        if not self.ar.activa[0]:
            r = self.ar.resultados()
            self.resultado = "heroe" if r["gana_heroe"][0] else ("jefe" if r["gana_jefe"][0] else "empate")

    def mensaje(self):
        if self.resultado is None:
            return ""
        if self.humano:
            return {"heroe": "¡GANASTE!", "jefe": "TE DESTRUYÓ", "empate": "TIEMPO"}[self.resultado]
        return {"heroe": "GANA EL HÉROE", "jefe": "GANA EL JEFE", "empate": "TIEMPO"}[self.resultado]


def dibujar_menu(pantalla, fuentes, jefes, heroes, ij, ih, marcador):
    f_t, f_m, f_c = fuentes
    pantalla.fill((14, 14, 20))
    t = f_t.render("JEFE EVOLUTIVO", True, NARANJA)
    pantalla.blit(t, (ANCHO // 2 - t.get_width() // 2, 70))
    s = f_c.render("un enemigo que aprendió a pelear con un algoritmo genético", True, GRIS)
    pantalla.blit(s, (ANCHO // 2 - s.get_width() // 2, 130))
    for col, (titulo, items, sel, color, tecla) in enumerate([
            ("JEFE", jefes, ij, NARANJA, "↑ ↓"), ("HÉROE", heroes, ih, AZUL, "← →")]):
        x = 90 + col * 300
        pantalla.blit(f_m.render(f"{titulo}  ({tecla})", True, color), (x, 200))
        for i, (nombre, _) in enumerate(items):
            c = BLANCO if i == sel else (90, 90, 105)
            pantalla.blit(f_m.render(("▶ " if i == sel else "   ") + nombre, True, c), (x, 245 + i * 34))
    ayuda = ["Enter: pelear    E: ver la evolución en vivo    Esc: salir",
             "En combate: WASD + mouse, clic/espacio dispara, R reinicia, P pausa, S sonido",
             "Mirando bots: + / - cambia la velocidad"]
    for i, a in enumerate(ayuda):
        t = f_c.render(a, True, GRIS)
        pantalla.blit(t, (ANCHO // 2 - t.get_width() // 2, ALTO - 120 + i * 24))
    if marcador:
        t = f_c.render("Tu marcador: " + "   ".join(f"{k}: {v[0]}-{v[1]}" for k, v in marcador.items()), True, BLANCO)
        pantalla.blit(t, (ANCHO // 2 - t.get_width() // 2, ALTO - 170))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", type=int, default=None, help="jugar directo contra el mejor jefe de esa generación")
    ap.add_argument("--bot", choices=list(TODOS), default=None, help="mirar directo al campeón contra ese bot")
    ap.add_argument("--cuadros", type=int, default=0, help="(pruebas) cerrar tras N cuadros")
    args = ap.parse_args()

    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Jefe evolutivo")
    reloj = pygame.time.Clock()
    fuentes = (pygame.font.SysFont("DejaVu Sans", 46, bold=True), pygame.font.SysFont("DejaVu Sans", 20),
               pygame.font.SysFont("DejaVu Sans", 15))
    sonidos = Sonidos()
    escena = Escena(LADO, (10, 10), sonidos)
    jefes, heroes = cargar_jefes(), cargar_heroes()
    en_vivo = None                                                # proceso de en_vivo.py, si está abierto
    ij, ih, marcador = 2, 0, {}
    combate, pausa, velocidad, cuadro = None, False, 1, 0

    if args.gen is not None:
        g = np.load(R / "mejores_por_generacion.npy")[args.gen - 1]
        combate = Combate((f"Generación {args.gen}", g), heroes[0], escena)
    elif args.bot:
        combate = Combate(jefes[2], (f"Bot {args.bot}", args.bot), escena)

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); return
            if ev.type != pygame.KEYDOWN:
                continue
            if combate is None:                                   # --- menú
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit(); return
                if ev.key == pygame.K_UP: ij = (ij - 1) % len(jefes)
                if ev.key == pygame.K_DOWN: ij = (ij + 1) % len(jefes)
                if ev.key == pygame.K_LEFT: ih = (ih - 1) % len(heroes)
                if ev.key == pygame.K_RIGHT: ih = (ih + 1) % len(heroes)
                if ev.key == pygame.K_e and en_vivo is None:
                    en_vivo = subprocess.Popen([sys.executable, str(Path(__file__).parent / "en_vivo.py")])
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    combate, velocidad = Combate(jefes[ij], heroes[ih], escena), 1
            else:                                                 # --- combate
                if ev.key == pygame.K_ESCAPE: combate = None
                elif ev.key == pygame.K_r or (ev.key == pygame.K_RETURN and combate.resultado):
                    combate = Combate(combate.jefe, combate.heroe, escena)
                elif ev.key == pygame.K_p: pausa = not pausa
                elif ev.key == pygame.K_s: sonidos.activo = not sonidos.activo
                elif ev.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS) and not combate.humano:
                    velocidad = min(8, velocidad * 2)
                elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS) and not combate.humano:
                    velocidad = max(1, velocidad // 2)

        if en_vivo is not None and en_vivo.poll() is not None:   # se cerró: cargar sus campeones
            en_vivo = None
            jefes, heroes = cargar_jefes(), cargar_heroes()
            ij, ih = min(ij, len(jefes) - 1), min(ih, len(heroes) - 1)
        if combate is None:
            dibujar_menu(pantalla, fuentes, jefes, heroes, ij, ih, marcador)
        else:
            if not pausa:
                antes = combate.resultado
                for _ in range(velocidad):
                    combate.paso()
                if antes is None and combate.resultado and combate.humano:
                    m = marcador.setdefault(combate.nombre_j.split(" ·")[0], [0, 0])
                    m[0 if combate.resultado == "heroe" else 1] += 1
            pantalla.fill((8, 8, 12))
            f = combate.ar.foto(0)
            sub = combate.mensaje() or ("PAUSA" if pausa else "")
            escena.dibujar(pantalla, f, titulo=f"{combate.nombre_j}  vs.  {combate.nombre_h}"
                           + (f"   x{velocidad}" if velocidad > 1 else ""),
                           subtitulo=sub, nombres=("Jefe", "Jugador" if combate.humano else "Héroe"))
            ayuda = "R: otra vez   Esc: menú" if combate.resultado else \
                ("WASD + mouse · clic dispara · P pausa · S sonido · Esc menú" if combate.humano
                 else "+/- velocidad · P pausa · S sonido · Esc menú")
            t = fuentes[2].render(ayuda, True, GRIS)
            pantalla.blit(t, (ANCHO // 2 - t.get_width() // 2, ALTO - 22))
        pygame.display.flip()
        reloj.tick(C.PASOS_POR_SEGUNDO)
        cuadro += 1
        if args.cuadros and cuadro >= args.cuadros:
            if os.environ.get("CAPTURA"):
                pygame.image.save(pantalla, os.environ["CAPTURA"])
            pygame.quit(); return


if __name__ == "__main__":
    main()
