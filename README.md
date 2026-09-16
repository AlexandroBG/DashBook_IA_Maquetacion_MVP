*[Leer en castellano](#dashbook-ia--de-manuscrito-a-libro-maquetado)*

# DashBook IA — from manuscript to typeset book

This project started with a fairly concrete question: can you take any
manuscript (a PDF, a Word doc, a plain TXT) and turn it into a book with
real typesetting — the kind you could send to a printer or upload to
Amazon KDP — without an editor having to open InDesign by hand?

Short answer: yes, but with some interesting nuances. And those nuances
are what make this project worth talking about.

It works in Spanish, Catalan, French, Italian, and English.

## The core idea

When I started putting AI into this pipeline, I had to make one decision
that shapes everything else: **the AI does not typeset the book.** Not
even close.

I've spent a couple of years now working with language models, and if
there's one thing I've learned, it's that they're excellent at
understanding text and terrible at calculating exact physical things —
like which line, on which page, a given paragraph lands on. Asking a
model to "invent" page numbers is the perfect recipe for a book that
looks right on a quick read and is wrong 10% of the time — which is
exactly the worst place to be wrong when something is headed to print.

So in this project, the AI does what it's good at — understanding and
generating language — and a real composition engine (WeasyPrint, built on
CSS Paged Media) does what it's good at: measuring rendered text,
calculating page breaks, and resolving a table of contents with numbers
that actually exist, not ones someone made up.

## What the program actually does

- **Detects the manuscript's chapters.** It first tries language-specific
  rules (typical patterns for how a chapter is marked). If that fails on
  an unusual manuscript, AI steps in — but only to *locate* where a title
  is written in the text, never to rewrite or summarize anything.
- **Writes the front matter** (half-title, title page, copyright,
  dedication) in the manuscript's own language.
- **Can generate sales copy, if asked**: back-cover synopsis, keywords,
  categories. This is optional, and if it fails, the book still gets
  built — it never blocks the main process.
- **Can run an editorial quality check**: the AI flags things like a
  name spelled two different ways across the book, so a person can
  review it. It never corrects anything on its own, only flags it.
- **Cleans up typography per language**: «angled» quotes in
  es/ca/it/fr, "curly" quotes in English, the thin non-breaking space
  before `; : ! ?` that French requires, fixing line-break hyphens
  carried over from the original document, and so on.
- **Actually composes the PDF**, with:
  - Real page numbering, calculated by the engine — not invented.
  - Mirrored margins with a gutter (inner margin) that changes based on
    how many pages the final book has, following KDP's official table.
    This gets resolved in two passes: the first estimates the page
    count, and with that number, the correct gutter is known for the
    second, final pass.
  - Chapters always starting on an odd (recto) page, inserting a blank
    page when needed — like a real printed book.
  - Widow and orphan control, automatic hyphenation per language.
  - A table of contents with real page numbers, resolved by the engine
    itself.
  - Running heads with the chapter title on every page.

## How it's put together

I split the project into pieces that don't depend on each other more
than they need to, because I knew I'd want to swap things out later (the
AI provider, the rendering engine) without one change quietly breaking
something else.

```
DashBook_IA_Maquetacion/
├── app.py                    # Streamlit interface — just the screen, no business logic
├── config.py                 # Global config: paths, languages, AI settings
│
├── core/                     # The heart of the process, knows nothing about AI or rendering
│   ├── extractor.py           # Pulls text out of PDF/DOCX/TXT/MD
│   ├── cleaner.py              # Cleans and normalizes typography per language
│   ├── structure_detector.py  # Finds the chapters
│   └── book_builder.py         # Orchestrates the whole process end to end
│
├── ai/                        # Everything that touches AI lives here, and only here
│   ├── client.py               # Single entry point into the AI
│   ├── front_matter.py         # Generates half-title, copyright, dedication
│   ├── kdp_metadata.py         # Synopsis and keywords (optional)
│   └── providers/gemini.py     # The provider I use today — swappable
│
├── layout/                    # Everything about typesetting the PDF
│   ├── kdp_rules.py             # KDP's dynamic gutter table
│   ├── engine.py                 # The two-pass composition logic
│   └── templates/                # HTML + CSS defining how the book looks
│
├── models/book.py              # The data: manuscript, chapter, project...
├── tests/                       # Tests for what I most care about not breaking
└── data/, logs/, requirements.txt, .env.example
```

