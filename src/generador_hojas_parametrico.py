"""
==============================================================
GENERADOR PARAMETRICO DE HOJAS
==============================================================

Genera siluetas de hojas (lista de coordenadas x, y) a partir
de parametros botanicos, en vez de extraerlas de una imagen.

Piensa en esto como el paso complementario a tu extractor:

    extractor_siluetas.py   -> hojas REALES (foto -> coordenadas)
    generador_hojas.py      -> hojas SINTETICAS (parametros -> coordenadas)

Ambos producen el mismo formato de salida, para que puedas
mezclarlos en el mismo dataset.

USO BASICO:

    from generador_hojas_parametrico import generar_hoja, guardar_json

    hoja = generar_hoja(
        forma="lanceolada",
        margen="serrado",
        apice="acuminado",
        base="cuneada",
        relacion_largo_ancho=2.5,
    )

    guardar_json(hoja, "hoja_00001.json")

Para pedir una hoja "en lenguaje natural", la idea es que un
modelo de lenguaje (Claude, GPT, etc.) traduzca la descripcion
del usuario a estos mismos parametros, y luego llames a
generar_hoja(**parametros).
==============================================================
"""

import json
import math
import random
import uuid


# ==============================================================
# CATALOGO DE PARAMETROS VALIDOS
# (misma taxonomia botanica que usamos para etiquetar)
# ==============================================================

FORMAS_VALIDAS = [
    "ovada", "lanceolada", "eliptica", "orbicular",
    "obovada", "oblonga", "linear", "deltoide", "cordada"
]

MARGENES_VALIDOS = [
    "entero", "serrado", "dentado", "crenado",
    "lobulado", "sinuado"
]

APICES_VALIDOS = [
    "agudo", "acuminado", "obtuso", "redondeado",
    "truncado", "emarginado", "mucronado"
]

BASES_VALIDAS = [
    "cuneada", "redondeada", "cordada", "truncada",
    "atenuada"
]


# ==============================================================
# CURVA BASE: perfil de la mitad de la hoja (silueta simple)
#
# Representamos la hoja como una curva r(t) alrededor de un eje
# central, con t de 0 (base) a 1 (apice), modulada por la forma
# general y luego deformada por apice/base/margen.
# ==============================================================

def _ancho_segun_forma(t, forma):
    """
    Devuelve el "medio ancho" relativo (0 a 1) de la hoja
    en la posicion t (0 = base, 1 = apice), segun la forma
    general elegida.
    """

    if forma == "eliptica":
        return math.sin(t * math.pi)

    if forma == "ovada":
        # mas ancha cerca de la base
        return math.sin(t * math.pi) * (1.3 - 0.5 * t)

    if forma == "obovada":
        # mas ancha cerca del apice (espejo de ovada)
        return math.sin(t * math.pi) * (0.8 + 0.5 * t)

    if forma == "lanceolada":
        # angosta y alargada, maximo ancho antes de la mitad
        pico = 0.35
        return math.sin(t * math.pi) * (1.0 - 0.6 * abs(t - pico))

    if forma == "oblonga":
        # ancho casi constante en el cuerpo, se cierra en los extremos
        cuerpo = min(1.0, math.sin(t * math.pi) * 1.4)
        return cuerpo

    if forma == "linear":
        return math.sin(t * math.pi) * 0.4

    if forma == "orbicular":
        # circular: radio ~ sin(t*pi) pero simetrico y ancho
        return math.sin(t * math.pi) * 1.1

    if forma == "deltoide":
        # triangular: crece linealmente desde la base
        return t * (1.0 - 0.15 * t)

    if forma == "cordada":
        # como ovada pero con un hueco en la base (se ajusta luego)
        return math.sin(t * math.pi) * (1.2 - 0.4 * t)

    # por defecto: eliptica
    return math.sin(t * math.pi)


