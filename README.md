# Dataset de Siluetas de Hojas

Proyecto para construir un dataset de coordenadas de siluetas de
hojas por especie, y generar hojas nuevas ("dame una hoja de mango")
a partir de un modelo estadístico de forma entrenado con fotos reales.

## Estructura

```
dataset_hojas/
├── src/
│   ├── extractor_siluetas.py          # foto -> coordenadas (usa OpenCV)
│   ├── generador_hojas_parametrico.py # genera hojas desde parámetros botánicos
│   ├── convertir_a_maxscript.py       # coordenadas -> MAXScript (3ds Max, extrusión 3D)
│   ├── modelo_forma_especie.py        # librería: correspondencia, Procrustes, PCA
│   ├── entrenar_todo.py               # entrena el modelo de TODAS las especies
│   └── generar.py                     # genera hojas desde un modelo ya entrenado
│
├── fotos_procesadas/
│   └── <nombre_especie>/
│       └── *_silueta.py               # salida del extractor, una por foto
│
├── modelos/                            # se llena solo al entrenar (.json por especie)
├── hojas_generadas/                    # se llena solo al generar (.json por hoja)
│
├── requirements.txt
└── .vscode/                            # configuración lista de VS Code
```

## Instalación (primera vez)

1. Abre esta carpeta en VS Code: `File → Open Folder...`
2. Abre una terminal integrada (`` Ctrl+` ``) y crea un entorno virtual:
   ```
   python -m venv .venv
   ```
3. Actívalo:
   - Windows: `.venv\Scripts\activate`
   - Mac/Linux: `source .venv/bin/activate`
4. Instala dependencias:
   ```
   pip install -r requirements.txt
   ```
5. En VS Code, `Ctrl+Shift+P` → **Python: Select Interpreter** → elige el que dice `.venv`

## Flujo de trabajo

1. **Extraer una hoja real de una foto:**
   Corre `src/extractor_siluetas.py` (F5 con la config *"1) Extractor de siluetas"*,
   o `python src/extractor_siluetas.py`). Te pedirá seleccionar una imagen y
   generará un `*_silueta.py` junto a la foto.

   Mueve ese archivo a `fotos_procesadas/<especie>/`. Repite con 8-10 fotos
   por especie.

2. **Entrenar los modelos:**
   ```
   python src/entrenar_todo.py
   ```
   (o F5 con la config *"2) Entrenar todos los modelos"*)

   Genera `modelos/<especie>.json` para cada especie con suficientes muestras.

3. **Generar hojas nuevas:**
   ```
   python src/generar.py mango --cantidad 5
   ```
   Deja los resultados en `hojas_generadas/`.

## Notas

- Cada especie necesita **mínimo 5 muestras** (recomendado 8-10) para
  entrenar un modelo con sentido.
- Una hoja por foto, extendida y plana, fondo liso.
- Si el peciolo (tallito) queda muy largo en el recorte, la detección
  automática de ápice/base puede confundirse — recórtalo si es posible.
