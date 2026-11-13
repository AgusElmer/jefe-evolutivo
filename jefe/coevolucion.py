"""Coevolución: jefes y héroes evolucionan a la vez, uno contra el otro.

Cada especie es la "función de aptitud" de la otra: si los héroes aprenden a
esquivar, los jefes tienen que aprender a anticipar, y así sucesivamente
(una "carrera armamentista"). Para que ninguna especie olvide cómo vencer a
rivales viejos, cada una también pelea contra un "salón de la fama" con los
campeones de generaciones anteriores.

Como la aptitud es relativa (depende del rival), cada tanto se toma un
"examen" contra rivales fijos: el jefe contra los héroes bot y el héroe
contra el jefe de reglas fijas.
"""
import numpy as np

from . import config as C
from .arena import Arena, aptitud, aptitud_heroe
from .genetico import nueva_generacion
from .jugadores import TODOS, jefe_manual
from .red import HEROE, JEFE, RedesEnLote
from .simulacion import combatir, combatir_politicas, politica_heroe_red, politica_red


class Coevolucion:
    def __init__(self, semilla=7, poblacion=C.COEVO_POBLACION, generaciones_previstas=300):
        self.rng = np.random.default_rng(semilla)
        self.n = poblacion
        self.total = generaciones_previstas
        self.jefes = JEFE.aleatorios(poblacion, self.rng)
        self.heroes = HEROE.aleatorios(poblacion, self.rng)
        self.salon_jefes, self.salon_heroes = [], []
        self.mejores_jefes, self.mejores_heroes = [], []
        self.historial = []
        self.gen = 0
        self.ultimo_examen = {"examen_jefe": np.nan, "examen_heroe": np.nan}

    # ------------------------------------------------------------------
    def _emparejar(self):
        """Arma la lista de combates: (índice de jefe, índice de héroe) y a quién le cuenta."""
        n, rng = self.n, self.rng
        ij, ih, cuenta_j, cuenta_h = [], [], [], []
        for _ in range(C.COEVO_RIVALES):                        # contra la población rival actual
            perm = rng.permutation(n)
            ij += list(range(n)); ih += list(perm)
            cuenta_j += [True] * n; cuenta_h += [True] * n
        for _ in range(C.COEVO_SALON if self.salon_heroes else 0):   # jefes vs. héroes históricos
            ij += list(range(n)); ih += list(n + rng.integers(0, len(self.salon_heroes), n))
            cuenta_j += [True] * n; cuenta_h += [False] * n
        for _ in range(C.COEVO_SALON if self.salon_jefes else 0):    # héroes vs. jefes históricos
            ij += list(n + rng.integers(0, len(self.salon_jefes), n)); ih += list(range(n))
            cuenta_j += [False] * n; cuenta_h += [True] * n
        return np.array(ij), np.array(ih), np.array(cuenta_j), np.array(cuenta_h)

    def paso(self):
        """Juega una generación completa y prepara la siguiente. Devuelve estadísticas."""
        n = self.n
        ij, ih, cj, ch = self._emparejar()
        todos_j = np.vstack([self.jefes] + ([np.array(self.salon_jefes)] if self.salon_jefes else []))
        todos_h = np.vstack([self.heroes] + ([np.array(self.salon_heroes)] if self.salon_heroes else []))
        red_j = RedesEnLote(todos_j, ij, JEFE)
        pol_h = politica_heroe_red(todos_h, ih)
        ar = Arena(len(ij), self.rng)
        while ar.activa.any():
            ar.paso(red_j(ar.observar()), pol_h(ar))
        res = ar.resultados()
        aj, ah = aptitud(res), aptitud_heroe(res)

        apt_j = np.bincount(ij[cj], weights=aj[cj], minlength=n)[:n] / np.bincount(ij[cj], minlength=n)[:n]
        apt_h = np.bincount(ih[ch], weights=ah[ch], minlength=n)[:n] / np.bincount(ih[ch], minlength=n)[:n]
        actuales = cj & ch                                     # combates entre poblaciones actuales
        mj, mh = int(np.argmax(apt_j)), int(np.argmax(apt_h))
        mejor_j, mejor_h = self.jefes[mj].copy(), self.heroes[mh].copy()
        self.mejores_jefes.append(mejor_j); self.mejores_heroes.append(mejor_h)
        self.salon_jefes.append(mejor_j); self.salon_heroes.append(mejor_h)

        self.gen += 1
        if self.gen % C.COEVO_EXAMEN_CADA == 0 or self.gen == 1:
            self.ultimo_examen = self.examen(mejor_j, mejor_h)
        fila = {
            "generacion": self.gen,
            "victorias_jefes": float(res["gana_jefe"][actuales].mean()),
            "victorias_heroes": float(res["gana_heroe"][actuales].mean()),
            "aptitud_jefes_max": float(apt_j.max()), "aptitud_jefes_media": float(apt_j.mean()),
            "aptitud_heroes_max": float(apt_h.max()), "aptitud_heroes_media": float(apt_h.mean()),
            "duracion_media_s": float(res["duracion"][actuales].mean() / C.PASOS_POR_SEGUNDO),
            **self.ultimo_examen,
        }
        self.historial.append(fila)

        g = min(self.gen, self.total - 1)
        self.jefes = nueva_generacion(self.jefes, apt_j, g, self.total, self.rng)
        self.heroes = nueva_generacion(self.heroes, apt_h, g, self.total, self.rng)
        return fila, mejor_j, mejor_h

    def examen(self, jefe, heroe, n=20):
        """Mide contra rivales que no cambian, para ver el progreso 'absoluto'."""
        estilos = [e for e in TODOS for _ in range(n)]
        r = combatir(politica_red(jefe, np.zeros(len(estilos), int)), estilos, self.rng)
        b = 4 * n
        r2 = combatir_politicas(jefe_manual, politica_heroe_red(heroe, np.zeros(b, int)), b, self.rng)
        return {"examen_jefe": float(r["gana_jefe"].mean()), "examen_heroe": float(r2["gana_heroe"].mean())}

    # ------------------------------------------------------------------
    def guardar(self, carpeta):
        import csv
        carpeta.mkdir(parents=True, exist_ok=True)
        np.save(carpeta / "mejores_jefes.npy", np.array(self.mejores_jefes))
        np.save(carpeta / "mejores_heroes.npy", np.array(self.mejores_heroes))
        np.save(carpeta / "jefe_final.npy", self.mejores_jefes[-1])
        np.save(carpeta / "heroe_final.npy", self.mejores_heroes[-1])
        with open(carpeta / "historial.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(self.historial[0]))
            w.writeheader()
            for fila in self.historial:
                w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in fila.items()})
