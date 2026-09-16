# DashBook IA Maquetación

Fábrica de libros maquetados: convierte un manuscrito (PDF, DOCX, TXT o
Markdown) en un libro con **paginación real**, listo para imprenta o
para subir a Amazon KDP.

Idiomas soportados: **castellano, català, français, italiano, English.**

## Qué hace, exactamente

- Detecta automáticamente la estructura de capítulos del manuscrito
  (heurística por patrones específica de cada idioma + fallback con IA
  para casos difíciles — el modelo solo *localiza* títulos literales
  dentro del texto, nunca reescribe ni resume contenido).
- Genera el front matter (portadilla, página de título, copyright,
  dedicatoria) con IA, en el idioma del manuscrito.
- Genera, opcionalmente, **metadatos comerciales para la ficha de
  venta** (sinopsis de contraportada, palabras clave, categorías) —
  "front matter hacia afuera": lo que ve un lector en la tienda, nunca
  dentro del PDF. Si este paso falla, el libro se compone igual.
- Ejecuta, opcionalmente, un **control de calidad editorial** con IA
  que señala posibles inconsistencias (un nombre escrito de dos formas
  distintas, por ejemplo) para que un editor humano decida — la IA
  nunca modifica el texto del autor, solo lo señala. Si este paso
  falla, el libro se compone igual.
- Limpia y normaliza la tipografía por idioma: comillas «guillemets» en
  es/ca/it/fr, comillas "curly" en inglés, espacio fino insecable antes
  de `; : ! ?` en francés (regla de la Imprimerie Nationale), rayas de
  diálogo, arreglo de guiones de corte de línea heredados del documento
  original.
- Compone el libro con **CSS Paged Media** (vía WeasyPrint):
  - Numeración de página real (no inventada), calculada por el motor
    de composición, no por el modelo de IA.
  - Márgenes espejo con **gutter dinámico** según el número de páginas
    final del libro (tabla oficial de KDP). Se resuelve en **doble
    pasada**: una primera composición estima el nº de páginas, y la
    segunda (definitiva) recalcula el gutter con el nº de páginas real.
  - Capítulos que siempre inician en página recta (impar), con página
    en blanco automática cuando hace falta.
  - Control de viudas y huérfanas, guionado automático por idioma.
  - Índice con números de página verdaderos, resueltos por el propio
    motor de composición (`target-counter`), no por la IA.
  - Cabeceras vivas (running heads) con el título del capítulo.

## Qué NO hace (todavía)

- Solo existe una plantilla de estilo ("novel"). Falta una para no
  ficción y otra para libros infantiles/ilustrados.
- No valida automáticamente contra todas las reglas de una imprenta
  específica más allá del gutter — revisa siempre los requisitos
  exactos de tu proveedor de impresión antes de enviar el archivo
  final.
- La detección de capítulos asume manuscritos con marcadores
  razonablemente estándar ("Capítulo 1", "Chapter One", etc.);
  manuscritos sin ninguna convención de títulos dependen por completo
  del fallback de IA.
- No hay OCR: un PDF escaneado (imagen) no tiene texto extraíble y el
  pipeline lo rechazará explícitamente en vez de generar un PDF vacío.
- No hay persistencia, historial de proyectos ni multiusuario — esto
  es un MVP demostrable, no un producto empresarial (ver roadmap al
  final).

## Arquitectura