def _ajuste_apice(t, valor, apice):
    """Modifica el ancho cerca del apice (t cercano a 1)."""

    factor_zona = max(0.0, (t - 0.85) / 0.15)  # 0 lejos, 1 en la punta

    if apice == "agudo":
        return valor * (1 - 0.6 * factor_zona)

    if apice == "acuminado":
        # se afila mas y con una punta mas larga
        return valor * (1 - 0.85 * factor_zona)

    if apice == "obtuso":
        return valor * (1 - 0.25 * factor_zona)

    if apice == "redondeado":
        return valor * (1 - 0.1 * factor_zona)

    if apice == "truncado":
        return valor if t < 0.97 else valor * 0.9

    if apice == "emarginado":
        # pequena muesca en la punta
        if t > 0.96:
            return valor * 0.5
        return valor

    if apice == "mucronado":
        if t > 0.995:
            return valor * 0.3
        return valor * (1 - 0.3 * factor_zona)

    return valor


def _ajuste_base(t, valor, base):
    """Modifica el ancho cerca de la base (t cercano a 0)."""

    factor_zona = max(0.0, (0.12 - t) / 0.12)

    if base == "cuneada":
        return valor * (1 - 0.7 * factor_zona)

    if base == "redondeada":
        return valor * (1 - 0.2 * factor_zona)

    if base == "cordada":
        # el ancho AUMENTA de golpe cerca de la base (lobulos)
        return valor * (1 + 0.6 * factor_zona)

    if base == "truncada":
        return valor if t > 0.03 else valor * 0.85

    if base == "atenuada":
        return valor * (1 - 0.5 * factor_zona)

    return valor


def _textura_margen(t, valor, margen, amplitud, frecuencia, semilla):
    """Agrega textura al borde (dientes, ondas, lobulos)."""

    random.seed(semilla + round(t * 1000))

    if margen == "entero":
        return valor

    if margen in ("serrado", "dentado"):
        onda = math.sin(t * frecuencia * math.pi * 2)
        diente = amplitud * max(0, onda)
        return valor - diente

    if margen == "crenado":
        onda = math.sin(t * frecuencia * math.pi * 2)
        return valor - amplitud * 0.5 * (onda ** 2)

    if margen == "sinuado":
        onda = math.sin(t * frecuencia * math.pi * 2)
        return valor + amplitud * 0.5 * onda

    if margen == "lobulado":
        onda = math.sin(t * frecuencia * math.pi)
        return valor * (0.7 + 0.3 * onda)

    return valor


# ==============================================================
# GENERAR HOJA COMPLETA
# ==============================================================

def generar_hoja(
    forma="eliptica",
    margen="entero",
    apice="agudo",
    base="redondeada",
    relacion_largo_ancho=2.0,
    largo=400,
    num_puntos_lado=200,
    amplitud_margen=0.04,
    frecuencia_margen=14,
    simetria=1.0,
    semilla=None,
):
    """
    Genera la silueta de una hoja como lista de puntos (x, y)
    en el mismo formato/orientacion que usa el extractor:
    origen en el centro, eje y hacia arriba.

    Parametros
    ----------
    forma, margen, apice, base : str
        Ver FORMAS_VALIDAS, MARGENES_VALIDAS, APICES_VALIDOS,
        BASES_VALIDAS.
    relacion_largo_ancho : float
        Que tan alargada es la hoja. 1.0 = casi redonda,
        4-5 = muy alargada (tipo linear).
    largo : float
        Largo total de la hoja en unidades de coordenadas.
    num_puntos_lado : int
        Resolucion del contorno (puntos por lado). Mas puntos
        = contorno mas suave.
    amplitud_margen, frecuencia_margen : float
        Controlan que tan pronunciado/denso es el serrado,
        crenado, etc.
    simetria : float (0 a 1)
        1.0 = ambos lados identicos. Valores menores agregan
        variacion natural entre el lado izquierdo y derecho.
    semilla : int o None
        Fija la aleatoriedad para poder reproducir la misma hoja.

    Retorna
    -------
    dict con metadatos + "puntos": lista de (x, y)
    """

    if semilla is None:
        semilla = random.randint(0, 1_000_000)

    ancho_max = largo / relacion_largo_ancho

    puntos_derecha = []
    puntos_izquierda = []

    for i in range(num_puntos_lado + 1):

        t = i / num_puntos_lado

        valor = _ancho_segun_forma(t, forma)
        valor = _ajuste_base(t, valor, base)
        valor = _ajuste_apice(t, valor, apice)

        valor_d = _textura_margen(
            t, valor, margen,
            amplitud_margen, frecuencia_margen,
            semilla
        )

        valor_i = _textura_margen(
            t, valor, margen,
            amplitud_margen, frecuencia_margen,
            semilla + 999
        )

        # mezclar segun simetria (1.0 = ambos lados iguales)
        valor_i = simetria * valor_d + (1 - simetria) * valor_i

        y = t * largo - largo / 2  # centrado verticalmente

        puntos_derecha.append(
            (max(0.0, valor_d) * ancho_max / 2, y)
        )

        puntos_izquierda.append(
            (-max(0.0, valor_i) * ancho_max / 2, y)
        )

    # contorno cerrado: subir por la derecha, bajar por la izquierda
    contorno = puntos_derecha + list(reversed(puntos_izquierda))

    contorno = [(round(x, 2), round(y, 2)) for x, y in contorno]

    return {
        "id": str(uuid.uuid4())[:8],
        "fuente": "sintetica",
        "forma": forma,
        "margen": margen,
        "apice": apice,
        "base": base,
        "relacion_largo_ancho": relacion_largo_ancho,
        "simetria": simetria,
        "semilla": semilla,
        "num_puntos": len(contorno),
        "puntos": contorno,
    }


