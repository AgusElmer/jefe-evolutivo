"""Dibujo del combate con Pygame: partículas, brillos, estelas, sacudida y sonido.

Lo usan jugar.py (para jugar o mirar) y en_vivo.py (coevolución en vivo).
No influye en la simulación: solo lee las "fotos" del estado de la arena.
"""
import math
import random
from collections import deque

import numpy as np
import pygame

from . import config as C

FONDO = (14, 14, 20)
GRILLA = (26, 26, 36)
BORDE = (60, 60, 80)
NARANJA = (240, 110, 55)
AMARILLO = (255, 214, 90)
AZUL = (80, 160, 245)
CELESTE = (170, 215, 255)
BLANCO = (240, 240, 245)
GRIS = (140, 140, 155)


def _brillo(radio, color, capas=8, intensidad=0.07):
    """Halo para mezclar en modo aditivo: fondo negro y capas tenues que se suman hacia el centro."""
    lado = radio * 4
    s = pygame.Surface((lado, lado))
    s.fill((0, 0, 0))
    capa = pygame.Surface((lado, lado))
    tenue = tuple(int(c * intensidad) for c in color)
    for i in range(capas):
        capa.fill((0, 0, 0))
        pygame.draw.circle(capa, tenue, (lado // 2, lado // 2), int(radio * 2 * (1 - i / capas)) or 1)
        s.blit(capa, (0, 0), special_flags=pygame.BLEND_ADD)
    return s


class Sonidos:
    """Sonidos sintetizados con NumPy. Si no hay audio disponible, queda en silencio."""

    def __init__(self):
        self.ok, self.activo, self.s = False, True, {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 256)
            fr = pygame.mixer.get_init()[0]
            canales = pygame.mixer.get_init()[2]
            def sonido(onda, vol):
                onda = np.clip(onda, -1, 1) * 32767 * vol
                arr = onda.astype(np.int16)
                if canales == 2:
                    arr = np.column_stack([arr, arr])
                return pygame.sndarray.make_sound(np.ascontiguousarray(arr))
            t = lambda dur: np.linspace(0, dur, int(fr * dur), endpoint=False)
            env = lambda x, k: np.exp(-k * x)
            x = t(0.09); self.s["disparo_jefe"] = sonido(np.sin(2 * np.pi * (700 - 3000 * x) * x) * env(x, 30), 0.25)
            x = t(0.06); self.s["disparo_heroe"] = sonido(np.sign(np.sin(2 * np.pi * (1400 - 6000 * x) * x)) * env(x, 50), 0.08)
            x = t(0.12); self.s["golpe"] = sonido(np.random.uniform(-1, 1, len(x)) * env(x, 35), 0.35)
            x = t(0.30); ruido = np.convolve(np.random.uniform(-1, 1, len(x)), np.ones(12) / 12, "same")
            self.s["embestida"] = sonido(ruido * np.sin(np.pi * x / 0.30) * 3, 0.35)
            x = t(0.8); ruido = np.convolve(np.random.uniform(-1, 1, len(x)), np.ones(30) / 30, "same")
            self.s["explosion"] = sonido(ruido * env(x, 5) * 5 + 0.3 * np.sin(2 * np.pi * 55 * x) * env(x, 4), 0.5)
            self.ok = True
        except Exception:
            self.ok = False

    def __call__(self, nombre):
        if self.ok and self.activo and nombre in self.s:
            self.s[nombre].play()


class Escena:
    """Dibuja una arena de lado `lado` píxeles con su esquina superior izquierda en `origen`."""

    def __init__(self, lado, origen=(0, 0), sonidos=None):
        self.lado, self.origen = lado, origen
        self.sonidos = sonidos
        self.particulas = []
        self.sacudida = 0.0
        self.estela = deque(maxlen=14)
        self.flash_jefe = self.flash_heroe = 0
        self.previa = None
        self.fin_mostrado = False
        r_j, r_h = int(C.JEFE_RADIO * lado), int(C.HEROE_RADIO * lado)
        self.g_jefe, self.g_emb = _brillo(r_j, NARANJA), _brillo(r_j, AMARILLO)
        self.g_heroe = _brillo(r_h, AZUL)
        self.g_bj, self.g_bh = _brillo(5, NARANJA, 4), _brillo(3, CELESTE, 4)
        self.f_chica = pygame.font.SysFont("DejaVu Sans", 14, bold=True)
        self.f_grande = pygame.font.SysFont("DejaVu Sans", 40, bold=True)
        self.fondo = self._fondo()

    def reiniciar(self):
        self.particulas.clear(); self.estela.clear()
        self.sacudida, self.previa, self.fin_mostrado = 0.0, None, False

    def _fondo(self):
        s = pygame.Surface((self.lado, self.lado))
        s.fill(FONDO)
        paso = self.lado // 16
        for i in range(0, self.lado, paso):
            pygame.draw.line(s, GRILLA, (i, 0), (i, self.lado))
            pygame.draw.line(s, GRILLA, (0, i), (self.lado, i))
        pygame.draw.rect(s, BORDE, s.get_rect(), 2)
        return s

    def _p(self, x, y, d=(0, 0)):
        return (self.origen[0] + x * self.lado + d[0], self.origen[1] + (1 - y) * self.lado + d[1])

    def _chispas(self, x, y, color, n, vel=4.0, vida=25):
        for _ in range(n):
            a, v = random.uniform(0, 2 * math.pi), random.uniform(0.3, 1) * vel
            self.particulas.append([*self._p(x, y), math.cos(a) * v, math.sin(a) * v, vida, vida, color])

    # ------------------------------------------------------------------ eventos
    def actualizar(self, f, sacudir_heroe=True):
        p = self.previa
        if p is not None:
            if f["jvida"] < p["jvida"] - 1e-6:
                self._chispas(*f["jefe"], NARANJA, 10)
                self.flash_jefe = 4
                if self.sonidos: self.sonidos("golpe")
            if f["hvida"] < p["hvida"] - 1e-6:
                fuerte = (p["hvida"] - f["hvida"]) * C.HEROE_VIDA > 5
                self._chispas(*f["heroe"], CELESTE, 18 if fuerte else 6, vel=6 if fuerte else 3)
                self.flash_heroe = 5
                if sacudir_heroe:
                    self.sacudida = min(14, self.sacudida + (10 if fuerte else 3))
                if self.sonidos and fuerte: self.sonidos("golpe")
            if f["embistiendo"] and not p["embistiendo"] and self.sonidos:
                self.sonidos("embestida")
            if len(f["balas_jefe"]) > len(p["balas_jefe"]) and self.sonidos:
                self.sonidos("disparo_jefe")
            if len(f["balas_heroe"]) > len(p["balas_heroe"]) and self.sonidos:
                self.sonidos("disparo_heroe")
            for clave, quien, color in (("jvida", "jefe", NARANJA), ("hvida", "heroe", AZUL)):
                if f[clave] <= 0 < p[clave]:
                    self._chispas(*f[quien], color, 70, vel=9, vida=45)
                    self._chispas(*f[quien], BLANCO, 30, vel=5, vida=35)
                    self.sacudida = 18
                    if self.sonidos: self.sonidos("explosion")
        self.estela.append((f["jefe"], f["embistiendo"]))
        self.previa = f

    # ------------------------------------------------------------------ dibujo
    def dibujar(self, pantalla, f, titulo="", subtitulo="", nombres=("Jefe", "Héroe")):
        d = (random.uniform(-1, 1) * self.sacudida, random.uniform(-1, 1) * self.sacudida)
        self.sacudida *= 0.85
        pantalla.blit(self.fondo, (self.origen[0] + d[0], self.origen[1] + d[1]))

        # Estela de la embestida
        for i, ((x, y), emb) in enumerate(self.estela):
            if emb:
                r = int(C.JEFE_RADIO * self.lado * (0.4 + 0.6 * i / len(self.estela)))
                s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*AMARILLO, int(25 + 60 * i / len(self.estela))), (r, r), r)
                cx, cy = self._p(x, y, d)
                pantalla.blit(s, (cx - r, cy - r))

        for x, y in f["balas_jefe"]:
            cx, cy = self._p(x, y, d)
            pantalla.blit(self.g_bj, (cx - 10, cy - 10), special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(pantalla, (255, 170, 120), (cx, cy), 4)
        for x, y in f["balas_heroe"]:
            cx, cy = self._p(x, y, d)
            pantalla.blit(self.g_bh, (cx - 6, cy - 6), special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(pantalla, BLANCO, (cx, cy), 2)

        # Héroe
        hx, hy = f["heroe"]; jx, jy = f["jefe"]
        if f["hvida"] > 0:
            cx, cy = self._p(hx, hy, d)
            r = int(C.HEROE_RADIO * self.lado)
            pantalla.blit(self.g_heroe, (cx - 2 * r, cy - 2 * r), special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(pantalla, BLANCO if self.flash_heroe else AZUL, (cx, cy), r)
            a = math.atan2(jy - hy, jx - hx)
            pygame.draw.line(pantalla, CELESTE, (cx, cy), (cx + math.cos(a) * r * 1.6, cy - math.sin(a) * r * 1.6), 3)

        # Jefe (con un ojo que mira al héroe)
        if f["jvida"] > 0:
            cx, cy = self._p(jx, jy, d)
            r = int(C.JEFE_RADIO * self.lado)
            g = self.g_emb if f["embistiendo"] else self.g_jefe
            pantalla.blit(g, (cx - 2 * r, cy - 2 * r), special_flags=pygame.BLEND_ADD)
            col = BLANCO if self.flash_jefe else (AMARILLO if f["embistiendo"] else NARANJA)
            pygame.draw.circle(pantalla, col, (cx, cy), r)
            pygame.draw.circle(pantalla, (120, 40, 20), (cx, cy), r, 3)
            a = math.atan2(hy - jy, hx - jx)
            ox, oy = cx + math.cos(a) * r * 0.45, cy - math.sin(a) * r * 0.45
            pygame.draw.circle(pantalla, BLANCO, (ox, oy), r * 0.32)
            pygame.draw.circle(pantalla, (20, 20, 25), (ox + math.cos(a) * r * 0.12, oy - math.sin(a) * r * 0.12), r * 0.16)
        self.flash_jefe = max(0, self.flash_jefe - 1)
        self.flash_heroe = max(0, self.flash_heroe - 1)

        # Partículas
        vivas = []
        for q in self.particulas:
            q[0] += q[2]; q[1] += q[3]; q[2] *= 0.92; q[3] *= 0.92; q[4] -= 1
            if q[4] > 0:
                k = q[4] / q[5]
                col = tuple(int(c + (255 - c) * k * 0.6) for c in q[6])
                pygame.draw.circle(pantalla, col, (q[0] + d[0], q[1] + d[1]), max(1, int(3.5 * k + 0.5)))
                vivas.append(q)
        self.particulas = vivas

        # Barras de vida y textos
        x0, y0 = self.origen
        for i, (v, col, nom) in enumerate([(f["jvida"], NARANJA, nombres[0]), (f["hvida"], AZUL, nombres[1])]):
            bx = x0 + 12 + i * (self.lado // 2)
            ancho = self.lado // 2 - 24
            pygame.draw.rect(pantalla, (40, 40, 52), (bx, y0 + 30, ancho, 10), border_radius=4)
            pygame.draw.rect(pantalla, col, (bx, y0 + 30, int(ancho * max(v, 0)), 10), border_radius=4)
            pantalla.blit(self.f_chica.render(nom, True, col), (bx, y0 + 10))
        if titulo:
            t = self.f_chica.render(titulo, True, BLANCO)
            pantalla.blit(t, (x0 + self.lado - t.get_width(), y0 + self.lado + 6))
        reloj = self.f_chica.render(f"{f['t'] / C.PASOS_POR_SEGUNDO:4.1f} s", True, GRIS)
        pantalla.blit(reloj, (x0, y0 + self.lado + 6))
        if subtitulo:
            t = self.f_grande.render(subtitulo, True, BLANCO)
            sombra = self.f_grande.render(subtitulo, True, (0, 0, 0))
            c = (x0 + self.lado // 2 - t.get_width() // 2, y0 + self.lado // 2 - t.get_height() // 2)
            pantalla.blit(sombra, (c[0] + 3, c[1] + 3)); pantalla.blit(t, c)