```
DashBook_IA_Maquetacion/
├── app.py                       # Interfaz Streamlit (capa fina, sin lógica de negocio)
├── config.py                    # Configuración global: rutas, idiomas, IA
│
├── core/                        # Pipeline de negocio, independiente de la IA y del render
│   ├── errors.py                # PipelineError / AIProviderError
│   ├── extractor.py             # Extracción de texto (PDF/DOCX/TXT/MD)
│   ├── cleaner.py                # Limpieza y normalización tipográfica por idioma
│   ├── structure_detector.py    # Detección de capítulos (heurística + fallback IA)
│   └── book_builder.py           # Orquestador del pipeline completo + CLI
│
├── ai/                           # Toda la dependencia de un proveedor de IA vive aquí
│   ├── client.py                 # Punto único de entrada: generate_json()
│   ├── front_matter.py           # Generación de front matter (usa ai.client)
│   ├── kdp_metadata.py           # Sinopsis/keywords/categorías comerciales (opcional)
│   ├── quality_check.py          # Observaciones de consistencia editorial (opcional)
│   └── providers/
│       ├── base.py               # Interfaz AIProvider
│       └── gemini.py             # Único proveedor implementado hoy
│
├── layout/                       # Todo lo relativo a la composición del PDF
│   ├── kdp_rules.py               # Trim sizes + tabla de gutter dinámico (KDP)
│   ├── render_backend.py         # Interfaz de motor de render + WeasyPrintBackend
│   ├── engine.py                  # Orquesta la doble pasada de composición
│   └── templates/
│       ├── novel.html
│       └── novel.css
│
├── models/
│   └── book.py                    # Modelos Pydantic: Manuscript, Chapter, BookProject...
│
├── utils/
│   └── logging.py                 # Logger, timer con callback de progreso, rutas seguras
│
├── tests/                         # Tests de humo de lo que más importa: tipografía,
│                                   # gutter, extracción, capa de IA, configuración
│
├── data/
│   ├── sample/                    # Manuscrito de ejemplo para la demo rápida
│   ├── input/                     # Manuscritos subidos (no versionado)
│   └── output/                    # PDFs generados (no versionado)
├── logs/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

### Por qué está organizado así

- **`core/` no sabe nada de IA ni de render.** Solo conoce modelos de
  datos y reglas de negocio (extracción, limpieza, heurística de
  capítulos). Esto es lo que permite que `ai/` y `layout/` evolucionen
  — o se sustituyan — sin arrastrar cambios al resto del pipeline.
- **`ai/` es la única puerta de entrada a un proveedor de IA.** Ningún
  otro módulo importa `google.genai` ni ningún otro SDK directamente.
  Ver más abajo cómo cambiar de modelo o de proveedor.
- **`layout/` separa la interfaz de render (`render_backend.py`) de la
  orquestación (`engine.py`).** WeasyPrint es la implementación de hoy,
  pero no la única posible: un motor más avanzado (p. ej. un motor
  comercial de CSS Paged Media) se añadiría como una nueva clase que
  implemente `RenderBackend`, sin tocar `engine.py` ni las plantillas.

## Arquitectura: por qué la IA no pagina el libro

Un modelo de lenguaje no puede calcular dónde cae físicamente una línea
de texto en una página de un tamaño y tipografía específicos. Pedirle
a una IA que "invente" números de página o saltos de página produce
resultados incorrectos con total confianza.

Por eso, en este proyecto:

- **La IA se usa solo para tareas de lenguaje**: detectar títulos de
  capítulo cuando la heurística falla (localizándolos literalmente en
  el texto, sin reescribirlo), y redactar el front matter.
- **WeasyPrint (motor CSS Paged Media) hace toda la composición
  real**: mide el texto renderizado, calcula saltos de página, resuelve
  la numeración y el índice.

Esta separación es la que garantiza que el PDF final tenga datos
reales, no aproximaciones generadas por IA — y es la razón por la que
`ai/` y `layout/` son paquetes completamente independientes entre sí.

## Instalación

```bash
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## Configuración del `.env`

Copia `.env.example` a `.env`:

```bash
cp .env.example .env
```

Y edítalo:

```env
AI_PROVIDER=gemini
AI_API_KEY=tu_clave_aqui
AI_MODEL=gemini-2.5-flash
```

Si `.env` no está configurado correctamente, la interfaz avisa **al
arrancar**, antes de aceptar ningún manuscrito — no vas a descubrir el
problema a mitad del proceso.

