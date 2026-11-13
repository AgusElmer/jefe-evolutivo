"""Jugá contra el jefe, o mirá cómo pelea contra los héroes bot.

    python jugar.py                       # menú (o ./jugar.sh)
    python jugar.py --gen 1               # directo contra el jefe de la generación 1
    python jugar.py --bot escurridizo     # directo: campeón vs. bot

Menú: ↑/↓ y Enter para elegir, Esc para volver.
En combate: WASD/flechas para moverte, mouse para apuntar, clic o espacio para
disparar. R reinicia, P pausa, M sonido, +/- velocidad (al mirar), Esc vuelve al menú.

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
from jefe.jugadores import HEROES, HeroeBot
from jefe.red import RedesEnLote
from jefe.render import AZUL, BLANCO, GRIS, NARANJA, Escena, Sonidos
from jefe.simulacion import politica_heroe_red

R = Path(__file__).parent / "resultados"
LADO = 700
ANCHO, ALTO = LADO + 20, LADO + 60


def _cargar(*partes):
    archivo = R.joinpath(*partes)
    return np.load(archivo) if archivo.exists() else None


def opciones():
    """Arma las tres pantallas del menú con lo que haya entrenado en resultados/."""
    mejores = np.load(R / "mejores_por_generacion.npy")
    gen1, gen50, campeon = mejores[0], mejores[min(49, len(mejores) - 1)], np.load(R / "campeon.npy")
    revancha = _cargar("revancha", "jefe_final.npy")
    jugador = ("Jugador", None)

    jugar = [("Fácil", "el jefe recién nacido (generación 1)", ("Fácil", gen1), jugador),
             ("Medio", "el jefe de la generación 50", ("Medio", gen50), jugador),
             ("Difícil", "el campeón (generación 200)", ("Difícil", campeon), jugador)]
    if revancha is not None:
        jugar.append(("Revancha", "entrenado contra la estrategia de kitear", ("Revancha", revancha), jugador))

    bot = lambda e: (f"Bot {e}", e)
    mirar = [("Recién nacido vs. bot", "así pelea sin entrenar", ("Generación 1", gen1), bot("escurridizo")),
             ("Campeón vs. bot", "el mismo rival, 200 generaciones después", ("Campeón", campeon), bot("escurridizo")),
             ("Campeón vs. kiteador", "la debilidad que encontré jugando", ("Campeón", campeon), bot("kiteador"))]
    if revancha is not None:
        mirar.append(("Revancha vs. kiteador", "el jefe que aprendió a enfrentarla", ("Revancha", revancha), bot("kiteador")))
    for carpeta, titulo, desc in (("coevolucion", "Coevolucionados", "jefe y héroe que aprendieron juntos"),
                                  ("en_vivo", "Tu evolución en vivo", "los campeones de tu última corrida")):
        j, h = _cargar(carpeta, "jefe_final.npy"), _cargar(carpeta, "heroe_final.npy")
        if j is not None and h is not None:
            mirar.append((titulo, desc, ("Jefe " + titulo.lower(), j), ("Héroe", h)))
    principal = [("Jugar", "enfrentá al jefe con teclado y mouse", "jugar", None),
                 ("Mirar una pelea", "peleas entre jefes y héroes que aprendieron solos", "mirar", None),
                 ("Ver la evolución en vivo", "jefes y héroes aprenden mientras mirás", "en_vivo", None)]
    return {"principal": principal, "jugar": jugar, "mirar": mirar}


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


TITULOS = {"principal": "", "jugar": "ELEGÍ LA DIFICULTAD", "mirar": "ELEGÍ UNA PELEA"}


def dibujar_menu(pantalla, fuentes, pantalla_menu, items, sel, marcador):
    f_t, f_m, f_c = fuentes
    pantalla.fill((14, 14, 20))
    t = f_t.render("JEFE EVOLUTIVO", True, NARANJA)
    pantalla.blit(t, (ANCHO // 2 - t.get_width() // 2, 70))
    sub = TITULOS[pantalla_menu] or "un enemigo que aprendió a pelear con un algoritmo genético"
    s = f_c.render(sub, True, AZUL if TITULOS[pantalla_menu] else GRIS)
    pantalla.blit(s, (ANCHO // 2 - s.get_width() // 2, 132))
    y = 210
    for i, (titulo, desc, *_ ) in enumerate(items):
        activo = i == sel
        if activo:
            pygame.draw.rect(pantalla, (30, 30, 42), (110, y - 8, ANCHO - 220, 60), border_radius=10)
            pygame.draw.rect(pantalla, NARANJA, (110, y - 8, 5, 60), border_radius=3)
        pantalla.blit(f_m.render(titulo, True, BLANCO if activo else (150, 150, 165)), (135, y))
        pantalla.blit(f_c.render(desc, True, GRIS if activo else (90, 90, 105)), (135, y + 27))
        y += 70
    if pantalla_menu == "jugar" and marcador:
        t = f_c.render("Tu marcador: " + "   ".join(f"{k} {v[0]}-{v[1]}" for k, v in marcador.items()), True, BLANCO)
        pantalla.blit(t, (ANCHO // 2 - t.get_width() // 2, ALTO - 110))
    ayuda = "↑ ↓ elegir    Enter aceptar    " + ("Esc salir" if pantalla_menu == "principal" else "Esc volver")
    t = f_c.render(ayuda, True, GRIS)
    pantalla.blit(t, (ANCHO // 2 - t.get_width() // 2, ALTO - 60))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", type=int, default=None, help="jugar directo contra el mejor jefe de esa generación")
    ap.add_argument("--bot", choices=list(HEROES), default=None, help="mirar directo al campeón contra ese bot")
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
    menus = opciones()
    menu, sel, marcador = "principal", 0, {}
    en_vivo = None                                                # proceso de en_vivo.py, si está abierto
    combate, pausa, velocidad, cuadro = None, False, 1, 0

    if args.gen is not None:
        g = np.load(R / "mejores_por_generacion.npy")[args.gen - 1]
        combate = Combate((f"Generación {args.gen}", g), ("Jugador", None), escena)
    elif args.bot:
        combate = Combate(("Campeón", np.load(R / "campeon.npy")), (f"Bot {args.bot}", args.bot), escena)

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); return
            if ev.type != pygame.KEYDOWN:
                continue
            if combate is None:                                   # --- menú
                items = menus[menu]
                if ev.key == pygame.K_ESCAPE:
                    if menu == "principal":
                        pygame.quit(); return
                    menu, sel = "principal", 0
                elif ev.key in (pygame.K_UP, pygame.K_w): sel = (sel - 1) % len(items)
                elif ev.key in (pygame.K_DOWN, pygame.K_s): sel = (sel + 1) % len(items)
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    _, _, a, b = items[sel]
                    if menu != "principal":
                        combate, velocidad = Combate(a, b, escena), 1
                    elif a == "en_vivo":
                        if en_vivo is None:
                            en_vivo = subprocess.Popen([sys.executable, str(Path(__file__).parent / "en_vivo.py")])
                    else:
                        menu, sel = a, 0
            else:                                                 # --- combate
                if ev.key == pygame.K_ESCAPE: combate = None
                elif ev.key == pygame.K_r or (ev.key == pygame.K_RETURN and combate.resultado):
                    combate = Combate(combate.jefe, combate.heroe, escena)
                elif ev.key == pygame.K_p: pausa = not pausa
                elif ev.key == pygame.K_m: sonidos.activo = not sonidos.activo
                elif ev.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS) and not combate.humano:
                    velocidad = min(8, velocidad * 2)
                elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS) and not combate.humano:
                    velocidad = max(1, velocidad // 2)

        if en_vivo is not None and en_vivo.poll() is not None:   # se cerró: cargar sus campeones
            en_vivo = None
            menus = opciones()
            sel = min(sel, len(menus[menu]) - 1)
        if combate is None:
            dibujar_menu(pantalla, fuentes, menu, menus[menu], sel, marcador)
        else:
            if not pausa:
                antes = combate.resultado
                for _ in range(velocidad):
                    combate.paso()
                if antes is None and combate.resultado and combate.humano:
                    m = marcador.setdefault(combate.nombre_j, [0, 0])
                    m[0 if combate.resultado == "heroe" else 1] += 1
            pantalla.fill((8, 8, 12))
            f = combate.ar.foto(0)
            sub = combate.mensaje() or ("PAUSA" if pausa else "")
            escena.dibujar(pantalla, f, titulo=f"{combate.nombre_j}  vs.  {combate.nombre_h}"
                           + (f"   x{velocidad}" if velocidad > 1 else ""),
                           subtitulo=sub, nombres=("Jefe", "Jugador" if combate.humano else "Héroe"))
            ayuda = "R: otra vez   Esc: volver" if combate.resultado else \
                ("WASD + mouse · clic dispara · P pausa · M sonido · Esc volver" if combate.humano
                 else "+/- velocidad · P pausa · M sonido · Esc volver")
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
