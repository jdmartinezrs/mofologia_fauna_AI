"""
==============================================================
MODELO DE FORMA POR ESPECIE (morfometria geometrica)
==============================================================

Toma varias muestras REALES de la misma especie (8-10+),
resuelve la correspondencia de puntos entre ellas, las alinea,
calcula la forma promedio y un modelo PCA de variacion natural.

Con eso, "dame una hoja de mango" deja de ser "repite una foto"
y pasa a ser "genera una silueta nueva, fiel a como varian las
hojas de mango reales que ya fotografiaste".

------------------------------------------------------------
FLUJO
------------------------------------------------------------

1. extraer_puntos(archivo)              -> lee el contorno crudo
2. construir_landmarks(puntos, n_lado)  -> ancla apice/base y
                                            re-muestrea AMBOS
                                            lados por separado,
                                            para que el mismo
                                            indice signifique lo
                                            mismo en toda hoja
3. analisis_procrustes_generalizado()   -> alinea todas las
                                            muestras (traslacion,
                                            rotacion, escala) y
                                            calcula la forma
                                            promedio
4. construir_modelo_pca()               -> modos de variacion
                                            natural de la especie
5. generar_variante()                   -> nueva hoja realista,
                                            muestreada del modelo

------------------------------------------------------------
REQUISITOS DE LAS FOTOS (importante)
------------------------------------------------------------

Para que la deteccion automatica de apice/base funcione bien:

  - Una hoja por foto, extendida y plana (no doblada)
  - Fondo liso y contrastante (esto ya lo pedia tu extractor)
  - No es necesario orientarla siempre igual: el algoritmo
    encuentra el eje largo de la hoja solo. Pero si el peciolo
    (tallito) quedo incluido en el recorte, cortalo antes o el
    algoritmo puede confundir peciolo con base.

==============================================================
"""

import json
import os
import re

import numpy as np


# ==============================================================
# 1. EXTRAER PUNTOS DE UN ARCHIVO *_silueta.py
# ==============================================================

def extraer_puntos(ruta_archivo):
    """
    Lee un archivo *_silueta.py y devuelve SOLO los puntos del
    contorno EXTERIOR (la silueta general de la hoja/planta).

    Importante: cuando la foto genera huecos interiores (comun en
    hojas con perforaciones, o en plantas como suculentas/cactus
    con texturas que el umbral confunde con huecos), el archivo
    trae VARIOS bloques de coordenadas (EXTERIOR + HUECO + DETALLE).
    Si se mezclan todos, la forma queda corrupta. Por eso se
    identifica cada bloque por su comentario "# Tipo: ..." y se
    usa unicamente el EXTERIOR mas grande.
    """
    with open(ruta_archivo, encoding="utf-8") as f:
        contenido = f.read()

    # Dividir el archivo en bloques, cada uno empieza con "# Tipo: X"
    bloques = re.split(r"# Tipo:\s*(\w+)", contenido)

    # re.split con grupo de captura devuelve:
    # [texto_antes, tipo1, texto1, tipo2, texto2, ...]
    if len(bloques) < 3:
        # archivo sin ese formato de comentarios (ej. generado a mano
        # o por el generador parametrico) -> usar todo el archivo
        pares = re.findall(r"\(([-\d.]+),\s*([-\d.]+)\)", contenido)
        return np.array([[float(x), float(y)] for x, y in pares])

    candidatos_exterior = []

    for i in range(1, len(bloques), 2):
        tipo = bloques[i]
        texto_bloque = bloques[i + 1]

        if tipo != "EXTERIOR":
            continue

        # cortar el bloque en el siguiente "]" de cierre de la lista
        # de puntos, para no arrastrar contornos de mas adelante
        cierre = texto_bloque.find("]")
        texto_puntos = texto_bloque[:cierre] if cierre != -1 else texto_bloque

        pares = re.findall(r"\(([-\d.]+),\s*([-\d.]+)\)", texto_puntos)
        puntos = np.array([[float(x), float(y)] for x, y in pares])

        if len(puntos) > 0:
            candidatos_exterior.append(puntos)

    if not candidatos_exterior:
        raise ValueError(
            f"No se encontro un contorno EXTERIOR valido en {ruta_archivo}"
        )

    # si hubiera mas de un EXTERIOR (no deberia pasar), usar el mas grande
    candidatos_exterior.sort(key=len, reverse=True)
    return candidatos_exterior[0]


