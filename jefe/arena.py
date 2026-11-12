"""Simulador del combate jefe vs. héroe.

Está vectorizado con NumPy: un objeto Arena simula B partidas en paralelo
(una por cada combinación individuo x rival), lo que permite evaluar a toda
la población del algoritmo genético en pocos segundos. Con B = 1 se usa para
mostrar o jugar una partida.
"""
import numpy as np

from . import config as C


def _rotar(dx, dy, ang):
    c, s = np.cos(ang), np.sin(ang)
    return dx * c - dy * s, dx * s + dy * c


def _normalizar(dx, dy):
    n = np.sqrt(dx * dx + dy * dy) + 1e-9
    return dx / n, dy / n, n


class Balas:
    def __init__(self, b):
        z = lambda: np.zeros((b, C.MAX_BALAS))
        self.x, self.y, self.vx, self.vy = z(), z(), z(), z()
        self.viva = np.zeros((b, C.MAX_BALAS), dtype=bool)

    def disparar(self, mascara, x, y, dx, dy, vel):
        """Crea una bala en el primer lugar libre de las partidas indicadas."""
        hueco = np.argmin(self.viva, axis=1)
        filas = np.arange(len(hueco))
        libre = ~self.viva[filas, hueco]
        m = mascara & libre
        f, h = filas[m], hueco[m]
        self.x[f, h], self.y[f, h] = x[m], y[m]
        self.vx[f, h], self.vy[f, h] = dx[m] * vel, dy[m] * vel
        self.viva[f, h] = True
        return m

    def mover(self):
        self.x += self.vx
        self.y += self.vy
        fuera = (self.x < 0) | (self.x > 1) | (self.y < 0) | (self.y > 1)
        self.viva &= ~fuera

    def impactos(self, cx, cy, radio):
        """Cantidad de balas que tocan el círculo (cx, cy, radio); las elimina."""
        d2 = (self.x - cx[:, None]) ** 2 + (self.y - cy[:, None]) ** 2
        toca = self.viva & (d2 < (radio + C.BALA_RADIO) ** 2)
        self.viva &= ~toca
        return toca.sum(axis=1)


