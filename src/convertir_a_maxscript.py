"""
==============================================================
CONVERSOR: coordenadas de silueta -> MAXScript (.ms) con extrusion
==============================================================

Lee un archivo *_silueta.py generado por el extractor (o
cualquier archivo con una lista "puntos = [(x, y), ...]"),
simplifica el contorno con Douglas-Peucker para que sea
manejable en 3ds Max, y genera un script .ms que:

  1. Crea una Line (spline) cerrada fiel al contorno
  2. Le aplica un modificador Extrude para darle volumen 3D
  3. La convierte a Editable Poly (opcional, mas facil de editar)

USO:
    python convertir_a_maxscript.py entrada_silueta.py salida.ms \
        --tolerancia 0.8 --extrusion 15
==============================================================
"""

import re
import sys
import argparse


# ==============================================================
# EXTRAER PUNTOS DEL ARCHIVO FUENTE
# ==============================================================

def extraer_puntos(ruta_archivo):
    if ruta_archivo.endswith(".json"):
        import json
        with open(ruta_archivo, encoding="utf-8") as f:
            data = json.load(f)
        return [(float(x), float(y)) for x, y in data["puntos"]]

    with open(ruta_archivo, encoding="utf-8") as f:
        contenido = f.read()

    bloques = re.split(r"# Tipo:\s*(\w+)", contenido)

    if len(bloques) < 3:
        pares = re.findall(r"\(([-\d.]+),\s*([-\d.]+)\)", contenido)
        return [(float(x), float(y)) for x, y in pares]

    candidatos_exterior = []

    for i in range(1, len(bloques), 2):
        tipo = bloques[i]
        texto_bloque = bloques[i + 1]

        if tipo != "EXTERIOR":
            continue

        cierre = texto_bloque.find("]")
        texto_puntos = texto_bloque[:cierre] if cierre != -1 else texto_bloque

        pares = re.findall(r"\(([-\d.]+),\s*([-\d.]+)\)", texto_puntos)
        puntos = [(float(x), float(y)) for x, y in pares]

        if puntos:
            candidatos_exterior.append(puntos)

    if not candidatos_exterior:
        pares = re.findall(r"\(([-\d.]+),\s*([-\d.]+)\)", contenido)
        return [(float(x), float(y)) for x, y in pares]

    candidatos_exterior.sort(key=len, reverse=True)
    return candidatos_exterior[0]


# ==============================================================
# SIMPLIFICACION: DOUGLAS-PEUCKER (version iterativa)
#
# Reduce el numero de puntos manteniendo la forma: solo elimina
# puntos que estan casi sobre una linea recta entre sus vecinos.
# Un contorno con detalle real (curvas, dientes) conserva sus
# puntos; un tramo recto se reduce a 2 puntos.
# ==============================================================

def _distancia_punto_a_segmento(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b

    dx, dy = bx - ax, by - ay

    if dx == 0 and dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5

    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))

    proy_x = ax + t * dx
    proy_y = ay + t * dy

    return ((px - proy_x) ** 2 + (py - proy_y) ** 2) ** 0.5


def simplificar_douglas_peucker(puntos, tolerancia):
    if len(puntos) < 3:
        return puntos[:]

    conservar = [False] * len(puntos)
    conservar[0] = True
    conservar[-1] = True

    pila = [(0, len(puntos) - 1)]

    while pila:
        inicio, fin = pila.pop()

        if fin - inicio < 2:
            continue

        a, b = puntos[inicio], puntos[fin]

        max_dist = -1.0
        max_idx = -1

        for i in range(inicio + 1, fin):
            d = _distancia_punto_a_segmento(puntos[i], a, b)
            if d > max_dist:
                max_dist = d
                max_idx = i

        if max_dist > tolerancia:
            conservar[max_idx] = True
            pila.append((inicio, max_idx))
            pila.append((max_idx, fin))

    return [p for p, k in zip(puntos, conservar) if k]


# ==============================================================
# GENERAR MAXSCRIPT
# ==============================================================