# ==============================================================
# 2. CORRESPONDENCIA: ANCLAR APICE/BASE Y RE-MUESTREAR POR LADO
# ==============================================================

def _eje_principal(puntos):
    """
    Devuelve el angulo (en radianes) del eje mas largo de la
    hoja, via PCA sobre las coordenadas x,y.
    """
    centrado = puntos - puntos.mean(axis=0)
    cov = np.cov(centrado.T)
    valores, vectores = np.linalg.eigh(cov)
    eje_principal = vectores[:, np.argmax(valores)]
    angulo = np.arctan2(eje_principal[1], eje_principal[0])
    return angulo


def _encontrar_apice_base(puntos):
    """
    Proyecta todos los puntos sobre el eje mas largo de la hoja.
    El extremo con proyeccion maxima = apice (punta).
    El extremo con proyeccion minima = base (donde iria el peciolo).

    Retorna los INDICES (en el arreglo original) del apice y base.
    """
    angulo = _eje_principal(puntos)
    direccion = np.array([np.cos(angulo), np.sin(angulo)])

    centro = puntos.mean(axis=0)
    proyeccion = (puntos - centro) @ direccion

    idx_apice = int(np.argmax(proyeccion))
    idx_base = int(np.argmin(proyeccion))

    return idx_apice, idx_base


def _resamplear_polilinea(polilinea, n_puntos):
    """
    Re-muestrea una polilinea abierta a n_puntos equidistantes
    por longitud de arco (incluye siempre el primer y ultimo punto).
    """
    polilinea = np.asarray(polilinea)

    if len(polilinea) < 2:
        return np.repeat(polilinea, n_puntos, axis=0)

    segmentos = np.linalg.norm(np.diff(polilinea, axis=0), axis=1)
    longitud_acumulada = np.concatenate([[0], np.cumsum(segmentos)])
    longitud_total = longitud_acumulada[-1]

    if longitud_total == 0:
        return np.repeat(polilinea[:1], n_puntos, axis=0)

    objetivos = np.linspace(0, longitud_total, n_puntos)

    x_interp = np.interp(objetivos, longitud_acumulada, polilinea[:, 0])
    y_interp = np.interp(objetivos, longitud_acumulada, polilinea[:, 1])

    return np.column_stack([x_interp, y_interp])


def construir_landmarks(puntos, n_por_lado=100):
    """
    Convierte un contorno crudo (miles de puntos irregulares) en
    un vector de landmarks CON CORRESPONDENCIA: mismo numero de
    puntos, empezando siempre en la base, pasando por un lado
    hasta el apice, y volviendo por el otro lado.

    Retorna un arreglo (2*n_por_lado, 2).
    """
    idx_apice, idx_base = _encontrar_apice_base(puntos)
    n = len(puntos)

    # lado A: de base a apice, avanzando en indices
    if idx_base <= idx_apice:
        lado_a = puntos[idx_base:idx_apice + 1]
    else:
        lado_a = np.vstack([puntos[idx_base:], puntos[:idx_apice + 1]])

    # lado B: de apice a base, continuando en indices (el resto del contorno)
    if idx_apice <= idx_base:
        lado_b = puntos[idx_apice:idx_base + 1]
    else:
        lado_b = np.vstack([puntos[idx_apice:], puntos[:idx_base + 1]])

    lado_a_rs = _resamplear_polilinea(lado_a, n_por_lado)
    lado_b_rs = _resamplear_polilinea(lado_b, n_por_lado)

    # concatenar: base -> apice (lado A) -> base (lado B, sin duplicar apice)
    landmarks = np.vstack([lado_a_rs, lado_b_rs[1:-1]])

    return landmarks


