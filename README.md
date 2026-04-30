
# How to Use

En cualquier proyecto git:

```sh
export GEMINI_API_KEY=tu_key
```
o

```
$env:GEMINI_API_KEY=""

```
llmwikidoc init       # instala hook + crea wiki/
git commit -m "..."   # → hook → llmwikidoc ingest → wiki actualizada
llmwikidoc query "¿qué hace UserService?"
llmwikidoc status
```

El ejecutable llmwikidoc.exe existe dentro del .venv del proyecto, pero no está en el PATH del sistema. Hay dos opciones:

1. Opción A — Instalar globalmente con uv (recomendado)

```sh
uv tool install D:/01-CROSSNET/01-PROJECTS/08-llmwikidoc
```

2. Opción B — Usar siempre uv run desde el directorio del proyecto

```sh
uv run llmwikidoc init
```

3. Opción C — Añadir el venv al PATH temporalmente

```sh
export PATH="D:/01-CROSSNET/01-PROJECTS/08-llmwikidoc/.venv/Scripts:$PATH"
```