def generar_maxscript(
    puntos,
    nombre_objeto="Hoja_Silueta",
    altura_extrusion=15.0,
    escala=1.0,
    segmentos_extrusion=1,
    convertir_a_poly=True,
):
    # Centrar en el origen (bounding box), y voltear Y
    # (en la imagen Y crece hacia abajo; en Max normalmente
    # queremos Y "normal" en el plano XY)
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]

    centro_x = (min(xs) + max(xs)) / 2
    centro_y = (min(ys) + max(ys)) / 2

    lineas = []

    lineas.append("-- ==========================================================")
    lineas.append("-- SILUETA 3D GENERADA AUTOMATICAMENTE")
    lineas.append("-- Puntos en el contorno: {}".format(len(puntos)))
    lineas.append("-- ==========================================================")
    lineas.append("")
    lineas.append("delete objects")
    lineas.append("")
    lineas.append("shp = splineShape pos:[0,0,0] name:\"{}\"".format(nombre_objeto))
    lineas.append("addNewSpline shp")
    lineas.append("")

    for x, y in puntos:
        px = (x - centro_x) * escala
        py = -(y - centro_y) * escala  # invertir Y

        lineas.append(
            "addKnot shp 1 #corner #line [{:.3f}, {:.3f}, 0]".format(px, py)
        )

    lineas.append("")
    lineas.append("close shp 1")
    lineas.append("updateShape shp")
    lineas.append("")
    lineas.append("-- Extrusion: le da volumen 3D a la silueta")
    lineas.append(
        "addModifier shp (Extrude amount:{} segments:{} capStart:on capEnd:on)".format(
            altura_extrusion, segmentos_extrusion
        )
    )
    lineas.append("")

    if convertir_a_poly:
        lineas.append("-- Convertir a Editable Poly para facilitar edicion posterior")
        lineas.append("convertToPoly shp")
        lineas.append("")

    lineas.append("max zoomext sel all")
    lineas.append("")
    lineas.append(
        'print ("Silueta 3D creada: " + shp.name + " (" + {} as string + " puntos)")'.format(
            len(puntos)
        )
    )

    return "\n".join(lineas)


# ==============================================================
# MAIN
# ==============================================================

def convertir(
    ruta_entrada,
    ruta_salida,
    tolerancia=0.8,
    altura_extrusion=15.0,
    escala=1.0,
    nombre_objeto=None,
):
    puntos = extraer_puntos(ruta_entrada)

    if not puntos:
        raise ValueError("No se encontraron coordenadas en el archivo.")

    puntos_simplificados = simplificar_douglas_peucker(puntos, tolerancia)

    if nombre_objeto is None:
        nombre_objeto = "Silueta_3D"

    codigo = generar_maxscript(
        puntos_simplificados,
        nombre_objeto=nombre_objeto,
        altura_extrusion=altura_extrusion,
        escala=escala,
    )

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write(codigo)

    return {
        "puntos_originales": len(puntos),
        "puntos_simplificados": len(puntos_simplificados),
        "reduccion_pct": round(
            100 * (1 - len(puntos_simplificados) / len(puntos)), 1
        ),
        "archivo_salida": ruta_salida,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convierte coordenadas de silueta a MAXScript con extrusion 3D"
    )
    parser.add_argument("entrada", help="Archivo .py con la lista de puntos")
    parser.add_argument("salida", help="Archivo .ms de salida")
    parser.add_argument("--tolerancia", type=float, default=0.8,
                         help="Tolerancia de simplificacion (mayor = menos puntos)")
    parser.add_argument("--extrusion", type=float, default=15.0,
                         help="Altura de la extrusion 3D")
    parser.add_argument("--escala", type=float, default=1.0,
                         help="Factor de escala de las coordenadas")
    parser.add_argument("--nombre", type=str, default=None,
                         help="Nombre del objeto en 3ds Max")

    args = parser.parse_args()

    resultado = convertir(
        args.entrada,
        args.salida,
        tolerancia=args.tolerancia,
        altura_extrusion=args.extrusion,
        escala=args.escala,
        nombre_objeto=args.nombre,
    )

    print("Puntos originales:", resultado["puntos_originales"])
    print("Puntos simplificados:", resultado["puntos_simplificados"])
    print("Reduccion:", resultado["reduccion_pct"], "%")
    print("Archivo generado:", resultado["archivo_salida"])