# ==============================================================
# 3. ANALISIS DE PROCRUSTES GENERALIZADO
# ==============================================================

def _procrustes_2_formas(forma, referencia):
    """
    Alinea 'forma' contra 'referencia' (misma cantidad de puntos)
    usando traslacion + rotacion + escala uniforme (sin reflejo).
    Version 2D del algoritmo de Kabsch.
    """
    centro_forma = forma.mean(axis=0)
    centro_ref = referencia.mean(axis=0)

    f = forma - centro_forma
    r = referencia - centro_ref

    escala_f = np.sqrt((f ** 2).sum())
    escala_r = np.sqrt((r ** 2).sum())

    f_norm = f / escala_f
    r_norm = r / escala_r

    matriz_h = f_norm.T @ r_norm
    u, _, vt = np.linalg.svd(matriz_h)
    rotacion = u @ vt

    # evitar reflejo (determinante negativo)
    if np.linalg.det(rotacion) < 0:
        u[:, -1] *= -1
        rotacion = u @ vt

    alineada = (f_norm @ rotacion) * escala_r + centro_ref

    return alineada


def analisis_procrustes_generalizado(lista_landmarks, iteraciones=5):
    """
    Alinea un conjunto de hojas (todas con la misma cantidad de
    landmarks, gracias a construir_landmarks) entre si, e itera
    para converger a una forma promedio estable.

    Retorna (formas_alineadas, forma_promedio).
    """
    formas = [f.copy() for f in lista_landmarks]

    promedio = formas[0].copy()

    for _ in range(iteraciones):
        alineadas = [_procrustes_2_formas(f, promedio) for f in formas]
        nuevo_promedio = np.mean(alineadas, axis=0)
        promedio = nuevo_promedio
        formas = alineadas

    return formas, promedio


# ==============================================================
# 4. MODELO PCA DE VARIACION DE FORMA
# ==============================================================

def detectar_valores_atipicos(formas_alineadas, promedio, nombres=None, factor_std=2.0):
    """
    Compara cada forma alineada contra el promedio y calcula que
    tan lejos esta (distancia RMS punto a punto). Muestras con
    artefactos de extraccion (lineas espurias, peciolo mal
    segmentado, hoja doblada) suelen quedar muy por encima del
    resto en esta distancia.

    Retorna una lista de dicts ordenada de mas a menos sospechosa:
        [{"nombre": ..., "distancia": ..., "atipico": True/False}, ...]
    """
    if nombres is None:
        nombres = [f"muestra_{i}" for i in range(len(formas_alineadas))]

    distancias = [
        float(np.sqrt(np.mean((f - promedio) ** 2)))
        for f in formas_alineadas
    ]

    media = np.mean(distancias)
    desviacion = np.std(distancias)
    umbral = media + factor_std * desviacion

    resultado = [
        {
            "nombre": nombre,
            "distancia": round(dist, 2),
            "atipico": bool(dist > umbral),
        }
        for nombre, dist in zip(nombres, distancias)
    ]

    resultado.sort(key=lambda r: r["distancia"], reverse=True)

    return resultado


def construir_modelo_pca(formas_alineadas, n_componentes=6):
    """
    Convierte cada forma alineada (N, 2) en un vector (2N,),
    y calcula PCA sobre el conjunto.

    Retorna un dict con: promedio, componentes, varianzas, n_puntos.
    """
    matriz = np.array([f.flatten() for f in formas_alineadas])

    promedio = matriz.mean(axis=0)
    centrado = matriz - promedio

    # SVD es mas estable que covarianza+eigh para pocas muestras
    u, s, vt = np.linalg.svd(centrado, full_matrices=False)

    n_disponibles = min(n_componentes, vt.shape[0])
    componentes = vt[:n_disponibles]
    varianzas = (s[:n_disponibles] ** 2) / (matriz.shape[0] - 1)

    return {
        "promedio": promedio.tolist(),
        "componentes": componentes.tolist(),
        "varianzas": varianzas.tolist(),
        "n_puntos": matriz.shape[1] // 2,
        "n_muestras": matriz.shape[0],
    }


