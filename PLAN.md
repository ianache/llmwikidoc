# llmwikidoc — Plan de Implementación

## Objetivo

CLI en Python que, al hacer `git commit` en cualquier proyecto, captura el contexto completo del commit y actualiza automáticamente una wiki en markdown dentro del mismo repo, siguiendo el patrón LLM Wiki de Karpathy con extensiones v2.

---

## Estructura del proyecto

```
llmwikidoc/                        ← este repo (la herramienta)
├── pyproject.toml
├── uv.lock
├── .python-version
├── src/
│   └── llmwikidoc/
│       ├── __init__.py
│       ├── cli.py                 ← CLI principal (typer)
│       ├── config.py              ← configuración por proyecto (.llmwikidoc.toml)
│       ├── git_reader.py          ← extrae datos del commit (gitpython)
│       ├── ingest.py              ← pipeline de ingesta: commit → wiki
│       ├── llm.py                 ← cliente Gemini (google-genai)
│       ├── wiki.py                ← gestión de archivos wiki
│       ├── graph.py               ← knowledge graph (networkx) — v2
│       ├── confidence.py          ← confidence scoring por hecho — v2
│       ├── search.py              ← búsqueda híbrida BM25+vector+graph — v2
│       └── lint.py                ← health checks, contradicciones — v2
├── hooks/
│   └── post-commit                ← template del git hook
└── tests/
    ├── conftest.py
    ├── test_git_reader.py
    ├── test_ingest.py
    ├── test_graph.py
    ├── test_confidence.py
    ├── test_search.py
    └── test_lint.py
```

### Estructura wiki generada (dentro del proyecto documentado)

```
mi-proyecto/
├── wiki/
│   ├── index.md                   ← catálogo navegable por categoría
│   ├── log.md                     ← log append-only de todas las operaciones
│   ├── graph.json                 ← knowledge graph serializado
│   ├── entities/                  ← páginas de entidades (clases, funciones, módulos)
│   │   └── <nombre>.md
│   ├── concepts/                  ← páginas de conceptos y decisiones
│   │   └── <nombre>.md
│   └── summaries/                 ← resúmenes de commits y sesiones
│       └── <sha>.md
└── .llmwikidoc.toml               ← config: modelo, rutas, opciones
```

---

## Stack técnico

| Componente | Librería |
|---|---|
| CLI | `typer` + `rich` |
| Gemini LLM | `google-genai` |
| Git | `gitpython` |
| Knowledge graph | `networkx` |
| BM25 | `rank-bm25` |
| Vector embeddings | `google-genai` (`gemini-embedding-001`) |
| Configuración | `tomli` / `tomllib` (stdlib 3.11+) |
| Tests | `pytest` + `pytest-mock` |

**Modelo por defecto:** `gemini-2.5-flash` (balance costo/calidad para alto volumen de commits)

---

## Comandos CLI

```bash
llmwikidoc init          # inicializa wiki + instala git hook en el proyecto actual
llmwikidoc ingest        # ingestar el último commit manualmente
llmwikidoc query "..."   # consultar la wiki en lenguaje natural
llmwikidoc lint          # health check: contradicciones, páginas huérfanas, stale claims
llmwikidoc status        # mostrar estadísticas de la wiki
```

---

## Flujo de ingesta (post-commit hook)

```
git commit
    └── .git/hooks/post-commit
            └── llmwikidoc ingest
                    ├── 1. git_reader: extrae commit
                    │       ├── mensaje del commit
                    │       ├── diff completo (patch)
                    │       ├── contenido completo de archivos modificados
                    │       └── contenido de archivos relacionados (imports, callers)
                    │
                    ├── 2. llm.py: envía a Gemini → extrae
                    │       ├── entidades (clases, funciones, módulos, decisiones)
                    │       ├── relaciones entre entidades
                    │       ├── hechos nuevos con confidence score inicial
                    │       └── posibles contradicciones con wiki existente
                    │
                    ├── 3. wiki.py: actualiza/crea páginas markdown
                    │       ├── summaries/<sha>.md  ← resumen del commit
                    │       ├── entities/<nombre>.md ← crea o actualiza
                    │       ├── concepts/<nombre>.md ← crea o actualiza
                    │       ├── index.md             ← actualiza catálogo
                    │       └── log.md               ← append entry
                    │
                    ├── 4. graph.py: actualiza knowledge graph
                    │       ├── nodos: entidades extraídas
                    │       └── aristas tipadas: "uses", "depends_on", "modifies", "fixes"
                    │
                    └── 5. confidence.py: actualiza scores
                            ├── hechos nuevos → score inicial 0.7
                            ├── hechos reforzados → score += 0.1
                            └── hechos contradichos → score -= 0.2, flag para lint
```

---

## Fase 1 — MVP funcional

**Objetivo:** ingest automático funcionando end-to-end con confidence + knowledge graph básico.

### Tareas