# ==============================================================
# GUARDAR EN DISCO
# ==============================================================

def guardar_json(hoja, ruta):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(hoja, f, ensure_ascii=False, indent=2)
    return ruta


def anexar_jsonl(hoja, ruta_dataset):
    """Agrega una hoja como una linea mas de un dataset .jsonl"""
    with open(ruta_dataset, "a", encoding="utf-8") as f:
        f.write(json.dumps(hoja, ensure_ascii=False) + "\n")
    return ruta_dataset


def generar_codigo_tkinter(hoja, nombre_archivo):
    """
    Convierte una hoja generada al mismo formato .py de
    reconstruccion (canvas.create_polygon) que usa tu extractor,
    para poder visualizarla igual que las hojas reales.
    """

    ANCHO_VENTANA = 1000
    ALTO_VENTANA = 800

    xs = [p[0] for p in hoja["puntos"]]
    ys = [p[1] for p in hoja["puntos"]]

    ancho = max(xs) - min(xs)
    alto = max(ys) - min(ys)

    margen_ventana = 60
    escala = min(
        (ANCHO_VENTANA - margen_ventana * 2) / ancho,
        (ALTO_VENTANA - margen_ventana * 2) / alto,
    )

    lineas = []
    lineas.append("import tkinter as tk")
    lineas.append("")
    lineas.append("ventana = tk.Tk()")
    lineas.append('ventana.title("Hoja generada")')
    lineas.append("ventana.geometry('1000x800')")
    lineas.append("ventana.configure(bg='white')")
    lineas.append("")
    lineas.append("canvas = tk.Canvas(ventana, width=1000, height=800, bg='white', highlightthickness=0)")
    lineas.append("canvas.pack()")
    lineas.append("")
    lineas.append("puntos = [")

    for x, y in hoja["puntos"]:
        cx = x * escala + ANCHO_VENTANA / 2
        cy = ALTO_VENTANA / 2 - y * escala
        lineas.append(f"    ({round(cx, 2)}, {round(cy, 2)}),")

    lineas.append("]")
    lineas.append("")
    lineas.append("canvas.create_polygon(puntos, fill='black', outline='black', smooth=True)")
    lineas.append("")
    lineas.append("ventana.mainloop()")

    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))

    return nombre_archivo


# ==============================================================
# EJEMPLO DE USO
# ==============================================================

if __name__ == "__main__":

    hoja = generar_hoja(
        forma="lanceolada",
        margen="serrado",
        apice="acuminado",
        base="cuneada",
        relacion_largo_ancho=2.5,
        semilla=42,
    )

    guardar_json(hoja, "hoja_ejemplo.json")
    generar_codigo_tkinter(hoja, "hoja_ejemplo_visual.py")

    print("Hoja generada:", hoja["id"])
    print("Puntos:", hoja["num_puntos"])
    print("Guardada en hoja_ejemplo.json")
    print("Vista previa en hoja_ejemplo_visual.py")
