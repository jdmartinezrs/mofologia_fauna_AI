"""
==============================================================
GENERAR HOJA DE UNA ESPECIE
==============================================================

Este es el script que corres cuando quieres "dame una hoja de
mango" desde la linea de comandos.

Requiere que ya hayas corrido entrenar_todo.py al menos una vez
(o modelo_forma_especie.entrenar_especie manualmente) para que
exista modelos/<especie>.json

USO:
    python generar.py mango
    python generar.py mango --cantidad 5
    python generar.py mango --semilla 42

    Para ver que especies estan disponibles:
    python generar.py --listar
==============================================================
"""

import argparse
import glob
import json
import os

from modelo_forma_especie import generar_hoja_de_especie


def listar_especies_disponibles(carpeta_modelos="modelos"):
    rutas = glob.glob(os.path.join(carpeta_modelos, "*.json"))
    return sorted(
        os.path.splitext(os.path.basename(r))[0] for r in rutas
    )


def main():
    parser = argparse.ArgumentParser(
        description="Genera hojas sinteticas a partir del modelo real de una especie"
    )
    parser.add_argument(
        "especie", nargs="?", default=None,
        help="Nombre de la especie (debe existir modelos/<especie>.json)"
    )
    parser.add_argument(
        "--cantidad", type=int, default=1,
        help="Cuantas hojas generar (default: 1)"
    )
    parser.add_argument(
        "--intensidad", type=float, default=1.0,
        help="1.0 = variacion tipica observada, <1 mas conservador, >1 mas extremo"
    )
    parser.add_argument(
        "--semilla", type=int, default=None,
        help="Fija la semilla para reproducir la misma hoja"
    )
    parser.add_argument(
        "--modelos", default="modelos",
        help="Carpeta donde estan los modelos .json"
    )
    parser.add_argument(
        "--salida", default="hojas_generadas",
        help="Carpeta donde guardar los .json generados"
    )
    parser.add_argument(
        "--listar", action="store_true",
        help="Muestra las especies disponibles y termina"
    )
    args = parser.parse_args()

    if args.listar or args.especie is None:
        disponibles = listar_especies_disponibles(args.modelos)

        if not disponibles:
            print(f"No hay modelos entrenados en '{args.modelos}/'.")
            print("Corre primero: python entrenar_todo.py")
        else:
            print("Especies disponibles:")
            for especie in disponibles:
                print(f"  - {especie}")
        return

    os.makedirs(args.salida, exist_ok=True)

    for i in range(args.cantidad):

        semilla_actual = (
            args.semilla + i if args.semilla is not None else None
        )

        hoja = generar_hoja_de_especie(
            args.especie,
            carpeta_modelos=args.modelos,
            intensidad=args.intensidad,
            semilla=semilla_actual,
        )

        nombre_archivo = f"{args.especie}_generada_{i + 1:03d}.json"
        ruta = os.path.join(args.salida, nombre_archivo)

        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(hoja, f, ensure_ascii=False, indent=2)

        print(f"Generada: {ruta}  ({len(hoja['puntos'])} puntos)")


if __name__ == "__main__":
    main()
