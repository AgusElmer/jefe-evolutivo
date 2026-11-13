"""Jefe final: sigue entrenando al jefe contra bots Y contra héroes coevolucionados.

Parte de la población final de entrenar.py (jefes que ya saben pelear) y la
sigue evolucionando contra rivales más duros: los 3 bots de entrenamiento más
los mejores héroes de las generaciones 100, 150, 200 y 250 de la coevolución.
Para la prueba quedan afuera el bot "impredecible" y el héroe coevolucionado
final (generación 300), que el jefe nunca enfrenta durante el entrenamiento.

    python entrenar_jefe_final.py            # 200 generaciones, mutación suave (ajuste fino)
    python entrenar_jefe_final.py --extra kiteador --salida revancha
        # "revancha": suma el bot kiteador (la estrategia que le ganó al campeón jugando)
Guarda en resultados/<salida>/ (no toca los resultados del informe).
"""
import argparse
import csv
import time
from pathlib import Path

import numpy as np

from jefe import config as C
from jefe.arena import Arena
from jefe.genetico import nueva_generacion
from jefe.jugadores import ENTRENAMIENTO, HEROES, HeroeBot
from jefe.red import RedesEnLote
from jefe.simulacion import (combatir, combatir_politicas, evaluar_contra_redes, evaluar_genomas,
                             politica_heroe_red, politica_red)

R = Path(__file__).parent / "resultados"
GENS_HEROES = [100, 150, 200, 250]


def aptitud_total(pob, heroes, rng, bots, rep_bots=2, rep_redes=2):
    mb = evaluar_genomas(pob, bots, rep_bots, rng)
    mr = evaluar_contra_redes(pob, heroes, rep_redes, rng)
    apt = np.hstack([mb["aptitud"], mr["aptitud"]]).mean(axis=1)
    return apt, mb["gana_jefe"].mean(axis=1), mr["gana_jefe"].mean(axis=1)


def comparar(jefes, heroe_prueba, rng, n=300):
    filas = []
    for nombre, g in jefes.items():
        fila = {"jefe": nombre}
        for e in HEROES:
            fila[e] = combatir(politica_red(g, np.zeros(n, int)), [e] * n, rng)["gana_jefe"].mean()
        r = combatir_politicas(politica_red(g, np.zeros(n, int)), politica_heroe_red(heroe_prueba, np.zeros(n, int)), n, rng)
        fila["heroe_coevo_final"] = r["gana_jefe"].mean()
        # Reglas del modo jugador (60 s, balas más fuertes): aproxima a una persona
        for e in ("escurridizo", "kiteador"):
            ar = Arena(n, rng, duracion=C.HUMANO_DURACION, heroe_danio=C.HUMANO_BALA_DANIO)
            bot, red = HeroeBot([e] * n, rng), RedesEnLote(g, np.zeros(n, int))
            while ar.activa.any():
                ar.paso(red(ar.observar()), bot(ar))
            fila[f"modo_jugador_vs_{e}"] = ar.resultados()["gana_jefe"].mean()
        filas.append(fila)
    return filas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", type=int, default=200)
    ap.add_argument("--sigma", type=float, nargs=2, default=(0.10, 0.03),
                    help="mutación inicial y final: más suave que al entrenar desde cero")
    ap.add_argument("--extra", nargs="*", default=[], help="bots extra (cada uno cuenta doble)")
    ap.add_argument("--salida", default="jefe_final")
    ap.add_argument("--semilla", type=int, default=99)
    args = ap.parse_args()
    rng = np.random.default_rng(args.semilla)
    SALIDA = R / args.salida
    bots = list(ENTRENAMIENTO) + [e for e in args.extra for _ in range(2)]
    C.SIGMA_MUTACION, C.SIGMA_MUTACION_MIN = args.sigma      # ajuste fino: no "desarmar" lo aprendido

    heroes_coevo = np.load(R / "coevolucion" / "mejores_heroes.npy")
    heroes = heroes_coevo[[g - 1 for g in GENS_HEROES]]
    heroe_prueba = heroes_coevo[-1]
    pob = np.load(R / "poblacion_final.npy")
    historial, t0 = [], time.time()

    for g in range(args.gen):
        apt, v_bots, v_redes = aptitud_total(pob, heroes, rng, bots)
        m = int(np.argmax(apt))
        historial.append({"generacion": g + 1, "aptitud_max": float(apt.max()), "aptitud_media": float(apt.mean()),
                          "victorias_bots_mejor": float(v_bots[m]), "victorias_heroes_coevo_mejor": float(v_redes[m]),
                          "victorias_bots_media": float(v_bots.mean()), "victorias_heroes_coevo_media": float(v_redes.mean())})
        if g % 10 == 0 or g == args.gen - 1:
            print(f"gen {g + 1:4d} | aptitud máx {apt.max():6.1f} media {apt.mean():6.1f} | "
                  f"victorias (media de la población): bots {v_bots.mean():4.0%}  héroes coevo {v_redes.mean():4.0%} | "
                  f"{time.time() - t0:4.0f}s", flush=True)
        if g < args.gen - 1:
            pob = nueva_generacion(pob, apt, g, args.gen, rng)

    # Elegir campeón entre los 10 mejores con más combates
    top = np.argsort(-apt)[:10]
    apt2, _, _ = aptitud_total(pob[top], heroes, rng, bots, rep_bots=10, rep_redes=8)
    final = pob[top[int(np.argmax(apt2))]]
    SALIDA.mkdir(parents=True, exist_ok=True)
    np.save(SALIDA / "jefe_final.npy", final)
    np.save(SALIDA / "poblacion_final.npy", pob)
    with open(SALIDA / "historial.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(historial[0])); w.writeheader(); w.writerows(historial)

    jefes = {"Campeón (informe)": np.load(R / "campeon.npy")}
    if args.salida != "jefe_final" and (R / "jefe_final" / "jefe_final.npy").exists():
        jefes["Jefe final"] = np.load(R / "jefe_final" / "jefe_final.npy")
    jefes[args.salida.capitalize().replace("_", " ")] = final
    filas = comparar(jefes, heroe_prueba, rng)
    with open(SALIDA / "comparacion.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0])); w.writeheader()
        w.writerows([{k: (round(v, 3) if isinstance(v, float) else v) for k, v in fl.items()} for fl in filas])
    print("\nVictorias del jefe (300 combates c/u):")
    cols = list(filas[0])[1:]
    print(f"{'':22s}" + "".join(f"{c[-14:]:>15s}" for c in cols))
    for fl in filas:
        print(f"{fl['jefe']:22s}" + "".join(f"{fl[c]:15.0%}" for c in cols))
    print(f"Listo en {time.time() - t0:.0f}s:", SALIDA)


if __name__ == "__main__":
    main()
