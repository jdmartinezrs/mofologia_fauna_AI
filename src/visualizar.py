"""
==============================================================
VISUALIZAR HOJAS (control de calidad)
==============================================================

Convierte archivos de coordenadas (ya sean *_silueta.py del
extractor, o *.json de hojas_generadas/) en imagenes PNG, para
poder revisar visualmente que las siluetas tengan sentido.

No requiere ventanas ni tkinter (a diferencia del *_silueta.py
original) — genera archivos PNG directamente, funciona igual en
cualquier maquina.

USO:
    # Una sola hoja
    python visualizar.py hojas_generadas/mango_generada_001.json

    # Una carpeta completa (genera un PNG por archivo)
    python visualizar.py hojas_generadas/ --salida vista_previas/

    # Una cuadricula con TODAS las hojas de una carpeta en una imagen
    python visualizar.py hojas_generadas/ --cuadricula --salida vista_previas/
==============================================================
"""

import argparse
import glob
import json
import os
import re

import matplotlib
matplotlib.use("Agg")  # sin ventanas, funciona en cualquier maquina
import matplotlib.pyplot as plt


# ==============================================================
# LECTURA DE PUNTOS (soporta .json de este proyecto Y
# *_silueta.py del extractor original)
# ==============================================================

def cargar_puntos(ruta_archivo):
    if ruta_archivo.endswith(".json"):
        with open(ruta_archivo, encoding="utf-8") as f:
            data = json.load(f)
        return data["puntos"], data.get("especie", os.path.basename(ruta_archivo))

    # asumir *_silueta.py u otro archivo con tuplas (x, y)
    with open(ruta_archivo, encoding="utf-8") as f:
        contenido = f.read()

    pares = re.findall(r"\(([-\d.]+),\s*([-\d.]+)\)", contenido)
    puntos = [[float(x), float(y)] for x, y in pares]
    return puntos, os.path.basename(ruta_archivo)


# ==============================================================
# DIBUJAR UNA HOJA
# ==============================================================

def dibujar_hoja(ax, puntos, titulo=""):
    xs = [p[0] for p in puntos] + [puntos[0][0]]
    ys = [p[1] for p in puntos] + [puntos[0][1]]

    ax.fill(xs, ys, color="seagreen", alpha=0.55)
    ax.plot(xs, ys, color="darkgreen", linewidth=1)
    ax.set_aspect("equal")
    ax.set_title(titulo, fontsize=9)
    ax.set_xticks([])
    ax.set_yticks([])


# ==============================================================
# MODO: UN ARCHIVO -> UN PNG
# ==============================================================

def visualizar_archivo(ruta_archivo, carpeta_salida):
    puntos, etiqueta = cargar_puntos(ruta_archivo)

    fig, ax = plt.subplots(figsize=(5, 6))
    dibujar_hoja(ax, puntos, titulo=f"{etiqueta}  ({len(puntos)} pts)")

    os.makedirs(carpeta_salida, exist_ok=True)
    nombre_base = os.path.splitext(os.path.basename(ruta_archivo))[0]
    ruta_salida = os.path.join(carpeta_salida, nombre_base + ".png")

    plt.tight_layout()
    plt.savefig(ruta_salida, dpi=110)
    plt.close(fig)

    return ruta_salida


# ==============================================================
# MODO: CARPETA -> CUADRICULA EN UN SOLO PNG
# ==============================================================

def visualizar_cuadricula(archivos, carpeta_salida, nombre_salida="cuadricula.png"):
    n = len(archivos)
    columnas = min(4, n)
    filas = (n + columnas - 1) // columnas

    fig, axes = plt.subplots(filas, columnas, figsize=(columnas * 3.2, filas * 3.8))

    if filas * columnas == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    for i, ruta_archivo in enumerate(archivos):
        puntos, etiqueta = cargar_puntos(ruta_archivo)
        dibujar_hoja(axes[i], puntos, titulo=f"{etiqueta}\n({len(puntos)} pts)")

    for j in range(n, len(axes)):
        axes[j].axis("off")

    os.makedirs(carpeta_salida, exist_ok=True)
    ruta_salida = os.path.join(carpeta_salida, nombre_salida)

    plt.tight_layout()
    plt.savefig(ruta_salida, dpi=110)
    plt.close(fig)

    return ruta_salida


# ==============================================================
# MAIN
# ==============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Genera vistas previas PNG de hojas (reales o generadas)"
    )
    parser.add_argument(
        "entrada",
        help="Un archivo .json/_silueta.py, o una carpeta con varios"
    )
    parser.add_argument(
        "--salida", default="vista_previas",
        help="Carpeta donde guardar los PNG (default: vista_previas)"
    )
    parser.add_argument(
        "--cuadricula", action="store_true",
        help="Si 'entrada' es una carpeta, junta todo en una sola imagen"
    )
    args = parser.parse_args()

    if os.path.isdir(args.entrada):
        archivos = sorted(
            glob.glob(os.path.join(args.entrada, "*.json"))
            + glob.glob(os.path.join(args.entrada, "*_silueta.py"))
        )

        if not archivos:
            print(f"No se encontraron .json ni *_silueta.py en {args.entrada}")
            return

        if args.cuadricula:
            ruta = visualizar_cuadricula(archivos, args.salida)
            print(f"Cuadricula generada: {ruta}")
        else:
            for archivo in archivos:
                ruta = visualizar_archivo(archivo, args.salida)
                print(f"Generado: {ruta}")

    else:
        ruta = visualizar_archivo(args.entrada, args.salida)
        print(f"Generado: {ruta}")


if __name__ == "__main__":
    main()