def generar_variante(modelo, intensidad=1.0, semilla=None):
    """
    Genera una silueta nueva a partir del modelo de la especie:
    forma promedio + combinacion aleatoria de los modos de
    variacion (PCA), acotada por la varianza real observada.

    intensidad: 1.0 = variacion tipica observada en las fotos.
                > 1.0 = variantes mas extremas (menos realistas).
                < 1.0 = variantes mas conservadoras (mas parecidas
                        al promedio).
    """
    rng = np.random.default_rng(semilla)

    promedio = np.array(modelo["promedio"])
    componentes = np.array(modelo["componentes"])
    varianzas = np.array(modelo["varianzas"])

    coeficientes = rng.normal(0, 1, size=len(varianzas))
    # acotar a +-2 desviaciones estandar (regla estandar en modelos
    # de forma estadisticos, evita siluetas irreales)
    coeficientes = np.clip(coeficientes, -2, 2) * intensidad

    desplazamiento = coeficientes @ (componentes * np.sqrt(varianzas)[:, None])

    vector_final = promedio + desplazamiento

    n_puntos = modelo["n_puntos"]
    return vector_final.reshape(n_puntos, 2)


# ==============================================================
# 5. FLUJO COMPLETO POR ESPECIE
# ==============================================================

def entrenar_especie(nombre_especie, archivos_silueta, n_por_lado=100,
                      n_componentes=6, carpeta_modelos="modelos"):
    """
    Toma una lista de archivos *_silueta.py de la MISMA especie,
    construye landmarks, alinea, y guarda el modelo PCA en disco.
    """
    landmarks_todas = []

    for archivo in archivos_silueta:
        puntos = extraer_puntos(archivo)
        landmarks = construir_landmarks(puntos, n_por_lado=n_por_lado)
        landmarks_todas.append(landmarks)

    formas_alineadas, promedio = analisis_procrustes_generalizado(
        landmarks_todas
    )

    nombres_archivos = [os.path.basename(a) for a in archivos_silueta]
    reporte_atipicos = detectar_valores_atipicos(
        formas_alineadas, promedio, nombres=nombres_archivos
    )

    modelo = construir_modelo_pca(formas_alineadas, n_componentes=n_componentes)
    modelo["especie"] = nombre_especie
    modelo["n_muestras_entrenamiento"] = len(archivos_silueta)
    modelo["reporte_calidad"] = reporte_atipicos

    os.makedirs(carpeta_modelos, exist_ok=True)
    ruta_modelo = os.path.join(carpeta_modelos, f"{nombre_especie}.json")

    with open(ruta_modelo, "w", encoding="utf-8") as f:
        json.dump(modelo, f, ensure_ascii=False, indent=2)

    return modelo, ruta_modelo, reporte_atipicos


def generar_hoja_de_especie(nombre_especie, carpeta_modelos="modelos",
                             intensidad=1.0, semilla=None):
    """
    Carga el modelo entrenado de una especie y genera una hoja nueva.
    Esta es la funcion que responde a "dame una hoja de mango".
    """
    ruta_modelo = os.path.join(carpeta_modelos, f"{nombre_especie}.json")

    with open(ruta_modelo, encoding="utf-8") as f:
        modelo = json.load(f)

    puntos = generar_variante(modelo, intensidad=intensidad, semilla=semilla)

    return {
        "especie": nombre_especie,
        "fuente": "generada_desde_modelo_real",
        "n_muestras_entrenamiento": modelo["n_muestras_entrenamiento"],
        "puntos": [[round(float(x), 2), round(float(y), 2)] for x, y in puntos],
    }


if __name__ == "__main__":
    print("Este modulo se usa importado, ver ejemplo_uso.py")