### Cómo introducir la API key

Pega tu clave en `AI_API_KEY` dentro de `.env`. Nunca la escribas en el
código ni la subas al repositorio (`.env` ya está en `.gitignore`).

### Cómo seleccionar el modelo

Cambia `AI_MODEL` en `.env` por el identificador del modelo que quieras
usar dentro del proveedor activo (por ejemplo, otro modelo de la
familia Gemini). No requiere tocar código.

### Cómo cambiar de proveedor de IA en el futuro

1. Crea `ai/providers/<nombre>.py` con una clase que implemente la
   interfaz `AIProvider` (un único método: `generate_json(prompt) -> dict`).
2. Regístrala en `ai/client.py`, en `_build_provider()`.
3. Pon `AI_PROVIDER=<nombre>` en tu `.env`.

Ningún otro archivo del proyecto necesita cambios: `core/structure_detector.py`
y `ai/front_matter.py` solo llaman a `ai.client.generate_json(...)`, sin
saber qué proveedor hay detrás.

## Ejecución

### Interfaz web (Streamlit)

```bash
streamlit run app.py
```

La interfaz incluye una casilla **"Usar manuscrito de ejemplo"** para
ver el pipeline completo funcionando en segundos, sin necesitar un
manuscrito propio a mano — útil para una primera demostración.

### Línea de comandos

```bash
python -m core.book_builder
```

Te pedirá la ruta del manuscrito, título, autor, idioma y trim size, y
generará el PDF maquetado en `data/output/`.

### Como librería, desde tu propio código

```python
from core.book_builder import build_book
from models.book import BookMetadata

metadata = BookMetadata(
    title="El regreso a casa",
    author="Ana Pérez",
    language="es",       # es | ca | fr | it | en
    year=2026,
    trim_size="6x9",
)
project = build_book("manuscrito.docx", metadata)
print(project.output_pdf_path, project.estimated_page_count)
```

## Flujo de procesamiento

```
manuscrito (PDF/DOCX/TXT/MD)
        │
        ▼
core.extractor        → texto plano con párrafos normalizados
        │
        ▼
core.cleaner           → tipografía normalizada por idioma
        │
        ▼
core.structure_detector → lista de capítulos (heurística, o IA si falla)
        │
        ▼
ai.front_matter         → portadilla, portada, copyright, dedicatoria (IA)
        │
        ▼
layout.engine            → doble pasada de composición (WeasyPrint)
        │                    1ª: estimación de páginas → gutter provisional
        │                    2ª: nº de páginas real → gutter definitivo → PDF
        ▼
   PDF maquetado (data/output/)
```

## Tests

```bash
pytest
```

Cubren lo que más importa para la precisión editorial y la
mantenibilidad: normalización tipográfica por idioma (incluida la
regla francesa), los límites de la tabla de gutter dinámico,
extracción de texto y sus errores de negocio, la capa de IA (parseo
JSON y manejo de errores, sin red real), y la validación de
configuración.

## Ejecución en producción / imprenta

- Revisa siempre los requisitos exactos de tu proveedor de impresión
  antes de enviar el archivo final: el gutter dinámico de este proyecto
  sigue la tabla pública de Amazon KDP, que es un punto de partida
  razonable pero no universal.
- El front matter y el índice generados por IA deben verificarse
  siempre por un editor humano antes de mandar a imprenta.

## Próximos pasos sugeridos

1. Probar con manuscritos reales largos (100+ páginas) en los 5 idiomas.
2. Añadir plantillas para no ficción y libro infantil/ilustrado.
3. Evaluar un backend de render de mayor precisión (implementando
   `RenderBackend`) sobre un manuscrito real, si la editorial necesita
   un salto de calidad tipográfica más allá de WeasyPrint.
4. Persistencia y multiusuario, cuando el MVP haya demostrado su valor.
