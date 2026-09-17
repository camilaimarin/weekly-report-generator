# weekly-report

Genera un reporte semanal de trabajo en HTML a partir de tus commits, con los
textos redactados por un modelo local (Ollama) y una entrevista corta que
llena lo que git no sabe.

La regla que ordena todo el proyecto: **el modelo escribe, pero nunca cuenta**.
Los números —commits, líneas, archivos, comparación contra la semana
anterior— se calculan en Python y llegan a la plantilla sin pasar por el
modelo. El esquema que se le entrega al LLM no tiene un solo campo numérico,
así que no puede inventar una métrica aunque quiera.

## Cómo funciona

```
fuentes → Activity → caché semanal → estadísticas ─┬→ métricas (Python)
                                                   └→ borrador (Ollama)
                                                          ↓
                                              entrevista → Report → HTML
```

1. **Fuentes.** Cada fuente lee un sistema y devuelve `Activity`. Hoy hay una:
   `git_local`, que lee `git log` de los repositorios que configures.
2. **Caché.** Las actividades de la semana se guardan en `data/AAAA-Wnn.json`.
   La segunda corrida no vuelve a tocar git; `--refresh` fuerza la relectura.
3. **Estadísticas.** Commits, líneas y archivos por día y por proyecto, más la
   comparación contra la semana anterior.
4. **Borrador.** El modelo recibe los commits agrupados por día y devuelve
   JSON validado contra un esquema de Pydantic: foco, resumen, logros y una
   línea por día. Después se revisa lo que escribió y se avisa si mencionó un
   proyecto que no existe, un día de otra semana o un número que no está en
   los datos.
5. **Entrevista.** Pregunta lo que ningún commit sabe: estado de cada
   proyecto, bloqueos, qué quedó a medias, el plan de la próxima semana. Todo
   lo que se puede proponer viene con un valor por omisión: Enter lo acepta.
6. **HTML.** Una plantilla Jinja2 con nueve secciones. Las que no tienen datos
   no se pintan, y las demás se renumeran solas.

## Requisitos

- Python 3.12 o superior
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) corriendo en local, con algún modelo de texto
  descargado (por omisión se usa `qwen3:4b`). También puedes prescindir de él
  con `--no-llm` y escribir los textos tú.

## Instalación

```bash
git clone <este-repo>
cd weekly-report-generator
uv sync
```

## Configuración

```bash
cp config.example.toml config.toml
```

`config.toml` queda fuera de git porque lleva las rutas de tus repositorios y
tus correos. Lo mínimo que hay que editar:

```toml
author = "Tu nombre"
role = "Tu puesto"                 # sale bajo el título del reporte
timezone = "America/Mexico_City"   # decide a qué día pertenece cada commit
model = "qwen3:4b"

emails = ["tu@correo.com"]         # todos con los que haces commits

# Lo que no cuenta como líneas escritas. Acepta nombres, comodines, rutas
# y carpetas completas terminadas en "/".
ignore_files = ["uv.lock", "*.min.js", "vendor/"]

[[repos]]
path = "~/Src/mi-pipeline"
project = "PIPE"                   # el código corto que aparece como etiqueta
```

Un commit que solo toca archivos ignorados sigue contando como actividad;
simplemente no suma líneas.

`config.toml`, `data/` y `output/` están en `.gitignore` a propósito: los dos
últimos guardan tus mensajes de commit y el texto de tus reportes. Si
clonas esto en un repositorio público, revisa que sigan ignorados.

## Uso

```bash
uv run weekly-report
```

Hace las preguntas y deja el reporte en `output/AAAA-Wnn.html`, junto con el
`Report` en JSON.

| Bandera | Para qué |
|---|---|
| `--week 2026-09-14` | Otra semana. Acepta cualquier día; calcula el lunes. |
| `--refresh` | Relee git aunque haya caché. Útil al final de la semana. |
| `--no-llm` | Sin Ollama: los textos los escribes tú. |
| `--render-only` | Regenera el HTML de un reporte ya capturado, sin preguntar nada. |
| `--config ruta.toml` | Otro archivo de configuración. |

`--render-only` es el que conviene tener a mano si vas a tocar la plantilla:
evita repetir la entrevista.

## Agregar una fuente

Una fuente implementa `Source` y devuelve actividades dentro del rango
`[start, end)`:

```python
from weekly_report.models import Activity
from weekly_report.sources.base import Source

class MiFuente(Source):
    name = "mi_fuente"

    def collect(self, start, end) -> list[Activity]:
        ...
```

`Activity` es deliberadamente genérica (`source`, `project`, `timestamp`,
`title`, `kind`, `ref`, `body`, `extra`), para que un ticket o una reunión
quepan igual que un commit. Lo que no aplique a tu fuente puede faltar: las líneas de
código se leen con `extra.get(campo, 0)`, así que una fuente sin código suma
cero en lugar de romper.

## Desarrollo

```bash
uv run pytest
```

Los tests no tocan git, ni Ollama, ni tu configuración: las fuentes se simulan
y el disco se escribe en carpetas temporales.

```
src/weekly_report/
  models.py      contrato del reporte, con las reglas que debe cumplir
  sources/       de dónde salen las actividades
  cache.py       recolección y caché por semana
  aggregate.py   números por día y por proyecto
  llm.py         borrador con Ollama y revisión de lo que escribió
  interview.py   las preguntas que git no puede contestar
  render.py      HTML desde el Report
  formats.py     fechas y números en español
  cli.py         el comando
```

## Estado

Proyecto personal, en construcción. Falta exportar a PDF, y la única fuente
implementada es git.
