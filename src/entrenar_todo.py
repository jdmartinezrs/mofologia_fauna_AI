"""
==============================================================
ENTRENAR TODO EL DATASET
==============================================================

Este es el script que SI corres directamente.

Recorre una carpeta con subcarpetas por especie:

    fotos_procesadas/
        mango/
            mango_01_silueta.py
            mango_02_silueta.py
            ...
        monstera/
            monstera_01_silueta.py
            ...

Y entrena (o re-entrena) el modelo de cada especie que tenga
al menos MINIMO_MUESTRAS archivos.

USO:
    python entrenar_todo.py

    (o especifica otra carpeta:)
    python entrenar_todo.py --carpeta otra_ruta/fotos_procesadas
==============================================================
"""

import argparse
import glob
import os

from modelo_forma_especie import entrenar_especie


MINIMO_MUESTRAS = 5  # por debajo de esto, no tiene sentido entrenar PCA


def encontrar_especies(carpeta_base):
    """
    Devuelve un dict {nombre_especie: [lista de archivos _silueta.py]}
    a partir de la estructura de carpetas.
    """
    especies = {}

    if not os.path.isdir(carpeta_base):
        raise FileNotFoundError(
            f"No existe la carpeta: {carpeta_base}\n"
            f"Crea 'fotos_procesadas/nombre_especie/' y pon ahi "
            f"los archivos *_silueta.py de esa especie."
        )

    for nombre_especie in sorted(os.listdir(carpeta_base)):
        ruta_especie = os.path.join(carpeta_base, nombre_especie)

        if not os.path.isdir(ruta_especie):
            continue

        archivos = sorted(
            glob.glob(os.path.join(ruta_especie, "*_silueta.py"))
        )

        if archivos:
            especies[nombre_especie] = archivos

    return especies


def main():
    parser = argparse.ArgumentParser(
        description="Entrena modelos de forma para todas las especies"
    )
    parser.add_argument(
        "--carpeta", default="fotos_procesadas",
        help="Carpeta con subcarpetas por especie (default: fotos_procesadas)"
    )
    parser.add_argument(
        "--modelos", default="modelos",
        help="Carpeta donde guardar los modelos .json (default: modelos)"
    )
    parser.add_argument(
        "--n-por-lado", type=int, default=100,
        help="Landmarks por lado de la hoja (default: 100)"
    )
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  ENTRENANDO MODELOS DE FORMA POR ESPECIE")
    print("=" * 60)
    print()

    especies = encontrar_especies(args.carpeta)

    if not especies:
        print(f"No se encontraron especies con archivos *_silueta.py")
        print(f"dentro de: {args.carpeta}")
        return

    for nombre_especie, archivos in especies.items():

        print(f"- {nombre_especie}: {len(archivos)} muestra(s)", end=" ")

        if len(archivos) < MINIMO_MUESTRAS:
            print(f"[OMITIDA: necesita al menos {MINIMO_MUESTRAS}]")
            continue

        try:
            modelo, ruta = entrenar_especie(
                nombre_especie,
                archivos,
                n_por_lado=args.n_por_lado,
                carpeta_modelos=args.modelos,
            )
            print(f"-> modelo guardado en {ruta}")

        except Exception as error:
            print(f"[ERROR: {error}]")

    print()
    print("=" * 60)
    print("  LISTO")
    print("=" * 60)
    print()
    print(f"Modelos disponibles en: {args.modelos}/")
    print("Usa generar.py para crear hojas a partir de estos modelos.")
    print()


if __name__ == "__main__":
    main()