class Arena:
    def __init__(self, b, rng):
        self.b, self.rng = b, rng
        self.t = 0
        # Jefe arriba, héroe abajo, con algo de variación
        self.jx = rng.uniform(0.3, 0.7, b)
        self.jy = rng.uniform(0.70, 0.85, b)
        self.hx = rng.uniform(0.3, 0.7, b)
        self.hy = rng.uniform(0.15, 0.30, b)
        self.jvx, self.jvy = np.zeros(b), np.zeros(b)
        self.hvx, self.hvy = np.zeros(b), np.zeros(b)
        self.jvida = np.full(b, C.JEFE_VIDA)
        self.hvida = np.full(b, C.HEROE_VIDA)
        self.j_disparo_cd = np.zeros(b, dtype=int)
        self.h_disparo_cd = np.zeros(b, dtype=int)
        self.emb_t = np.zeros(b, dtype=int)          # pasos restantes de embestida
        self.emb_cd = np.zeros(b, dtype=int)
        self.emb_dx, self.emb_dy = np.zeros(b), np.zeros(b)
        self.emb_golpeo = np.zeros(b, dtype=bool)
        self.balas_jefe = Balas(b)
        self.balas_heroe = Balas(b)
        self.activa = np.ones(b, dtype=bool)
        self.fin = np.full(b, C.DURACION_MAX)
        # Estadísticas
        self.disparos_jefe = np.zeros(b)
        self.embestidas = np.zeros(b)
        self.embestidas_acertadas = np.zeros(b)

    # ------------------------------------------------------------ percepción
    def observar(self):
        """Vector de 15 percepciones del jefe (sus 'sensores'), en [-1, 1] aprox."""
        dx, dy = self.hx - self.jx, self.hy - self.jy
        dist = np.sqrt(dx * dx + dy * dy)
        # Bala del héroe más cercana al jefe
        bh = self.balas_heroe
        d2 = (bh.x - self.jx[:, None]) ** 2 + (bh.y - self.jy[:, None]) ** 2
        d2 = np.where(bh.viva, d2, np.inf)
        k = np.argmin(d2, axis=1)
        f = np.arange(self.b)
        hay = np.isfinite(d2[f, k])
        bdx = np.where(hay, bh.x[f, k] - self.jx, 0.0)
        bdy = np.where(hay, bh.y[f, k] - self.jy, 0.0)
        bvx = np.where(hay, bh.vx[f, k] / C.HEROE_BALA_VEL, 0.0)
        bvy = np.where(hay, bh.vy[f, k] / C.HEROE_BALA_VEL, 0.0)
        return np.stack([
            dx * 2, dy * 2, dist * 2 - 1,
            self.hvx / C.HEROE_VEL, self.hvy / C.HEROE_VEL,
            np.clip(bdx * 3, -1, 1), np.clip(bdy * 3, -1, 1), bvx, bvy,
            self.jx * 2 - 1, self.jy * 2 - 1,
            np.where(self.emb_cd == 0, 1.0, -1.0),
            np.where(self.j_disparo_cd == 0, 1.0, -1.0),
            self.jvida / C.JEFE_VIDA * 2 - 1,
            self.hvida / C.HEROE_VIDA * 2 - 1,
        ], axis=1)

    # ------------------------------------------------------------ dinámica
    def paso(self, salida_jefe, cmd_heroe):
        """Avanza un paso.

        salida_jefe: (B, 5) en [-1, 1] -> mover x, mover y, embestir, disparar, puntería
        cmd_heroe: dict con vx, vy (dirección deseada), disparar (bool), angulo (rad)
        """
        a = self.activa
        mx, my = salida_jefe[:, 0], salida_jefe[:, 1]
        quiere_embestir = salida_jefe[:, 2] > 0
        quiere_disparar = salida_jefe[:, 3] > 0
        ajuste = salida_jefe[:, 4] * C.DESVIO_PUNTERIA

        ux, uy, dist = _normalizar(self.hx - self.jx, self.hy - self.jy)
        ax, ay = _rotar(ux, uy, ajuste)              # dirección de ataque del jefe

        # --- Jefe: embestida
        empieza = a & quiere_embestir & (self.emb_cd == 0) & (self.emb_t == 0)
        self.emb_t = np.where(empieza, C.JEFE_EMBESTIDA_DURACION, self.emb_t)
        self.emb_cd = np.where(empieza, C.JEFE_EMBESTIDA_CD, self.emb_cd)
        self.emb_dx = np.where(empieza, ax, self.emb_dx)
        self.emb_dy = np.where(empieza, ay, self.emb_dy)
        self.emb_golpeo = np.where(empieza, False, self.emb_golpeo)
        self.embestidas += empieza

        # --- Jefe: movimiento
        n = np.maximum(1.0, np.sqrt(mx * mx + my * my))
        embistiendo = self.emb_t > 0
        self.jvx = np.where(embistiendo, self.emb_dx * C.JEFE_EMBESTIDA_VEL, mx / n * C.JEFE_VEL)
        self.jvy = np.where(embistiendo, self.emb_dy * C.JEFE_EMBESTIDA_VEL, my / n * C.JEFE_VEL)

        # --- Jefe: disparo
        dispara = a & quiere_disparar & (self.j_disparo_cd == 0)
        ok = self.balas_jefe.disparar(dispara, self.jx, self.jy, ax, ay, C.JEFE_BALA_VEL)
        self.j_disparo_cd = np.where(ok, C.JEFE_DISPARO_CD, self.j_disparo_cd)
        self.disparos_jefe += ok

        # --- Héroe: movimiento y disparo
        hx, hy = cmd_heroe["vx"], cmd_heroe["vy"]
        n = np.maximum(1.0, np.sqrt(hx * hx + hy * hy))
        self.hvx, self.hvy = hx / n * C.HEROE_VEL, hy / n * C.HEROE_VEL
        h_disp = a & cmd_heroe["disparar"] & (self.h_disparo_cd == 0)
        ang = cmd_heroe["angulo"]
        ok = self.balas_heroe.disparar(h_disp, self.hx, self.hy, np.cos(ang), np.sin(ang), C.HEROE_BALA_VEL)
        self.h_disparo_cd = np.where(ok, C.HEROE_DISPARO_CD, self.h_disparo_cd)

        # --- Integración y límites de la arena
        am = a.astype(float)
        self.jx = np.clip(self.jx + self.jvx * am, C.JEFE_RADIO, 1 - C.JEFE_RADIO)
        self.jy = np.clip(self.jy + self.jvy * am, C.JEFE_RADIO, 1 - C.JEFE_RADIO)
        self.hx = np.clip(self.hx + self.hvx * am, C.HEROE_RADIO, 1 - C.HEROE_RADIO)
        self.hy = np.clip(self.hy + self.hvy * am, C.HEROE_RADIO, 1 - C.HEROE_RADIO)
        self.balas_jefe.mover()
        self.balas_heroe.mover()

        # --- Daño por balas
        danio_h = self.balas_jefe.impactos(self.hx, self.hy, C.HEROE_RADIO) * C.JEFE_BALA_DANIO
        danio_j = self.balas_heroe.impactos(self.jx, self.jy, C.JEFE_RADIO) * C.HEROE_BALA_DANIO

        # --- Contacto cuerpo a cuerpo
        dx, dy = self.hx - self.jx, self.hy - self.jy
        tocan = (dx * dx + dy * dy) < (C.JEFE_RADIO + C.HEROE_RADIO) ** 2
        golpe = tocan & (self.emb_t > 0) & ~self.emb_golpeo
        self.emb_golpeo |= golpe
        self.embestidas_acertadas += golpe & a
        danio_h = danio_h + np.where(golpe, C.JEFE_EMBESTIDA_DANIO, 0.0)
        danio_h = danio_h + np.where(tocan & ~golpe, C.JEFE_CONTACTO_DANIO, 0.0)

        self.hvida -= danio_h * am
        self.jvida -= danio_j * am

        # --- Temporizadores
        self.emb_t = np.maximum(0, self.emb_t - 1)
        self.emb_cd = np.maximum(0, self.emb_cd - 1)
        self.j_disparo_cd = np.maximum(0, self.j_disparo_cd - 1)
        self.h_disparo_cd = np.maximum(0, self.h_disparo_cd - 1)

        self.t += 1
        termina = a & ((self.hvida <= 0) | (self.jvida <= 0) | (self.t >= C.DURACION_MAX))
        self.fin = np.where(termina, self.t, self.fin)
        self.activa = a & ~termina

    # ------------------------------------------------------------ resultados
    def resultados(self):
        hv = np.maximum(self.hvida, 0)
        jv = np.maximum(self.jvida, 0)
        return {
            "danio_hecho": C.HEROE_VIDA - hv,
            "danio_recibido": C.JEFE_VIDA - jv,
            "gana_jefe": (hv <= 0) & (jv > 0),
            "gana_heroe": (jv <= 0),
            "duracion": self.fin,
            "disparos": self.disparos_jefe,
            "embestidas": self.embestidas,
            "embestidas_acertadas": self.embestidas_acertadas,
        }

    def foto(self, k=0):
        """Estado de la partida k para dibujarla."""
        bj, bh = self.balas_jefe, self.balas_heroe
        return {
            "t": self.t,
            "jefe": (self.jx[k], self.jy[k]), "heroe": (self.hx[k], self.hy[k]),
            "jvida": max(self.jvida[k], 0) / C.JEFE_VIDA,
            "hvida": max(self.hvida[k], 0) / C.HEROE_VIDA,
            "embistiendo": bool(self.emb_t[k] > 0),
            "balas_jefe": list(zip(bj.x[k][bj.viva[k]], bj.y[k][bj.viva[k]])),
            "balas_heroe": list(zip(bh.x[k][bh.viva[k]], bh.y[k][bh.viva[k]])),
        }


def aptitud(res):
    """Función de aptitud (fitness) de una partida, desde el punto de vista del jefe."""
    f = res["danio_hecho"] - C.PESO_DANIO_RECIBIDO * res["danio_recibido"] * (C.HEROE_VIDA / C.JEFE_VIDA)
    rapidez = 1 - res["duracion"] / C.DURACION_MAX
    f = f + res["gana_jefe"] * (C.PREMIO_VICTORIA + C.PREMIO_RAPIDEZ * rapidez)
    return f
