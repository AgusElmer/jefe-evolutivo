"""Comportamientos programados a mano (sin aprendizaje).

* Héroes "bot": simulan distintos estilos de jugador humano. Contra ellos
  entrena y se evalúa el jefe. Uno de ellos (PRUEBA) nunca se usa en el
  entrenamiento, para medir si el jefe generaliza.
* Jefe manual: un jefe clásico con reglas fijas ("si está cerca, embestir"),
  usado como línea de base para comparar con el jefe evolucionado.
"""
import numpy as np

from . import config as C

ENTRENAMIENTO = {
    "agresivo":      dict(dist=0.22, ruido=0.10, esquiva=0.5, anticipa=0.0, cambio=0.010),
    "francotirador": dict(dist=0.55, ruido=0.05, esquiva=0.8, anticipa=1.0, cambio=0.020),
    "escurridizo":   dict(dist=0.38, ruido=0.14, esquiva=1.2, anticipa=0.0, cambio=0.050),
}
PRUEBA = {
    "impredecible":  dict(dist=0.32, ruido=0.07, esquiva=1.0, anticipa=1.0, cambio=0.080),
}
TODOS = {**ENTRENAMIENTO, **PRUEBA}


class HeroeBot:
    """Un bot por partida; cada partida puede tener un estilo distinto."""

    def __init__(self, estilos, rng):
        self.rng = rng
        b = len(estilos)
        p = {k: np.array([TODOS[e][k] for e in estilos], dtype=float) for k in TODOS["agresivo"]}
        p["dist"] = p["dist"] + rng.uniform(-0.04, 0.04, b)    # cada partida es un poco distinta
        self.p = p
        self.lado = rng.choice([-1.0, 1.0], b)                  # sentido en que rodea al jefe

    def __call__(self, ar):
        p, rng = self.p, self.rng
        dx, dy = ar.jx - ar.hx, ar.jy - ar.hy
        dist = np.sqrt(dx * dx + dy * dy) + 1e-9
        ux, uy = dx / dist, dy / dist

        # 1) Mantener su distancia preferida y rodear al jefe
        radial = np.clip((dist - p["dist"]) * 8, -1, 1)
        self.lado = np.where(rng.random(ar.b) < p["cambio"], -self.lado, self.lado)
        vx = ux * radial - uy * self.lado * 0.7
        vy = uy * radial + ux * self.lado * 0.7

        # 2) Esquivar balas del jefe que vienen hacia él
        bj = ar.balas_jefe
        rx, ry = ar.hx[:, None] - bj.x, ar.hy[:, None] - bj.y
        vn = np.sqrt(bj.vx ** 2 + bj.vy ** 2) + 1e-9
        bvx, bvy = bj.vx / vn, bj.vy / vn
        adelante = rx * bvx + ry * bvy
        px, py = rx - adelante * bvx, ry - adelante * bvy
        perp = np.sqrt(px * px + py * py) + 1e-9
        amenaza = bj.viva & (adelante > 0) & (adelante < 0.25) & (perp < 0.07)
        peso = amenaza * (1 - perp / 0.07)
        vx = vx + p["esquiva"] * 2 * (peso * px / perp).sum(axis=1)
        vy = vy + p["esquiva"] * 2 * (peso * py / perp).sum(axis=1)

        # 3) Apartarse de una embestida en curso
        emb = (ar.emb_t > 0) & (dist < 0.35)
        vx = vx + emb * p["esquiva"] * 2 * (-ar.emb_dy) * self.lado
        vy = vy + emb * p["esquiva"] * 2 * (ar.emb_dx) * self.lado

        # 4) No quedar pegado a las paredes
        vx = vx + np.clip((0.12 - ar.hx) * 10, 0, 1) - np.clip((ar.hx - 0.88) * 10, 0, 1)
        vy = vy + np.clip((0.12 - ar.hy) * 10, 0, 1) - np.clip((ar.hy - 0.88) * 10, 0, 1)

        # 5) Apuntar (con error humano y, algunos, anticipando el movimiento)
        t_vuelo = dist / C.HEROE_BALA_VEL
        tx = ar.jx + p["anticipa"] * ar.jvx * t_vuelo
        ty = ar.jy + p["anticipa"] * ar.jvy * t_vuelo
        ang = np.arctan2(ty - ar.hy, tx - ar.hx) + rng.normal(0, 1, ar.b) * p["ruido"]
        return {"vx": vx, "vy": vy, "disparar": np.ones(ar.b, dtype=bool), "angulo": ang}


def jefe_manual(ar):
    """Jefe con reglas fijas: se acerca, dispara directo y embiste si está cerca."""
    dx, dy = ar.hx - ar.jx, ar.hy - ar.jy
    dist = np.sqrt(dx * dx + dy * dy) + 1e-9
    acercarse = np.where(dist > 0.25, 1.0, -0.5)
    return np.stack([
        dx / dist * acercarse, dy / dist * acercarse,
        np.where(dist < 0.30, 1.0, -1.0),
        np.ones(ar.b),
        np.zeros(ar.b),
    ], axis=1)


def jefe_quieto(ar):
    """Jefe que solo dispara directo sin moverse (línea de base mínima)."""
    z = np.zeros(ar.b)
    return np.stack([z, z, -np.ones(ar.b), np.ones(ar.b), z], axis=1)