**Why organize it this way?** Because if tomorrow I want to switch from
Gemini to another model, or swap WeasyPrint for a more powerful
composition engine, I don't want to hunt through file after file to find
where to make the change. With this structure, I touch one piece (say,
`ai/providers/gemini.py`) and the rest of the project doesn't even
notice.

## Getting it running

```bash
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your API key:

```bash
cp .env.example .env
```

```env
AI_PROVIDER=gemini
AI_API_KEY=your_key_here
AI_MODEL=gemini-2.5-flash
```

If something in `.env` isn't set up right, the interface warns you the
moment it starts — before you can upload a manuscript. I'd rather it
fail there than fail halfway through, after you've already lost five
minutes.

### Trying it without your own manuscript

The Streamlit interface has a "use sample manuscript" checkbox, made
exactly for this: so anyone can see the full pipeline working in a
couple of minutes.

```bash
streamlit run app.py
```

### From the command line

```bash
python -m core.book_builder
```

It'll ask for the manuscript path, title, author, language, and trim
size, and leave the finished PDF in `data/output/`.

### From your own code

```python
from core.book_builder import build_book
from models.book import BookMetadata

metadata = BookMetadata(
    title="El regreso a casa",
    author="Ana Pérez",
    language="es",
    year=2026,
    trim_size="6x9",
)
project = build_book("manuscrito.docx", metadata)
print(project.output_pdf_path, project.estimated_page_count)
```

## The path a manuscript follows

```
Manuscript (PDF/DOCX/TXT/MD)
        │
Text gets extracted
        │
Typography gets cleaned and normalized
        │
Chapters get detected
        │
AI drafts the front matter
        │
Two-pass composition (page count → gutter → final PDF)
        │