| # | Tarea | Descripción |
|---|---|---|
| 1.1 | Setup del proyecto | `uv init`, `pyproject.toml`, entry point CLI, `.python-version` |
| 1.2 | `config.py` | Leer/escribir `.llmwikidoc.toml` (GEMINI_API_KEY, modelo, rutas) |
| 1.3 | `llm.py` | Cliente Gemini: `generate()` y `embed()` con manejo de errores y retry |
| 1.4 | `git_reader.py` | Extraer de HEAD: mensaje, diff, archivos modificados completos, archivos relacionados |
| 1.5 | `wiki.py` | CRUD de páginas markdown, gestión de index.md y log.md |
| 1.6 | `ingest.py` | Pipeline completo: git_reader → LLM → wiki (prompts estructurados con JSON output) |
| 1.7 | `graph.py` | Knowledge graph con networkx: añadir nodos/aristas, serializar a graph.json |
| 1.8 | `confidence.py` | Score por hecho: inicialización, refuerzo, decaimiento, serialización en frontmatter markdown |
| 1.9 | `cli.py` — `init` | Crear `wiki/`, instalar hook en `.git/hooks/post-commit`, escribir `.llmwikidoc.toml` |
| 1.10 | `cli.py` — `ingest` | Llamar pipeline, mostrar resumen con rich |
| 1.11 | `cli.py` — `query` | Buscar en wiki (text search básico), sintetizar con Gemini, mostrar resultado |
| 1.12 | `hooks/post-commit` | Script shell que llama `llmwikidoc ingest` con manejo de errores no-bloqueante |
| 1.13 | Tests Fase 1 | Unit tests para git_reader, ingest (mock LLM), graph, confidence |

### Diseño de prompts (Fase 1)

El prompt de ingesta enviará a Gemini el contexto del commit y pedirá respuesta JSON con este esquema:

```json
{
  "summary": "string",
  "entities": [{"name": "str", "type": "class|function|module|decision|concept", "description": "str"}],
  "relations": [{"from": "str", "to": "str", "type": "uses|depends_on|modifies|fixes|implements"}],
  "facts": [{"statement": "str", "confidence": 0.7, "entity": "str"}],
  "contradictions": [{"fact": "str", "conflicts_with": "str"}],
  "pages_to_update": ["str"],
  "pages_to_create": ["str"]
}
```

---

## Fase 2 — Calidad y búsqueda

**Objetivo:** lint automático, auto-corrección, búsqueda híbrida completa.

### Tareas

| # | Tarea | Descripción |
|---|---|---|
| 2.1 | `lint.py` | Detectar: contradicciones, páginas huérfanas, claims sin fuente, links rotos |
| 2.2 | Auto-corrección en lint | Para contradicciones simples: Gemini resuelve cuál claim es más reciente/confiable |
| 2.3 | `search.py` — BM25 | Índice BM25 sobre todas las páginas wiki (rank-bm25) |
| 2.4 | `search.py` — Vector | Embeddings con `gemini-embedding-001`, almacenados en wiki/.embeddings/ |
| 2.5 | `search.py` — Graph | Traversal por aristas tipadas del knowledge graph |
| 2.6 | Reciprocal Rank Fusion | Combinar los 3 streams de búsqueda, ranking unificado |
| 2.7 | `cli.py` — `lint` | Comando lint con reporte rich, flag `--fix` para auto-corrección |
| 2.8 | Mejorar `query` | Usar búsqueda híbrida en vez de text search básico |
| 2.9 | Tests Fase 2 | Tests para lint, cada stream de búsqueda, RRF |

---

## Fase 3 — Memoria y compounding

**Objetivo:** consolidación por tiers, decaimiento temporal, cristalización de sesiones.

### Tareas

| # | Tarea | Descripción |
|---|---|---|
| 3.1 | Consolidation tiers | Working → Episodic → Semantic → Procedural (compresión progresiva) |
| 3.2 | Retention decay | Ebbinghaus: facts decaen con el tiempo, se resetean al ser reforzados |
| 3.3 | Consolidation scheduler | `llmwikidoc lint --consolidate` fusiona facts relacionados en semantic tier |
| 3.4 | Session crystallization | `llmwikidoc digest` genera resumen estructurado de N commits como nueva fuente |
| 3.5 | Tests Fase 3 | Tests para decay, consolidation, digest |

---

## Configuración (.llmwikidoc.toml)

```toml
[llmwikidoc]
model = "gemini-2.5-flash"
wiki_dir = "wiki"
context_depth = 2          # niveles de archivos relacionados a incluir

[llmwikidoc.confidence]
initial = 0.7
reinforce_delta = 0.1
contradict_delta = -0.2
decay_days = 30

[llmwikidoc.search]
bm25_weight = 0.33
vector_weight = 0.33
graph_weight = 0.34
```

---

## Convenciones de wiki (frontmatter)

Cada página markdown incluye frontmatter YAML:

```yaml
---
type: entity|concept|summary
name: string
created: ISO date
updated: ISO date
confidence: float (0.0-1.0)
sources: [sha1, sha2]
related: [page1, page2]
tier: working|episodic|semantic|procedural
---
```

---

## Decisiones de diseño

1. **Post-commit no bloquea**: si `llmwikidoc ingest` falla, el commit no se revierte. Los errores se logean en `wiki/log.md`.
2. **JSON output mode de Gemini**: se usa `response_mime_type="application/json"` para extracciones estructuradas, evitando parsing frágil.
3. **Embeddings cacheados**: los embeddings se generan una vez por página y se recalculan solo cuando la página cambia (hash del contenido).
4. **Wiki en el mismo repo**: la carpeta `wiki/` se commitea junto al código. El usuario decide si añadirla a `.gitignore` o versionarla.
5. **API key via env var**: `GEMINI_API_KEY` — nunca en `.llmwikidoc.toml`.

---

## Orden de implementación

```
Fase 1 (MVP)  →  validar end-to-end con un proyecto real
Fase 2        →  mejorar calidad de búsqueda y detección de errores
Fase 3        →  memoria a largo plazo
```

Cada fase termina con tests pasando antes de pasar a la siguiente.