Typeset book, ready in data/output/
```

## Tests

```bash
pytest
```

They cover what I actually worry about breaking without noticing:
per-language typography (including the French thin-space rule), the
gutter table's limits, text extraction, the AI layer (no real calls,
just logic), and configuration failing clearly when something's not set
up right.

## Before sending it to print

- The dynamic gutter follows KDP's public table, which is a solid
  starting point but not the only standard out there — it's worth
  checking your specific printer's requirements.
- Everything the AI generates (front matter, table of contents) needs
  to be reviewed by a person before the book is signed off. AI helps,
  it doesn't decide.

## What's next

1. Testing with real, long manuscripts (100+ pages) across all five
   languages.
2. Templates for non-fiction and illustrated children's books.
3. Looking into a more powerful rendering engine, if more typographic
   precision than WeasyPrint offers is ever needed.
4. Persistence and multiple users, once the MVP has proven its worth.

---

*[Read in English](#dashbook-ia--from-manuscript-to-typeset-book)*

# DashBook IA — de manuscrito a libro maquetado

Este proyecto nació de una pregunta bastante concreta: ¿se puede coger un
manuscrito cualquiera (un PDF, un Word, un TXT) y convertirlo en un libro
con maquetación de verdad, de las que se pueden llevar a imprenta o subir a
Amazon KDP, sin que un editor tenga que tocar InDesign a mano?

La respuesta corta es sí, pero con matices interesantes. Y esos matices son
los que hacen que este proyecto merezca la pena contarlo.

Funciona en castellano, català, français, italiano e inglés.

## La idea de fondo

Cuando empecé a meterle IA a este pipeline, tuve que tomar una decisión que
condiciona todo lo demás: **la IA no maqueta el libro**. Ni de casualidad.

Llevo un par de años trabajando con modelos de lenguaje y si algo he
aprendido es que son buenísimos entendiendo texto y fatales calculando cosas
físicas y exactas — como en qué línea de qué página cae un párrafo concreto.
Pedirle a un modelo que "invente" la numeración de páginas es la receta
perfecta para que el libro parezca correcto en una lectura rápida y esté
mal en el 10% de los casos, que es justo el peor sitio para fallar en algo
que va a imprenta.

Así que en este proyecto la IA hace lo que se le da bien —entender y generar
lenguaje— y un motor de composición real (WeasyPrint, basado en CSS Paged
Media) hace lo que se le da bien a él: medir texto, calcular saltos de
página y resolver un índice con números que existen de verdad, no que
alguien se ha inventado.

## Qué hace el programa, en la práctica

- **Detecta los capítulos del manuscrito.** Primero lo intenta con reglas
  específicas de cada idioma (patrones típicos de cómo se marca un
  capítulo). Si eso falla en un manuscrito raro, entra la IA — pero solo
  para *localizar* dónde está escrito el título dentro del texto, nunca
  para reescribir ni resumir nada.
- **Redacta el front matter** (portadilla, página de título, copyright,
  dedicatoria) en el idioma del manuscrito.
- **Puede generar, si se le pide, los textos de venta**: la sinopsis de
  contraportada, palabras clave, categorías. Esto es opcional y si falla,
  el libro se compone igual — nunca bloquea el proceso principal.
- **Puede pasar un control de calidad editorial**: la IA señala cosas como
  un nombre escrito de dos formas distintas a lo largo del libro, para que
  lo revise una persona. No corrige nada por su cuenta, solo avisa.
- **Limpia la tipografía según el idioma**: comillas «angulares» en
  es/ca/it/fr, comillas curvas en inglés, el espacio fino antes de `; : ! ?`
  que exige el francés, arregla guiones de corte de línea que suele traer
  el documento original, etc.
- **Compone el PDF de verdad**, con:
  - Numeración de página calculada por el motor, no inventada.
  - Márgenes espejo con un gutter (margen interior) que cambia según
    cuántas páginas tenga el libro final, siguiendo la tabla oficial de
    KDP. Esto se resuelve en dos pasadas: la primera calcula cuántas
    páginas va a tener el libro, y con ese dato ya se sabe qué gutter le
    corresponde para la segunda pasada, la definitiva.
  - Los capítulos siempre empiezan en página impar, metiendo una página en
    blanco si hace falta — como en un libro de verdad.
  - Control de viudas y huérfanas, guionado automático según el idioma.
  - Un índice con números de página reales, resueltos por el propio motor.
  - Cabeceras vivas con el título del capítulo en cada página.

## Cómo está montado por dentro

Separé el proyecto en piezas que no dependen unas de otras más de lo
necesario, porque sabía que iba a querer cambiar cosas sobre la marcha (el
proveedor de IA, el motor de render, etc.) sin que un cambio en un sitio
rompiera otro sin avisar.

```
DashBook_IA_Maquetacion/
├── app.py                    # Interfaz Streamlit — solo la pantalla, sin lógica
├── config.py                 # Configuración: rutas, idiomas, IA
│
├── core/                     # El corazón del proceso, sin saber nada de IA ni de render
│   ├── extractor.py           # Saca el texto de PDF/DOCX/TXT/MD
│   ├── cleaner.py              # Limpia y normaliza la tipografía por idioma
│   ├── structure_detector.py  # Encuentra los capítulos
│   └── book_builder.py         # Orquesta todo el proceso, de principio a fin
│
├── ai/                        # Todo lo que toca IA vive aquí, y solo aquí
│   ├── client.py               # Único punto de entrada a la IA
│   ├── front_matter.py         # Genera portadilla, copyright, dedicatoria
│   ├── kdp_metadata.py         # Sinopsis y palabras clave (opcional)
│   └── providers/gemini.py     # El proveedor que uso hoy — cambiable
│
├── layout/                    # Todo lo relativo a maquetar el PDF
│   ├── kdp_rules.py             # Tabla de gutter dinámico de KDP
│   ├── engine.py                 # La doble pasada de composición
│   └── templates/                # HTML + CSS que define cómo se ve el libro
│
├── models/book.py              # Los datos: manuscrito, capítulo, proyecto...
├── tests/                       # Tests de lo que más me importa que no se rompa
└── data/, logs/, requirements.txt, .env.example
```

**¿Por qué separarlo así?** Porque si mañana quiero cambiar de Gemini a
otro modelo, o cambiar WeasyPrint por un motor de composición más potente,
no quiero tener que ir archivo por archivo buscando dónde toco. Con esta
estructura, cambio una pieza (`ai/providers/gemini.py`, por ejemplo) y el
resto del proyecto ni se entera.

## Cómo lo pongo a funcionar

```bash
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copio `.env.example` a `.env` y relleno mi clave de la API:

```bash
cp .env.example .env
```

```env
AI_PROVIDER=gemini
AI_API_KEY=tu_clave_aqui
AI_MODEL=gemini-2.5-flash
```

Si algo en `.env` no está bien configurado, la interfaz avisa nada más
arrancar — antes de dejarte subir ningún manuscrito. Prefiero que falle ahí
a que falle a mitad del proceso, cuando ya has perdido cinco minutos.

### Para probarlo sin manuscrito propio a mano

La interfaz de Streamlit trae una casilla de "usar manuscrito de ejemplo",
pensada justo para eso: para que cualquiera pueda ver el pipeline completo
funcionando en un par de minutos.

```bash
streamlit run app.py
```

### Desde la terminal

```bash
python -m core.book_builder
```

Te pregunta la ruta del manuscrito, título, autor, idioma y tamaño de
página, y te deja el PDF terminado en `data/output/`.

### Desde tu propio código

```python
from core.book_builder import build_book
from models.book import BookMetadata

metadata = BookMetadata(
    title="El regreso a casa",
    author="Ana Pérez",
    language="es",
    year=2026,
    trim_size="6x9",
)
project = build_book("manuscrito.docx", metadata)
print(project.output_pdf_path, project.estimated_page_count)
```

## El camino que sigue un manuscrito

```
Manuscrito (PDF/DOCX/TXT/MD)
        │
Se extrae el texto
        │
Se limpia y normaliza la tipografía
        │
Se detectan los capítulos
        │
La IA redacta el front matter
        │
Se compone en dos pasadas (páginas → gutter → PDF final)
        │
Libro maquetado, listo en data/output/
```

## Tests

```bash
pytest
```

Cubren lo que de verdad me preocupa que se rompa sin darme cuenta: la
tipografía por idioma (incluida la regla francesa del espacio fino), los
límites de la tabla de gutter, la extracción de texto, la capa de IA (sin
llamadas reales, solo lógica) y que la configuración falle de forma clara
cuando algo no está bien puesto.

## Antes de mandarlo a imprenta

- El gutter dinámico sigue la tabla pública de KDP, que es un buen punto de
  partida pero no la única norma que existe — conviene revisar los
  requisitos concretos de tu imprenta.
- Todo lo que genera la IA (front matter, índice) lo tiene que revisar una
  persona antes de dar el libro por bueno. La IA ayuda, no decide.

## Lo que tengo pendiente

1. Probar con manuscritos reales largos (100+ páginas) en los cinco idiomas.
2. Plantillas para no ficción y libro infantil/ilustrado.
3. Mirar un motor de render más potente si algún día hace falta más
   precisión tipográfica de la que da WeasyPrint.
4. Persistencia y varios usuarios, cuando el MVP haya demostrado que vale
   la pena.